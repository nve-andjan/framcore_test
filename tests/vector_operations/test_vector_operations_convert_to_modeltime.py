from datetime import datetime, timedelta

import numpy as np
import pytest

from framcore.expressions._time_vector_operations import convert_to_modeltime

# Must be able to process timve vectors with any data resolution: yearly, monthly, weekly, two-week, daily, hourly, minute, 15-minutes etc.
# Must be able to process time vectors of any period, f.ex. 1 year, multiple years, several months etc.

# If there is no week 53 in the period, return data as is
# If there is one ore more week 53 in the period:
    # Remove all data in week 53
    # If period duration is not compatible with the total period after removing week 53 data, raise exception
# If start date is in week 53, remove week 53 and move start date to week 1 of next year


HOURS_PER_WEEK = 168
MINUTES_PER_HOUR = 60
MINUTES_PER_WEEK = HOURS_PER_WEEK * MINUTES_PER_HOUR
MODEL_WEEKS_PER_YEAR = 52

YEAR_WITH_53_WEEKS = 2026

def _test_vector(size: int) -> np.ndarray:
    return np.arange(0, size, dtype=np.float32)


@pytest.mark.parametrize("period_duration", [
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
ids=[
    "seconds=1",
    "minutes=1",
    "minutes=15",
    "minutes=30",
    "hours=1",
    "hours=4",
    "hours=8",
    "days=1",
    "days=2",
    "days=4",
    "weeks=1",
    "weeks=2",
    "weeks=4",
],
)
def test_no_week_53_compatible_data_resolutions(period_duration: timedelta):
    assert timedelta(weeks=52) % period_duration == timedelta(0)

    datapoints_count = timedelta(weeks=52) // period_duration
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)
    start_date = datetime.fromisocalendar(2021, 1, 1)  # year with 52 weeks

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=period_duration,
    )

    assert out_date == start_date
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
    "2_weeks_1_day",
    "104_weeks_1_day",
    "2_weeks_2_days",
    "2_weeks_1_week",
    "104_weeks_1_week",
    "208_weeks_4_weeks",
],
)
def test_no_week_53_various_periods_compatible_data_resolutions(total_period: timedelta, period_duration: timedelta):
    assert total_period % period_duration == timedelta(0)

    start_date = datetime.fromisocalendar(2021, 1, 1)   # year with 52 weeks
    datapoints_count = total_period // period_duration

    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=period_duration,
    )

    assert out_date == start_date
    assert output_vector.size == datapoints_count
    assert np.array_equal(output_vector, np.arange(0, datapoints_count, dtype=np.float32))

_two_53_weeks_removed_data = [0., 1., 2., 3., 4., 5., 6., 7., 8., 9., 10., 11.,
 12., 13., 14., 15., 16., 17., 18., 19., 20., 21., 22., 23.,
 24., 25., 26.5, 27.5, 28.5, 29.5, 30.5, 31.5, 32.5, 33.5, 34.5, 35.5,
 36.5, 37.5, 38.5, 39.5, 40.5, 41.5, 42.5, 43.5, 44.5, 45.5, 46.5, 47.5,
 48.5, 49.5, 50.5, 51.5, 52.5, 53.5, 54.5, 55.5, 56.5, 57.5, 58.5, 59.5,
 60.5, 61.5, 62.5, 63.5, 64.5, 65.5, 66.5, 67.5, 68.5, 69.5, 70.5, 71.5,
 72.5, 73.5, 74.5, 75.5, 76.5, 77.5, 78.5, 79.5, 80.5, 81.5, 82.5, 83.5,
 84.5, 85.5, 86.5, 87.5, 88.5, 89.5, 90.5, 91.5, 92.5, 93.5, 94.5, 95.5,
 96.5, 97.5, 98.5, 99.5, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5,
 108.5, 109.5, 110.5, 111.5, 112.5, 113.5, 114.5, 115.5, 116.5, 117.5, 118.5, 119.5,
 120.5, 121.5, 122.5, 123.5, 124.5, 125.5, 126.5, 127.5, 128.5, 129.5, 130.5, 131.5,
 132.5, 133.5, 134.5, 135.5, 136.5, 137.5, 138.5, 139.5, 140.5, 141.5, 142.5, 143.5,
 144.5, 145.5, 146.5, 147.5, 148.5, 149.5, 150.5, 151.5, 152.5, 153.5, 154.5, 155.5,
 156.5, 157.5, 158.5, 159.5, 160.5, 161.5, 162.5, 163.5, 164.5, 165.5, 166.5, 167.5,
 168.5, 169.5, 170.5, 171.5, 172.5, 173.5, 174.5, 175.5, 176.5, 177.5, 178.5, 179.5,
 180.5, 181.5]

@pytest.mark.parametrize(("total_period", "period_duration", "expected_vector"), [
    (timedelta(weeks=53), timedelta(days=1), _test_vector(52*7)), # Period with one week 53 at the end, daily periods
    (timedelta(weeks=54), timedelta(days=1), np.delete(_test_vector(54 * 7), slice(364, 371))), # Period with one week 53 in the middle, daily periods
    (timedelta(weeks=53), timedelta(weeks=1), _test_vector(52)), # Period with one week 53 at the end, weekly periods
    (timedelta(weeks=54), timedelta(weeks=1), np.delete(_test_vector(54), [52])), # Period with one week 53 in the middle, weekly periods
    (timedelta(weeks=366), timedelta(weeks=1), np.delete(_test_vector(366), [52, 365])), # Period with two weeks 53, weekly periods
    (timedelta(weeks=366), timedelta(weeks=2), _two_53_weeks_removed_data), # Period with two weeks 53, 2-week periods
],
ids=[
    "Period with 1 x week-53 at the end, daily periods",
    "Period with 1 x week-53 in the middle, daily periods",
    "Period with 1 x week-53 at the end, weekly periods",
    "Period with 1 x week-53 in the middle, weekly periods",
    "Period with 2 x week-53, weekly periods",
    "Period with 2 x week-53, 2-week periods",
],
)
def test_period_with_53_weeks_compatible_data_resolution_should_remove_week_53_data(total_period: timedelta, period_duration: timedelta, expected_vector):
    assert total_period % period_duration == timedelta(0)

    datapoints_count = total_period // period_duration
    start_date = datetime.fromisocalendar(2020, 1, 1) # year with 53 weeks
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=period_duration,
    )

    assert out_date == start_date
    assert np.size(output_vector) == np.size(expected_vector)
    assert np.array_equal(output_vector, expected_vector)

def test_when_input_not_full_53_weeks_year_daily_data_should_remove_week_53_data():
    start_date = datetime.fromisocalendar(YEAR_WITH_53_WEEKS, 1, 1)
    input_vector = np.arange(0, 53*7-1, dtype=np.float32)

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=timedelta(days=1),
    )

    assert out_date == start_date
    assert np.size(output_vector) == MODEL_WEEKS_PER_YEAR * 7
    assert np.array_equal(output_vector, np.arange(0, MODEL_WEEKS_PER_YEAR * 7, dtype=np.float32))


def test_when_start_date_is_in_week_53_should_remove_week_53_and_move_start_date_to_week_1():
    period_duration = timedelta(days=1)
    datapoints_count = 52 * 7
    input_vector = np.arange(0, datapoints_count, dtype=np.float32)
    start_date = datetime(2026, 12, 30)  # start date is in week 53

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=period_duration,
    )

    assert out_date == datetime(2027, 1, 4)
    assert np.size(output_vector) == datapoints_count-5 # 5 days removed from week 53
    assert np.array_equal(output_vector, np.arange(0, datapoints_count, dtype=np.float32)[5:])

def test_period_with_2_53_week_years_and_2_week_period_duration_expect_2_weeks_removed():
    start_date = datetime.fromisocalendar(2020, 1, 1)
    input_vector = np.arange(0, 183, dtype=np.float32) # 366 weeks from 2020 to 2027 (2x53 + 5x52)

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=timedelta(weeks=2),
    )

    assert out_date == start_date
    assert np.size(output_vector) == 182 # 366 - 2 weeks removed / 2
    # assert np.array_equal(output_vector, np.arange(0, MODEL_WEEKS_PER_YEAR // 2 * 2, dtype=np.float32))

def test_period_with_3_53_week_years_and_3_week_period_duration_expect_3_weeks_removed():
    start_date = datetime.fromisocalendar(2020, 1, 1)
    input_vector = np.arange(0, 227, dtype=np.float32)  # 681 weeks from 2020 to 2033, 3-week periods

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=timedelta(weeks=3),
    )

    assert out_date == start_date
    assert np.size(output_vector) == 226 # 681 - 3 weeks removed / 3


def test_when_period_duration_greater_than_1_week_should_return_results_as_is():
    start_date = datetime(YEAR_WITH_53_WEEKS, 1, 1)
    input_vector = np.arange(0, 12, dtype=np.float32)

    out_date, output_vector = convert_to_modeltime(
        input_vector,
        startdate=start_date,
        period_duration=timedelta(minutes=MINUTES_PER_WEEK + 1),
    )

    assert out_date == start_date
    assert np.array_equal(output_vector, np.arange(0, 12, dtype=np.float32))


@pytest.mark.parametrize("input_array", [None, np.array([1, 2]).reshape(2, 1)])
def test_when_input_vetor_is_not_vector_raise_exception(input_array):
    with pytest.raises(AssertionError):
        convert_to_modeltime(input_array, startdate=datetime.now().date(), period_duration=1)


@pytest.mark.parametrize("start_date", [None, 0, 1.5, "string"])
def test_when_startdate_is_not_date_raise_exception(start_date):
    input_array = np.ones(52, dtype=np.float32)

    with pytest.raises(AssertionError):
        convert_to_modeltime(input_array, startdate=start_date, period_duration=1)

@pytest.mark.parametrize("period_duration", [-1, 0, None, 1.5, "string"])
def test_when_period_duration_is_not_valid_raise_exception(period_duration):
    input_array = np.ones(52, dtype=np.float32)
    start_date = datetime.now().date()

    with pytest.raises(AssertionError):
        convert_to_modeltime(input_array, startdate=start_date, period_duration=period_duration)

def test_incompatible_period_duration_after_removing_53_week_data_raises_exception():
    start_date = datetime.fromisocalendar(2020, 1, 1)
    input_vector = np.arange(0, 73, dtype=np.float32)
    period_duration = timedelta(days=5)

    with pytest.raises(ValueError, match="Incompatible period duration detected!"):
        convert_to_modeltime(input_vector, startdate=start_date, period_duration=period_duration)
