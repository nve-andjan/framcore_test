from datetime import date, datetime, timedelta

import numpy as np
import pytest

from framcore.expressions._time_vector_operations import repeat_oneyear_isotime


@pytest.mark.parametrize(
    "input_start_date, num_of_periods, period_duration, output_start_date, output_end_date, expected_result_len",
    [
        # 52-week year input, repeating for one 52-week year
        (
            datetime.fromisocalendar(2021, 1, 1),
            52,
            timedelta(weeks=1),
            output_start_date := datetime.fromisocalendar(2022, 1, 1),
            output_end_date := datetime.fromisocalendar(2023, 1, 1),
            52,
        ),
        # 52-week year input, repeating over two 52-week years
        (
            datetime.fromisocalendar(2021, 1, 1),
            52,
            timedelta(weeks=1),
            output_start_date := datetime.fromisocalendar(2022, 1, 1),
            output_end_date := datetime.fromisocalendar(2024, 1, 1),
            104,
        ),
        # 52-week year input, repeating over 52 and 53-week years
        (
            datetime.fromisocalendar(2021, 1, 1),
            52,
            timedelta(weeks=1),
            output_start_date := datetime.fromisocalendar(2025, 1, 1),
            output_end_date := datetime.fromisocalendar(2028, 1, 1),
            157,
        ),
    ],
)
def test_given_52_week_year_weekly_data_input_vector_should_rotate_over_expected_period(
    input_start_date,
    num_of_periods,
    period_duration,
    output_start_date,
    output_end_date,
    expected_result_len,
):
    input_vector = np.arange(num_of_periods, dtype=np.float32)

    result = repeat_oneyear_isotime(
        input_vector=input_vector,
        input_start_date=input_start_date,
        period_duration=period_duration,
        output_start_date=output_start_date,
        output_end_date=output_end_date,
    )

    assert len(result) == expected_result_len, f"Expected {expected_result_len} weeks, got {len(result)}"
    assert np.array_equal(result[:num_of_periods], input_vector), (
        f"Expected first {num_of_periods} periods to match input vector, got {result[:num_of_periods]}"
    )


def test_given_52_week_year_hourly_data_input_vector_should_rotate_over_one_52_week_year():
    input_start_date = datetime.fromisocalendar(2021, 1, 1)
    num_of_periods = 52 * 7 * 24
    period_duration = timedelta(hours=1)
    output_start_date = datetime.fromisocalendar(2022, 1, 1)
    output_end_date = datetime.fromisocalendar(2023, 1, 1)

    input_vector = np.arange(num_of_periods, dtype=np.float32)

    result = repeat_oneyear_isotime(
        input_vector=input_vector,
        input_start_date=input_start_date,
        period_duration=period_duration,
        output_start_date=output_start_date,
        output_end_date=output_end_date,
    )

    expected_result_len = num_of_periods

    assert len(result) == expected_result_len, f"Expected {expected_result_len} hours, got {len(result)}"
    assert np.array_equal(result[:num_of_periods], input_vector), (
        f"Expected first {num_of_periods} periods to match input vector, got {result[:num_of_periods]}"
    )


def test_given_52_week_year_hourly_data_input_vector_should_rotate_over_two_52_week_years():
    input_start_date = datetime.fromisocalendar(2021, 1, 1)
    num_of_periods = 52 * 7 * 24
    period_duration = timedelta(hours=1)
    output_start_date = datetime.fromisocalendar(2022, 1, 1)
    output_end_date = datetime.fromisocalendar(2024, 1, 1)

    input_vector = np.arange(num_of_periods, dtype=np.float32)

    result = repeat_oneyear_isotime(
        input_vector=input_vector,
        input_start_date=input_start_date,
        period_duration=period_duration,
        output_start_date=output_start_date,
        output_end_date=output_end_date,
    )

    expected_result_len = num_of_periods * 2

    assert len(result) == expected_result_len, f"Expected {expected_result_len} hours, got {len(result)}"
    assert np.array_equal(result[:num_of_periods], input_vector), (
        f"Expected first {num_of_periods} periods to match input vector, got {result[:num_of_periods]}"
    )
    assert np.array_equal(result[num_of_periods : 2 * num_of_periods], input_vector), (
        f"Expected second {num_of_periods} periods to match input vector, got {result[num_of_periods : 2 * num_of_periods]}"
    )


def test_given_53_week_year_weekly_data_input_vector_should_rotate_over_one_53_week_year():
    input_vector = np.arange(53, dtype=np.float32)

    result = repeat_oneyear_isotime(
        input_vector=input_vector,
        input_start_date=datetime.fromisocalendar(2020, 1, 1),
        period_duration=timedelta(weeks=1),
        output_start_date=datetime.fromisocalendar(2020, 1, 1),
        output_end_date=datetime.fromisocalendar(2021, 1, 1),
    )

    assert len(result) == 53, f"Expected 53 weeks, got {len(result)}"
    assert np.array_equal(result, input_vector), f"Expected {input_vector}, got {result}"


def test_given_53_week_year_weekly_data_input_vector_should_rotate_over_one_53_and_one_52_week_years():
    input_vector = np.arange(53, dtype=np.float32)

    result = repeat_oneyear_isotime(
        input_vector=input_vector,
        input_start_date=datetime.fromisocalendar(2020, 1, 1),
        period_duration=timedelta(weeks=1),
        output_start_date=datetime.fromisocalendar(2020, 1, 1),
        output_end_date=datetime.fromisocalendar(2022, 1, 1),
    )

    assert len(result) == 105, f"Expected 105 weeks (53 + 52), got {len(result)}"
    assert np.array_equal(result[:53], input_vector), (
        f"Expected first 53 weeks to match input vector, got {result[:53]}"
    )
    assert np.array_equal(result[53:], np.arange(52, dtype=np.float32)), (
        f"Expected last 52 weeks to be a sequence from 0 to 51, got {result[53:]}"
    )


@pytest.mark.parametrize("input_vector", [None, 123, np.array([2, 2]).reshape(2, 1)])
def test_when_input_vector_is_not_a_vector_should_raise_type_error(input_vector):
    with pytest.raises(AssertionError, match="input_vector must be a 1D numpy array."):
        repeat_oneyear_isotime(
            input_vector=input_vector,
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=timedelta(weeks=1),
            output_start_date=datetime.fromisocalendar(2022, 1, 1),
            output_end_date=datetime.fromisocalendar(2023, 1, 1),
        )


@pytest.mark.parametrize("input_start_date", [None, "2021-01-01", 123])
def test_when_input_start_date_is_not_a_date_should_raise_type_error(input_start_date):
    with pytest.raises(AssertionError, match="input_start_date must be a date object."):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=input_start_date,
            period_duration=timedelta(weeks=1),
            output_start_date=datetime.fromisocalendar(2022, 1, 1),
            output_end_date=datetime.fromisocalendar(2023, 1, 1),
        )


@pytest.mark.parametrize(
    "period_duration, expected_exception",
    [
        (None, "period_duration must be a timedelta object."),
        ("1 week", "period_duration must be a timedelta object."),
        (123, "period_duration must be a timedelta object."),
    ],
)
def test_when_period_duration_is_invalid_should_raise_error(period_duration, expected_exception):
    with pytest.raises(AssertionError, match=expected_exception):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=period_duration,
            output_start_date=datetime.fromisocalendar(2022, 1, 1),
            output_end_date=datetime.fromisocalendar(2023, 1, 1),
        )


@pytest.mark.parametrize("output_start_date", [None, "2022-01-01", 123])
def test_when_output_start_date_is_not_a_date_should_raise_type_error(output_start_date):
    with pytest.raises(AssertionError, match="output_start_date must be a date object."):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=datetime.fromisocalendar(2023, 1, 1),
        )


@pytest.mark.parametrize("output_end_date", [None, "2023-01-01", 123])
def test_when_output_end_date_is_not_a_date_should_raise_type_error(output_end_date):
    with pytest.raises(AssertionError, match="output_end_date must be a date object."):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=timedelta(weeks=1),
            output_start_date=datetime.fromisocalendar(2022, 1, 1),
            output_end_date=output_end_date,
        )


@pytest.mark.parametrize(
    "output_start_date, output_end_date",
    [
        (datetime.fromisocalendar(2022, 1, 1), datetime.fromisocalendar(2021, 1, 1)),
        (datetime.fromisocalendar(2022, 2, 1), datetime.fromisocalendar(2022, 1, 1)),
    ],
)
def test_when_output_start_date_is_after_output_end_date_should_raise_error(output_start_date, output_end_date):
    with pytest.raises(AssertionError, match="output_end_date must be after output_start_date."):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=timedelta(weeks=1),
            output_start_date=output_start_date,
            output_end_date=output_end_date,
        )


def test_when_output_duration_is_less_than_period_duration_should_raise_error():
    with pytest.raises(AssertionError, match="Output period must be at least one period duration long."):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=timedelta(weeks=1),
            output_start_date=datetime.fromisocalendar(2022, 1, 1),
            output_end_date=datetime.fromisocalendar(2022, 1, 2),  # Less than one week
        )


def test_when_output_duration_is_not_a_multiple_of_period_duration_should_raise_error():
    with pytest.raises(AssertionError, match="Output period must be a multiple of input period duration."):
        repeat_oneyear_isotime(
            input_vector=np.arange(52, dtype=np.float32),
            input_start_date=datetime.fromisocalendar(2021, 1, 1),
            period_duration=timedelta(weeks=1),
            output_start_date=datetime.fromisocalendar(2022, 1, 1),
            output_end_date=datetime.fromisocalendar(2022, 2, 3),  # Not a multiple of one week
        )
