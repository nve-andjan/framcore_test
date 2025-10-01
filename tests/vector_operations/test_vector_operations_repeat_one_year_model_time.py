import datetime as dt

import numpy as np
import pytest

from framcore.expressions._time_vector_operations import repeat_oneyear_modeltime

MINUTES_PER_WEEK = 10080
HOURS_PER_WEEK = 168
DAYS_PER_WEEK = 7


@pytest.fixture
def one_year_weekly_data():
    """Fixture to provide one year of weekly data."""
    return np.arange(52, dtype=np.float32)


@pytest.mark.parametrize(
    "input_num_of_periods, period_duration",
    [
        (52, dt.timedelta(weeks=1)),  # Weekly
        (52 * DAYS_PER_WEEK, dt.timedelta(days=1)),  # Daily
        (52 * HOURS_PER_WEEK, dt.timedelta(hours=1)),  # Hourly
        (52 * MINUTES_PER_WEEK, dt.timedelta(minutes=1)),  # Minutely
    ],
)
def test_given_one_year_data_with_resolution_one_week_or_lower_should_repeat_over_specified_number_of_weeks_from_start_of_the_year(
    input_num_of_periods: int,
    period_duration: dt.timedelta,
):
    total_weeks_to_repeat = 60  # Total weeks in the output vector
    input_vector = np.arange(input_num_of_periods, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(weeks=total_weeks_to_repeat)

    result_vector = repeat_oneyear_modeltime(
        input_vector=input_vector,
        input_start_date=input_start_date,
        period_duration=period_duration,
        output_start_date=output_start_date,
        output_end_date=output_end_date,
    )

    periods_per_week = int(dt.timedelta(weeks=1) / period_duration)
    assert len(result_vector) == total_weeks_to_repeat * periods_per_week, (
        "Result vector should contain 60 weeks of data in the specified resolution."
    )
    assert np.array_equal(result_vector[: 52 * periods_per_week], input_vector), (
        "First 52 weeks should match the input vector."
    )
    assert np.array_equal(result_vector[52 * periods_per_week :], input_vector[: 8 * periods_per_week]), (
        "Next 8 weeks should match the first 8 weeks of the input vector."
    )


@pytest.mark.parametrize(
    "input_num_of_periods, period_duration",
    [
        (52, dt.timedelta(weeks=1)),  # Weekly
        (52 * DAYS_PER_WEEK, dt.timedelta(days=1)),  # Daily
        (52 * HOURS_PER_WEEK, dt.timedelta(hours=1)),  # Hourly
        (52 * MINUTES_PER_WEEK, dt.timedelta(minutes=1)),  # Minutely
    ],
)
def test_given_one_year__data_with_one_week_or_lower_should_repeat_for_specified_number_of_weeks_for_any_output_start_date(
    input_num_of_periods: int,
    period_duration: dt.timedelta,
):
    total_weeks_to_repeat = 60  # Total weeks in the output vector
    input_vector = np.arange(input_num_of_periods, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = dt.datetime.fromisocalendar(2021, 5, 1)
    output_end_date = dt.datetime.fromisocalendar(year=2022, week=13, day=1)

    result_vector = repeat_oneyear_modeltime(
        input_vector=input_vector,
        input_start_date=input_start_date,
        period_duration=period_duration,
        output_start_date=output_start_date,
        output_end_date=output_end_date,
    )

    periods_per_week = int(dt.timedelta(weeks=1) / period_duration)
    assert len(result_vector) == total_weeks_to_repeat * periods_per_week, (
        "Result vector should contain 60 weeks of data."
    )
    assert np.array_equal(result_vector[: 48 * periods_per_week], input_vector[4 * periods_per_week :]), (
        "First 48 weeks should match the input vector starting from week 5."
    )
    assert np.array_equal(
        result_vector[48 * periods_per_week : total_weeks_to_repeat * periods_per_week],
        input_vector[: 12 * periods_per_week],
    ), "Next 12 weeks should match the first 8 weeks of the input vector."


@pytest.mark.parametrize(
    "input_num_of_periods, period_duration",
    [
        (1, dt.timedelta(weeks=52)),  # Yearly
        (12, dt.timedelta(weeks=4)),  # Monthly
        (52, dt.timedelta(weeks=1)),  # Weekly
        (52 * DAYS_PER_WEEK, dt.timedelta(days=1)),  # Daily
        (52 * HOURS_PER_WEEK, dt.timedelta(hours=1)),  # Hourly
        (52 * MINUTES_PER_WEEK, dt.timedelta(minutes=1)),  # Minutely
    ],
)
def test_given_one_year_data_in_any_resolution_should_repeat_over_two_whole_years(
    input_num_of_periods,
    period_duration,
):
    input_vector = np.arange(input_num_of_periods, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(
        seconds=input_num_of_periods * period_duration.total_seconds() * 2,
    )  # 2 years

    result_vector = repeat_oneyear_modeltime(
        input_vector=input_vector,
        input_start_date=input_start_date,
        period_duration=period_duration,
        output_start_date=output_start_date,
        output_end_date=output_end_date,
    )

    expected_output_length = input_num_of_periods * 2
    assert len(result_vector) == expected_output_length, (
        f"Result vector should contain {expected_output_length} periods of data (2 years data)."
    )
    assert np.array_equal(result_vector[:input_num_of_periods], input_vector), (
        "First year should match the input vector."
    )
    assert np.array_equal(result_vector[input_num_of_periods:], input_vector), (
        "Second year should also match the input vector."
    )


@pytest.mark.parametrize("input_array", [None, np.array([1, 2]).reshape(2, 1)])
def test_when_input_vector_is_not_vector_raise_exception(input_array):
    input_vector = input_array
    input_start_date = dt.date.fromisocalendar(2020, 1, 1)
    output_start_date = dt.date.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(weeks=60)

    with pytest.raises(AssertionError, match="input_vector must be a 1D numpy array."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=dt.timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


@pytest.mark.parametrize(
    "start_date",
    [
        None,
        1,
        "2020-01-01",
    ],
)
def test_when_input_start_date_is_invalid_should_raise_exception(start_date: object):
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = start_date
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(weeks=60)

    with pytest.raises(AssertionError, match="input_start_date must be a datetime object."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=dt.timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


@pytest.mark.parametrize(
    "period_duration, expected_exception",
    [
        (None, "period_duration must be a timedelta object."),
        (1, "period_duration must be a timedelta object."),
        ("1 week", "period_duration must be a timedelta object."),
        (dt.timedelta(seconds=1), "period_duration must be at least one minute."),
        (dt.timedelta(seconds=100), "period_duration must be at least one minute resolution."),
    ],
)
def test_when_period_duration_is_invalid_should_raise_exception(period_duration: object, expected_exception: str):
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(weeks=60)

    with pytest.raises(AssertionError, match=expected_exception):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=period_duration,
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


@pytest.mark.parametrize(
    "start_date",
    [
        None,
        1,
        "2020-01-01",
    ],
)
def test_when_output_start_date_is_invalid_should_raise_exception(start_date: object):
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = start_date
    output_end_date = dt.datetime.fromisocalendar(2021, 1, 1)

    with pytest.raises(AssertionError, match="output_start_date must be a datetime object."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=dt.timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


@pytest.mark.parametrize(
    "end_date",
    [
        None,
        1,
        "2020-01-01",
    ],
)
def test_when_output_end_date_is_invalid_should_raise_exception(end_date: object):
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = end_date

    with pytest.raises(AssertionError, match="output_end_date must be a datetime object."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=dt.timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


@pytest.mark.parametrize(
    "start_date, end_date",
    [
        (dt.datetime.fromisocalendar(2020, 1, 1), dt.datetime.fromisocalendar(2020, 1, 1)),  # Same date
        (dt.datetime.fromisocalendar(2020, 1, 1), dt.datetime.fromisocalendar(2019, 1, 1)),  # End date before start date
    ],
)
def test_when_output_end_date_is_before_or_equal_to_output_start_date_should_raise_exception(start_date: dt.datetime, end_date: dt.datetime):  # noqa: E501
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date

    with pytest.raises(AssertionError, match="output_end_date must be after output_start_date."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=dt.timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


def test_when_output_duration_is_less_than_one_input_period_duration_should_raise_exception():
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    period_duration = dt.timedelta(weeks=1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(days=1)  # Output duration is less than one week

    with pytest.raises(AssertionError, match="Output period must be at least one period duration long."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=period_duration,
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


def test_when_output_duration_is_not_multiple_of_input_period_duration_should_raise_exception():
    input_vector = np.arange(52, dtype=np.float32)
    input_start_date = dt.datetime.fromisocalendar(2020, 1, 1)
    period_duration = dt.timedelta(weeks=1)
    output_start_date = dt.datetime.fromisocalendar(2021, 1, 1)
    output_end_date = output_start_date + dt.timedelta(days=13)  # Not a multiple of one week

    with pytest.raises(AssertionError, match="Output period must be a multiple of input period duration."):
        repeat_oneyear_modeltime(
            input_vector=input_vector,
            input_start_date=input_start_date,
            period_duration=period_duration,
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )
