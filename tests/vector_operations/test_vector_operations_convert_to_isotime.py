from datetime import datetime, timedelta

import numpy as np
import pytest

from framcore.expressions._time_vector_operations import convert_to_isotime

# Must handle various data resolutions (second, hourly, daily, weekly, multi-week, etc.)
# If defined period contains one or more 53-weeks/parts of week-53, data must be repeated from week 52 accordingly.
# Period duration must be compatible with both input and resulting vectors, otherwise ValueError is raised.

def _test_vector(size: int) -> np.ndarray:
    return np.arange(0, size, dtype=np.float32)


@pytest.mark.parametrize(
    "period_duration", [
        timedelta(seconds=1),
        timedelta(minutes=1),
        timedelta(minutes=15),
        timedelta(minutes=30),
        timedelta(hours=1),
        timedelta(hours=4),
        timedelta(hours=8),
        timedelta(days=1),
        timedelta(days=2),
        timedelta(days=4),
        timedelta(weeks=1),
        timedelta(weeks=2),
        timedelta(weeks=4),
    ],
    ids=lambda td: f"period_duration={td}",
)
def test_period_does_not_contain_week_53_various_data_resolutions(period_duration: timedelta):
    total_duration = timedelta(weeks=52)

    assert total_duration % period_duration == timedelta(0)

    datapoints_count = total_duration // period_duration
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)
    start_date = datetime.fromisocalendar(2021, 1, 1)  # year with 52 weeks

    output_vector = convert_to_isotime(input_vector, start_date, period_duration)

    assert output_vector.size == datapoints_count
    assert np.array_equal(output_vector, np.arange(0, datapoints_count, dtype=np.float32))

@pytest.mark.parametrize(("total_period", "period_duration"), [
    (timedelta(weeks=2), timedelta(days=1)),
    (timedelta(weeks=104), timedelta(days=1)),
    (timedelta(weeks=2), timedelta(days=2)),
    (timedelta(weeks=2), timedelta(weeks=1)),
    (timedelta(weeks=104), timedelta(weeks=1)),
    (timedelta(weeks=208), timedelta(weeks=4)),
],
ids=[
    "total_period=2_weeks_period_duration=1_day",
    "total_period=104_weeks_period_duration=1_day",
    "total_period=2_weeks_period_duration=2_days",
    "total_period=2_weeks_period_duration=1_week",
    "total_period=104_weeks_period_duration=1_week",
    "total_period=208_weeks_period_duration=4_weeks",
],
)
def test_period_does_not_contain_week_53_various_periods_compatible_data_resolutions(total_period: timedelta, period_duration: timedelta):
    assert total_period % period_duration == timedelta(0)

    start_date = datetime.fromisocalendar(2021, 1, 1)   # year with 52 weeks
    datapoints_count = total_period // period_duration

    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    output_vector = convert_to_isotime(
        input_vector,
        startdate=start_date,
        period_duration=period_duration,
    )

    assert output_vector.size == datapoints_count
    assert np.array_equal(output_vector, np.arange(0, datapoints_count, dtype=np.float32))

@pytest.mark.parametrize(("total_period", "period_duration", "expected_output"), [
    (timedelta(weeks=53), timedelta(days=1), np.insert(_test_vector(371), 364, _test_vector(371)[357:364])),
    (timedelta(weeks=53), timedelta(weeks=1), np.insert(_test_vector(53), 52, _test_vector(53)[51])),
    (timedelta(weeks=366), timedelta(weeks=1), np.insert(_test_vector(366), [52, 364], [51, 363])),
], ids=[
    "total_period=53_weeks, period_duration=1_day",
    "total_period=53_weeks, period_duration=1_week",
    "total_period=366_weeks, period_duration=1_week",
],
)
def test_period_contains_whole_weeks_53_and_compatible_data_resolution(total_period: timedelta, period_duration: timedelta, expected_output: np.ndarray):
    assert total_period % period_duration == timedelta(0)

    start_date = datetime.fromisocalendar(2026, 1, 1)  # 2026 is a 53 weeks year
    datapoints_count = total_period // period_duration

    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    output_vector = convert_to_isotime(input_vector, start_date, period_duration)

    assert len(output_vector) == len(expected_output)
    assert np.array_equal(output_vector, expected_output)

@pytest.mark.parametrize(("start_date", "total_period", "period_duration", "expected_output"), [
    (datetime.fromisocalendar(2021, 4, 1), timedelta(weeks=4), timedelta(weeks=1), _test_vector(4)),
    (datetime.fromisocalendar(2021, 4, 1), timedelta(weeks=52), timedelta(weeks=1), _test_vector(52)),
    (datetime.fromisocalendar(2021, 4, 1), timedelta(weeks=104), timedelta(weeks=1), _test_vector(104)),
    (datetime.fromisocalendar(2021, 4, 3), timedelta(weeks=52), timedelta(weeks=1), _test_vector(52)),
], ids=[
    "Start of week, total_period=4 weeks, period_duration=1 week",
    "Start of week, total_period=52 weeks, period_duration=1 week",
    "Start of week, total_period=104 weeks, period_duration=1 week",
    "Not start of week, total_period=52 weeks, period_duration=1 week",
])
def test_period_does_not_contain_week_53_and_period_starts_not_at_start_of_year(start_date: datetime, total_period: timedelta, period_duration: timedelta, expected_output: np.ndarray):
    assert total_period % period_duration == timedelta(0)

    datapoints_count = total_period // period_duration
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    result_vector = convert_to_isotime(input_vector, start_date, period_duration)

    assert len(result_vector) == len(expected_output)
    assert np.array_equal(result_vector, expected_output)


@pytest.mark.parametrize(("start_date", "total_period", "period_duration", "expected_output"), [
    (datetime.fromisocalendar(2026, 4, 1), timedelta(weeks=52), timedelta(weeks=1), np.insert(_test_vector(52), 49, [48])),
    (datetime.fromisocalendar(2026, 4, 1), timedelta(weeks=363), timedelta(weeks=1), np.insert(_test_vector(363), [49, 361], [48, 360])),
    (datetime.fromisocalendar(2026, 4, 3), timedelta(weeks=50), timedelta(days=1), np.insert(_test_vector(350), 341, _test_vector(350)[334:341])),
],
ids=[
    "Start of week, total_period=52 weeks, period_duration=1 week",
    "Start of week, total_period=363 weeks, period_duration=1 week",
    "Not start of week, total_period=2 weeks, period_duration=1 day",
])
def test_period_contains_whole_weeks_53_and_starts_not_at_start_of_year(start_date: datetime, total_period: timedelta, period_duration: timedelta, expected_output: np.ndarray):
    assert total_period % period_duration == timedelta(0)

    datapoints_count = total_period // period_duration
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    output_vector = convert_to_isotime(input_vector, start_date, period_duration)

    assert len(output_vector) == len(expected_output)
    assert np.array_equal(output_vector, expected_output)

def test_period_contains_whole_weeks_53_and_starts_not_at_start_of_year_need_disaggregation():
    input_vector = np.array([1, 8, 5], dtype=np.float32) # 3 weeks of data
    start_date = datetime.fromisocalendar(2026, 51, 3)  # 2026 is a 53 weeks year
    period_duration = timedelta(weeks=1)

    output_vector = convert_to_isotime(input_vector, start_date, period_duration)

    expected_output = np.array([1, 6, 8, 5], dtype=np.float32)
    assert len(output_vector) == len(expected_output)
    assert np.array_equal(output_vector, expected_output)

@pytest.mark.parametrize(("input_vector", "start_date", "period_duration"), [
    (np.arange(0, 4, dtype=np.float32), datetime.fromisocalendar(2026, 52, 1), timedelta(days=2)),   # incompatible resolution after adding week 53
    (np.arange(0, 27, dtype=np.float32), datetime.fromisocalendar(2026, 1, 1), timedelta(weeks=2)),  # incompatible resolution after adding week 53
    (np.arange(0, 105, dtype=np.float32), datetime.fromisocalendar(2026, 1, 1), timedelta(weeks=4)), # incompatible resolution after adding week 53
],ids=[
    "input_vector_size=4, start_date=2026 week 52, period_duration=2_days",
    "input_vector_size=27, start_date=2026 week 1, period_duration=2_weeks",
    "input_vector_size=105, start_date=2026 week 1, period_duration=4_weeks",
],
)
def test_period_contains_whole_week_53_but_incompatible_data_resolution_raises_exception(input_vector: np.ndarray, start_date: datetime, period_duration: timedelta):
    with pytest.raises(ValueError, match="Incompatible period duration detected when converting to ISO-time!"):
        convert_to_isotime(input_vector, start_date, period_duration)

def test_period_ends_in_week_53_should_add_whole_week():
    input_vector = np.arange(10, dtype=np.float32)
    start_date = datetime.fromisocalendar(2026, 52, 1)
    period_duration = timedelta(days=1)

    output_vector = convert_to_isotime(input_vector, start_date, period_duration)

    expected_output = np.array([0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=np.float32)
    assert len(output_vector) == len(expected_output)
    assert np.array_equal(output_vector, expected_output)

@pytest.mark.parametrize(("period_duration", "expected_output"), [
    (timedelta(days=1), np.concatenate([_test_vector(52*7), _test_vector(52*7)[-7:]])),
    (timedelta(weeks=1), np.concatenate([_test_vector(52), _test_vector(52)[-1:]])),
], ids=[
    "period_duration=1_day",
    "period_duration=1_week",
])
def test_when_period_starts_at_first_day_of_the_53_week_year_and_contains_52_weeks_of_data_should_repeat_week_52(period_duration, expected_output):
    start_date = datetime.fromisocalendar(2020, 1, 1)
    total_duration = timedelta(weeks=52)

    assert total_duration % period_duration == timedelta(0)

    datapoints_count = total_duration // period_duration
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    output_vector = convert_to_isotime(input_vector, start_date, period_duration)

    assert len(output_vector) == len(expected_output)
    assert np.array_equal(output_vector, expected_output)
