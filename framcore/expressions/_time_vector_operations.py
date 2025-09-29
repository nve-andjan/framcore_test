# ruff: noqa: PLR2004
import math
from datetime import date, datetime, timedelta

import numpy as np
from numpy.typing import NDArray

HOURS_PER_WEEK = 168
MINUTES_PER_WEEK = HOURS_PER_WEEK * 60
SECONDS_PER_WEEK = MINUTES_PER_WEEK * 60
MODEL_WEEKS_PER_YEAR = 52


def aggregate(input_vector: NDArray, output_vector: NDArray, is_aggfunc_sum: bool) -> None:
    """Aggregate input vector to output vector."""
    assert len(input_vector.shape) == 1
    assert len(output_vector.shape) == 1
    assert input_vector.size > output_vector.size
    assert input_vector.size % output_vector.size == 0
    assert input_vector.dtype == output_vector.dtype

    multiplier = input_vector.size // output_vector.size
    num_macro_periods = output_vector.size
    input_vector.reshape((num_macro_periods, multiplier)).mean(axis=1, out=output_vector)

    if is_aggfunc_sum:
        np.multiply(output_vector, multiplier, out=output_vector)


def disaggregate(input_vector: NDArray, output_vector: NDArray, is_disaggfunc_repeat: bool) -> None:
    """Disaggregate input vector to output vector."""
    assert len(input_vector.shape) == 1
    assert len(output_vector.shape) == 1
    assert input_vector.size < output_vector.size
    assert output_vector.size % input_vector.size == 0
    assert input_vector.dtype == output_vector.dtype

    multiplier = output_vector.size // input_vector.size
    output_vector[:] = np.repeat(input_vector, multiplier)

    if not is_disaggfunc_repeat:
        np.multiply(output_vector, 1 / multiplier, out=output_vector)


def convert_to_modeltime(input_vector: NDArray, startdate: datetime, period_duration: timedelta) -> tuple[datetime, NDArray]:
    """
    Convert isotime input vector to model time (52-weeks) of various data resolutions by removing week 53 data if present.

    The method supports input vector period durations starting at 1 second up to multiple weeks.

    If the input vector period duration is not compatible with the target period after removing week 53 data, the method will raise a ValueError.

    If start_date of input vector is in week 53, the start_date will be moved to the first week of the next year.

    Args:
        input_vector (NDArray): The input time series vector in isotime format.
        startdate (datetime): The start date of the input vector.
        period_duration (timedelta): The duration of each period in the input vector.

    Returns:
        tuple[datetime, NDArray]: A tuple with two elements, where the first element is a (possibly adjusted) start date and the second element is the converted
        model time vector.

    """
    assert isinstance(input_vector, np.ndarray)
    assert input_vector.ndim == 1
    assert isinstance(startdate, datetime)
    assert isinstance(period_duration, timedelta)
    assert period_duration.total_seconds() > 0, "Period duration must be greater than zero."

    end_date = startdate + period_duration * input_vector.size

    if not _period_contains_week_53(startdate, end_date):
        return startdate, input_vector.copy()

    whole_duration = end_date - startdate
    week_53_periods = _find_all_week_53_periods(startdate, end_date)
    remaining_period = whole_duration - _total_duration(week_53_periods)

    # check if the remaining period is compatible with the target period duration
    if remaining_period % period_duration != timedelta(0):
        suggested_period_duration = _common_compatible_period_duration(whole_duration, remaining_period)
        err_message = f"Incompatible period duration detected! The resulting vector would be incompatible with period duration of {period_duration} after week 53 data is removed. Solution: use period duration that is compatible with both input and resulting vectors. Suggested period duration: {suggested_period_duration}."
        raise ValueError(err_message)

    sub_periods = _find_all_sub_periods(startdate, end_date, week_53_periods)

    if _period_duration_compatible_with_all_sub_periods(period_duration, sub_periods):
        return _to_modeltime(input_vector, startdate, period_duration)

    new_period_duration = _common_compatible_period_duration(period_duration, *[sub_period[1] - sub_period[0] for sub_period in sub_periods])
    scaling_factor = period_duration // new_period_duration

    tmp_vector = np.zeros(input_vector.size * scaling_factor, dtype=input_vector.dtype)

    disaggregate(
        input_vector=input_vector,
        output_vector=tmp_vector,
        is_disaggfunc_repeat=True,
    )

    output_date, tmp_vector = _to_modeltime(
        input_vector=tmp_vector,
        startdate=startdate,
        period_duration=new_period_duration,
    )

    assert tmp_vector.size % scaling_factor == 0, "This should never happen: expected tmp_vector.size to be multiple of scaling_factor before aggregation."

    out_vector = np.zeros(tmp_vector.size // scaling_factor, dtype=input_vector.dtype)

    aggregate(
        input_vector=tmp_vector,
        output_vector=out_vector,
        is_aggfunc_sum=False,
    )

    return output_date, out_vector

def _total_duration(periods: list[tuple[datetime, datetime]]) -> timedelta:
    return sum((end - start for start, end in periods), timedelta(0))

def _find_all_sub_periods(startdate: datetime, enddate: datetime, week_53_periods: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if week_53_periods is None or len(week_53_periods) == 0:
        return [(startdate, enddate)]

    assert week_53_periods[0][0] >= startdate, "First week 53 period must be after or equal to startdate."
    assert week_53_periods[-1][0] < enddate, "Last week 53 period start must be before the enddate."
    assert week_53_periods[-1][1] <= enddate, "Last week 53 period end must be before or equal to the enddate."

    sub_periods = []

    for i, (week_53_start, week_53_end) in enumerate(week_53_periods):
        if i == 0 and week_53_start != startdate:
            sub_periods.append((startdate, week_53_start))
        else:
            prev_week_53_end = week_53_periods[i - 1][1]
            sub_periods.append((prev_week_53_end, week_53_start))
        sub_periods.append((week_53_start, week_53_end))
    if week_53_periods[-1][1] != enddate:
        sub_periods.append((week_53_periods[-1][1], enddate))
    return sub_periods

def _period_duration_compatible_with_all_sub_periods(period_duration: timedelta, periods: list[tuple[datetime, datetime]]) -> bool:
    return not any((period[1] - period[0]) % period_duration != timedelta(0) for period in periods)

def _common_compatible_period_duration(*period_durations: timedelta) -> timedelta:
    return timedelta(seconds=math.gcd(*[int(period_duration.total_seconds()) for period_duration in period_durations]))

def _to_modeltime(input_vector: NDArray, startdate: datetime, period_duration: timedelta) -> tuple[datetime, NDArray]:
    output_vector = _remove_week_53_data(input_vector, startdate, period_duration)

    if not _is_within_week_53(startdate):
        output_date = startdate
    else:
        output_date = _get_start_of_next_year(startdate)

    return output_date, output_vector


def convert_to_isotime(
    input_vector: NDArray,
    startdate: datetime,
    period_duration: timedelta,
) -> NDArray:
    """
    Convert model time input vector to isotime, handling week 53 if present.

    Args:
        input_vector (NDArray): The input vector in model time. Input can be in weekly, daily, hourly or minute format.
            For example year, week and hour format: (2025, 3, 1), (2025, 3, 2), ..., (2025, 52, 168), (2026, 1, 1). Time
            index can start at any date, not necessarily the first day of the year.
        startdate (date): The start date of the input vector.
        period_duration (int): The duration of each period in minutes.

    Returns:
        NDArray: The converted isotime vector.

    """
    assert isinstance(input_vector, np.ndarray)
    assert input_vector.ndim == 1

    total_duration = period_duration * input_vector.size

    is_whole_years = startdate.isocalendar().week == 1 and startdate.isocalendar().weekday == 1 and  (total_duration % timedelta(weeks=52) == timedelta(0))

    if is_whole_years:
        total_years = total_duration // timedelta(weeks=52)
        end_date = datetime.fromisocalendar(startdate.isocalendar().year + total_years, 1, 1)
    else:
        end_date = startdate + total_duration

    if not (is_whole_years and _has_week_53(startdate.isocalendar().year)) and not _period_contains_week_53(startdate, end_date):
        return input_vector.copy()

    week_53_periods = _find_all_week_53_periods(startdate, end_date)
    extended_total_duration = total_duration + timedelta(weeks=len(week_53_periods))

    # check if the extended period is compatible with the target period duration
    if extended_total_duration % period_duration != timedelta(0):
        suggested_period_duration = _common_compatible_period_duration(total_duration, extended_total_duration)
        err_message = f"Incompatible period duration detected when converting to ISO-time! The resulting vector would be incompatible with period duration of {period_duration} after week 53 data is added. Solution: use period duration that is compatible with both input and resulting vectors. Suggested period duration: {suggested_period_duration}."
        raise ValueError(err_message)

    sub_periods = _find_all_sub_periods(startdate,  end_date, week_53_periods)

    if _period_duration_compatible_with_all_sub_periods(period_duration, sub_periods):
        return _to_isotime(input_vector, period_duration, sub_periods)

    new_period_duration = _common_compatible_period_duration(period_duration, *[sub_period[1] - sub_period[0] for sub_period in sub_periods])

    scaling_factor = period_duration // new_period_duration
    tmp_vector = np.zeros(input_vector.size * scaling_factor, dtype=input_vector.dtype)

    disaggregate(
        input_vector=input_vector,
        output_vector=tmp_vector,
        is_disaggfunc_repeat=True,
    )

    assert tmp_vector.size % scaling_factor == 0, "This should never happen: expected tmp_vector.size to be multiple of scaling_factor before aggregation."

    adjusted_vector = _to_isotime(tmp_vector, new_period_duration, sub_periods)


    out_vector = np.zeros(adjusted_vector.size // scaling_factor, dtype=input_vector.dtype)

    aggregate(
        input_vector=adjusted_vector,
        output_vector=out_vector,
        is_aggfunc_sum=False,
    )

    return out_vector

def _to_isotime(input_vector: NDArray, period_duration: timedelta, sub_periods: list[tuple[datetime, datetime]]) -> NDArray:
    periods_per_week = timedelta(weeks=1) // period_duration

    idxs, values = [], []

    for sub_period in sub_periods:
        if sub_period[0].isocalendar().week == 53:
            delta = sub_period[0] - sub_periods[0][0]
            offset = delta // period_duration - len(idxs)
            for i in range(periods_per_week):
                idxs.append(offset)
                values.append(input_vector[offset-periods_per_week + i])

    return np.insert(input_vector, idxs, values)


MINUTES_PER_DAY = 24 * 60


def periodize_isotime(
    input_vector: NDArray,
    input_start_year: int,
    input_num_years: int,
    output_start_year: int,
    output_num_years: int,
) -> NDArray:
    """
    Extract data for a given number of years from an input time series vector.

    This function supports input vectors representing yearly, monthly, or higher-resolution data.
    It calculates the appropriate indices to slice the input vector based on the input and output
    time periods and returns the corresponding subset of the data.

    Args:
        input_vector (NDArray): A 1D NumPy array representing the input time series data.
        input_start_year (int): The starting year of the input time series.
        input_num_years (int): The number of years covered by the input time series.
        output_start_year (int): The starting year of the desired output time series.
        output_num_years (int): The number of years to include in the output time series.

    Returns:
        NDArray: A 1D NumPy array containing the subset of the input vector corresponding to the
                 specified output time period.

        AssertionError: If any of the following conditions are not met:
            - `input_vector` is a 1D NumPy array.
            - `input_start_year` is less than or equal to `output_start_year`.
            - `input_num_years` is less than or equal to the size of `input_vector`.
            - `output_num_years` is less than or equal to `input_num_years`.
            - For higher-resolution data, the input vector size must be a multiple of the
              number of minutes in the input period.
              of minutes in the input period.

    Notes:
        - If the input vector size matches the number of years (`input_num_years`), it is assumed
          to represent yearly data.
        - If the input vector size matches `input_num_years * 12`, it is assumed to represent
          monthly data.
        - For higher-resolution data (e.g., minute-level), the function calculates the appropriate
          indices based on the number of minutes in the input and output periods.

    """
    assert isinstance(input_vector, np.ndarray), "Input vector must be a 1D NumPy array."
    assert input_vector.ndim == 1, "Input vector must be a 1D NumPy array."
    assert input_start_year <= output_start_year, "Input start year must be greater than or equal to output start year."
    assert input_num_years <= input_vector.size, "Input number of years must be less than or equal to input vector size."
    assert output_num_years <= input_num_years, "Output number of years must be less or equalt to input_number_years."

    if input_vector.size == input_num_years:
        # If the input vector size is equal to the number of years.
        start_idx = output_start_year - input_start_year
        end_idx = start_idx + output_num_years
    elif input_vector.size == input_num_years * 12:
        # If the input vector size is monthly data.
        start_idx = (output_start_year - input_start_year) * 12
        end_idx = start_idx + output_num_years * 12
    else:
        input_start_date = date.fromisocalendar(input_start_year, 1, 1)
        input_end_date = date.fromisocalendar(input_start_year + input_num_years, 1, 1)
        output_start_date = date.fromisocalendar(output_start_year, 1, 1)
        output_end_date = date.fromisocalendar(output_start_year + output_num_years, 1, 1)

        data_size_minutes = (input_end_date - input_start_date).days * MINUTES_PER_DAY
        assert data_size_minutes % input_vector.size == 0, "Input vector size must be a multiple of the number of minutes in the input period."

        period_size_minutes = data_size_minutes // input_vector.size
        offset_minutes = (output_start_date - input_start_date).days * MINUTES_PER_DAY
        output_size_minutes = (output_end_date - output_start_date).days * MINUTES_PER_DAY

        start_idx = offset_minutes // period_size_minutes
        end_idx = start_idx + output_size_minutes // period_size_minutes

    return input_vector[start_idx:end_idx]


def periodize_modeltime(
    input_vector: NDArray,
    input_start_year: int,
    input_num_years: int,
    output_start_year: int,
    output_num_years: int,
) -> NDArray:
    """
    Extract a portion of a time-series input vector corresponding to a specified range of years.

    This function assumes that the input vector represents a time series divided into equal periods
    per year. It extracts a subset of the input vector corresponding to the specified output years.

    Args:
        input_vector (NDArray): A 1-dimensional NumPy array representing the input time series.
        input_start_year (int): The starting year of the input vector.
        input_num_years (int): The total number of years represented in the input vector.
        output_start_year (int): The starting year for the output vector.
        output_num_years (int): The number of years to include in the output vector.

    Returns:
        NDArray: A 1-dimensional NumPy array containing the portion of the input vector
                 corresponding to the specified output years.

    Raises:
        AssertionError: If any of the following conditions are not met:
            - `input_vector` is a 1-dimensional NumPy array.
            - `output_start_year` is greater than or equal to `input_start_year`.
            - `input_num_years` is less than or equal to the size of `input_vector`.
            - The size of `input_vector` is a multiple of `input_num_years`.
            - `output_num_years` is less than or equal to `input_num_years`.
            - The requested output vector does not exceed the size of `input_vector`.

    """
    assert isinstance(input_vector, np.ndarray)
    assert input_vector.ndim == 1
    assert output_start_year >= input_start_year, "Output start year must be greater than or equal to input start year."
    assert input_num_years <= input_vector.size, "Input number of years must be less than or equal to input vector size."
    assert input_vector.size % input_num_years == 0, "Input vector size must be a multiple of input number of years."
    assert output_num_years <= input_num_years, "Output number of years must be less or equalt to input_number_years."

    periods_per_year = input_vector.size // input_num_years
    start_idx = (output_start_year - input_start_year) * periods_per_year
    end_idx = start_idx + periods_per_year * output_num_years

    assert end_idx < input_vector.size + 1, "Requested output vector exceeds input vector size."

    return input_vector[start_idx:end_idx]


def repeat_oneyear_modeltime(
    input_vector: NDArray,
    input_start_date: datetime,
    period_duration: timedelta,
    output_start_date: datetime,
    output_end_date: datetime,
) -> NDArray:
    """
    Repeat a one-year input vector to cover the specified output date range.

    Args:
        input_vector (NDArray): A 1D NumPy array representing the input time series for one year.
        input_start_date (date): The start date of the input vector.
        period_duration (timedelta): The duration of each period in the input vector.
        output_start_date (date): The start date of the output period.
        output_end_date (date): The end date of the output period.

    Returns:
        NDArray: A 1D NumPy array containing the repeated time series data for the specified output period.

    """
    assert isinstance(input_vector, np.ndarray), "input_vector must be a 1D numpy array."
    assert input_vector.ndim == 1, "input_vector must be a 1D numpy array."
    assert isinstance(input_start_date, datetime), "input_start_date must be a datetime object."
    assert isinstance(period_duration, timedelta), "period_duration must be a timedelta object."
    assert period_duration.total_seconds() >= 0, "period_duration must be at least one second."
    assert period_duration.total_seconds() % 60 == 0, "period_duration must be at least one minute resolution."
    assert isinstance(output_start_date, datetime), "output_start_date must be a datetime object."
    assert isinstance(output_end_date, datetime), "output_end_date must be a datetime object."
    assert output_start_date < output_end_date, "output_end_date must be after output_start_date."

    output_total_duration = output_end_date - output_start_date
    assert output_total_duration >= period_duration, "Output period must be at least one period duration long."
    assert output_total_duration % period_duration == timedelta(0), "Output period must be a multiple of input period duration."

    output_periods_count = int((output_end_date - output_start_date) / period_duration)

    _, input_start_week, input_start_weekday = input_start_date.isocalendar()
    _, output_start_week, output_start_weekday = output_start_date.isocalendar()

    start_offset_days = (output_start_week - input_start_week) * 7 + (output_start_weekday - input_start_weekday)
    start_offset_periods = int(timedelta(days=start_offset_days) / period_duration)

    # Repeat the input vector enough times to cover the output period
    repeat_count = (start_offset_periods + output_periods_count) / len(input_vector)

    if start_offset_periods + output_periods_count > len(input_vector):
        repeat_count += 1  # Ensure we have enough data to cover the offset

    repeated_vector = np.tile(input_vector, int(repeat_count))

    # Slice the repeated vector to match the exact output period
    return repeated_vector[start_offset_periods : start_offset_periods + output_periods_count]


def repeat_oneyear_isotime(
    input_vector: NDArray,
    input_start_date: datetime,
    period_duration: timedelta,
    output_start_date: datetime,
    output_end_date: datetime,
) -> NDArray:
    """
    Repeat a one-year input vector to cover the specified output date range in isotime format.

    Args:
        input_vector (NDArray): A 1D NumPy array representing the input time series for one year.
        input_start_date (date): The start date of the input vector.
        period_duration (timedelta): The duration of each period in the input vector.
        output_start_date (date): The start date of the output period.
        output_end_date (date): The end date of the output period.

    Returns:
        NDArray: A 1D NumPy array containing the repeated time series data for the specified output period.

    """
    assert isinstance(input_vector, np.ndarray), "input_vector must be a 1D numpy array."
    assert input_vector.ndim == 1, "input_vector must be a 1D numpy array."
    assert isinstance(input_start_date, date), "input_start_date must be a date object."
    assert isinstance(period_duration, timedelta), "period_duration must be a timedelta object."
    assert period_duration.total_seconds() >= 0, "period_duration must be at least one second."
    assert period_duration.total_seconds() % 1 == 0, "period_duration must be at least one second resolution."
    assert isinstance(output_start_date, datetime), "output_start_date must be a date object."
    assert isinstance(output_end_date, datetime), "output_end_date must be a date object."
    assert output_start_date < output_end_date, "output_end_date must be after output_start_date."

    output_total_duration = output_end_date - output_start_date
    assert output_total_duration >= period_duration, "Output period must be at least one period duration long."

    total_years = output_end_date.isocalendar().year - output_start_date.isocalendar().year

    if period_duration > timedelta(weeks=1):
        if period_duration == timedelta(weeks=52) or period_duration == timedelta(weeks=53):
            _, output_start_week, output_start_weekday = output_start_date.isocalendar()
            _, output_end_week, output_end_weekday = output_end_date.isocalendar()

            assert (  # noqa: PT018
                output_start_week == 1 and output_start_weekday == 1 and output_end_week == 1 and output_end_weekday == 1
            ), "Output period must be whole years."
            return np.repeat(input_vector, total_years)
        return ValueError("Provided period duration is not supported for isotime conversion.")

    assert output_total_duration % period_duration == timedelta(0), "Output period must be a multiple of input period duration."

    periods_per_week = SECONDS_PER_WEEK / period_duration.total_seconds()
    assert periods_per_week.is_integer(), "Week must be a multiple of input period duration."
    periods_per_week = int(periods_per_week)

    # Initialize 2D array with 53 weeks per year
    output_vector = np.zeros((total_years, 53 * periods_per_week), dtype=np.float32)

    # Repeat input vector across all years
    output_vector[:, : input_vector.size] = np.tile(input_vector, (total_years, 1))

    # Fill week 53 with the data from week 52 for each year
    if len(input_vector) == 52 * periods_per_week:
        output_vector[:, 52 * periods_per_week :] = output_vector[:, 51 * periods_per_week : 52 * periods_per_week]

    # Flatten the output vector to 1D
    output_vector = np.reshape(output_vector, -1)

    # Array of all years in the output period
    years = np.arange(output_start_date.isocalendar().year, output_end_date.isocalendar().year)

    # Find all indices of years with only 52 weeks
    years_with_52_weeks = np.argwhere(~np.vectorize(_has_week_53)(years)).flatten()

    if years_with_52_weeks.size > 0:
        indices_to_delete = np.reshape(
            [
                np.arange(
                    idx * 53 * periods_per_week + 52 * periods_per_week,
                    idx * 53 * periods_per_week + 52 * periods_per_week + periods_per_week,
                )
                for idx in years_with_52_weeks
            ],
            -1,
        )

        # Remove week 53 for years with only 52 weeks
        output_vector = np.delete(output_vector, indices_to_delete)

    return output_vector


def _is_within_week_53(starttime: datetime) -> bool:
    """Check if the start date is in week 53 of the year."""
    return starttime.isocalendar().week == 53


def _get_start_of_next_year(starttime: datetime) -> datetime:
    """Move the start date to the first week of the next year if it starts in week 53."""
    if starttime.isocalendar().week != 53:
        raise ValueError("Start date is not in week 53.")

    return datetime.fromisocalendar(starttime.isocalendar().year + 1, 1, 1)


def _is_week_53(starttime: datetime) -> bool:
    """Check if the given date is in week 53 of the year."""
    return starttime.isocalendar().week == 53


def _remove_week_53_data(input_vector: NDArray, starttime: datetime, period_duration: timedelta) -> NDArray:
    """Remove data corresponding to week 53 from the input vector."""
    period_duration_seconds = int(period_duration.total_seconds())

    tracking_index = 0
    tracking_date = starttime

    # Adjust start date to the beginning of the week if it doesn't start on a Monday
    if starttime.isocalendar().weekday != 1:
        seconds_to_adjust = (1 - starttime.isocalendar().weekday) * 24 * 60 * 60
        tracking_index += seconds_to_adjust // period_duration_seconds
        tracking_date += timedelta(seconds=seconds_to_adjust)

    indexes_to_remove = []

    while tracking_index < input_vector.size:
        # Calculate the start of week 53
        weeks_to_start_of_week_53 = 53 - tracking_date.isocalendar().week
        seconds_to_start_of_week_53 = weeks_to_start_of_week_53 * SECONDS_PER_WEEK
        tracking_date += timedelta(seconds=seconds_to_start_of_week_53)
        tracking_index += seconds_to_start_of_week_53 // period_duration_seconds

        # Check if week 53 exists and mark its indexes for removal
        if _is_week_53(tracking_date):
            periods_per_week = SECONDS_PER_WEEK // period_duration_seconds
            indexes_to_remove.extend(range(max(tracking_index, 0), min(tracking_index + periods_per_week, input_vector.size)))
            tracking_date += timedelta(seconds=SECONDS_PER_WEEK)
            tracking_index += periods_per_week
    return np.delete(input_vector, indexes_to_remove)


def _has_week_53(year_: int) -> bool:
    """Check if the year of the given date has week 53."""
    return date(year_, 12, 31).isocalendar().week == 53

def _period_contains_week_53(startdate: datetime, enddate: datetime) -> bool:
    """Check if the period between startdate and enddate contains week 53."""
    start_year = startdate.isocalendar().year
    end_year = enddate.isocalendar().year

    for year in range(start_year, end_year + 1):
        if _has_week_53(year):
            week_53_start = datetime.fromisocalendar(year, 53, 1)
            week_53_end = week_53_start + timedelta(weeks=1)
            if startdate < week_53_end and enddate > week_53_start:
                return True
    return False

def _find_all_week_53_periods(startdate: datetime, enddate: datetime) -> list[tuple[datetime, datetime]]:
    """
    Find all week 53 periods between startdate and enddate.

    Returns:
        list of tuples: Each tuple is (start, end), where 'start' is inclusive and 'end' is exclusive.
        Both 'start' and 'end' are datetime objects, representing the start and end of week 53 periods
        within the given range, with granularity at the datetime level.

    """
    week_53_periods = []
    start_year = startdate.isocalendar().year
    end_year = enddate.isocalendar().year

    for year in range(start_year, end_year + 1):
        if _has_week_53(year):
            week_53_start = datetime.fromisocalendar(year, 53, 1)
            week_53_end = week_53_start + timedelta(weeks=1)
            start = max(startdate, week_53_start)
            end = min(enddate, week_53_end)

            if start < end:
                week_53_periods.append((start, end))
    return week_53_periods
