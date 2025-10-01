from datetime import datetime, timedelta

import numpy as np
import pytest

from framcore.timeindexes import FixedFrequencyTimeIndex


# TODO: Expand test coverage
@pytest.mark.parametrize(
    ("start_time", "duration", "expected_value"),
    [
        (datetime(2020, 1, 1, 20), timedelta(hours=4), 1),  # ekstrapolate_first_point
        (datetime(2020, 1, 1, 20), timedelta(hours=8), 1.5),  # overlap first point
        (datetime(2020, 1, 2, 4), timedelta(hours=4), 6),  # interval 1
        (datetime(2020, 1, 2, 5), timedelta(hours=4), 7),  # interval 2
        (datetime(2020, 1, 2, 20), timedelta(hours=8), 22.5),  # overlap last point
        (datetime(2020, 1, 3, 16), timedelta(hours=4), 23),  # ekstrapolate_last_point
    ],
    ids=[
        "extrapolate_first_point",
        "overlap_first_point",
        "interval_1",
        "interval_2",
        "overlap_last_point",
        "extrapolate_last_point",
    ],
)
def test_FrequencyTimeIndex_get_interval_average(start_time, duration, expected_value):  # noqa: N802
    start = datetime(2020, 1, 2)
    frequency = timedelta(hours=2)
    num_points = 12
    values = np.array([1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23], dtype=float)
    request_52_week_years = False

    # Step interpolation
    time_index = FixedFrequencyTimeIndex(
        start_time=start,
        period_duration=frequency,
        num_periods=num_points,
        is_52_week_years=False,
        extrapolate_first_point=True,
        extrapolate_last_point=True,
    )
    result = time_index.get_period_average(values, start_time, duration, is_52_week_years=request_52_week_years)

    assert result == expected_value, f"Expected value {expected_value}, got {result}"


@pytest.mark.parametrize(
    ("start_time", "duration", "expected_value"),
    [
        (datetime(2020, 1, 1, 20), timedelta(hours=4), 1),  # ekstrapolate_first_point
        (datetime(2020, 1, 1, 20), timedelta(hours=8), 1.5),  # overlap first point
        (datetime(2020, 1, 2, 4), timedelta(hours=4), 6),  # interval 1
        (datetime(2020, 1, 2, 5), timedelta(hours=4), 7),  # interval 2
        (datetime(2020, 1, 2, 20), timedelta(hours=8), 22.5),  # overlap last point
        (datetime(2020, 1, 3, 16), timedelta(hours=4), 23),  # ekstrapolate_last_point
    ],
    ids=[
        "extrapolate_first_point",
        "overlap_first_point",
        "interval_1",
        "interval_2",
        "overlap_last_point",
        "extrapolate_last_point",
    ],
)
def test_Frequency52TimeIndex_get_interval_average(start_time, duration, expected_value):  # noqa: N802
    start = datetime(2020, 1, 2)
    frequency = timedelta(hours=2)
    num_points = 12
    values = np.array([1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23], dtype=float)
    is_52_week_years = True

    # Step interpolation
    time_index = FixedFrequencyTimeIndex(
        start_time=start,
        period_duration=frequency,
        num_periods=num_points,
        is_52_week_years=True,
        extrapolate_first_point=True,
        extrapolate_last_point=True,
    )

    result = time_index.get_period_average(values, start_time, duration, is_52_week_years=is_52_week_years)

    assert result == expected_value, f"Expected value {expected_value}, got {result}"


@pytest.mark.parametrize(
    ("start_time", "duration", "expected_value"),
    [
        # Test around isoweek 52, 53, 1 for a relevant year
        (datetime(2020, 12, 23), timedelta(days=2), 360.5),  # interval week 52
        (datetime(2020, 12, 30), timedelta(days=2), 360.5),  # same interval week 53
        (datetime(2020, 12, 27), timedelta(days=2), 361),  # overlap week 52 and 53
        (datetime(2020, 12, 26), timedelta(weeks=2), 363.5),  # overlap week 52, 53 and 1
        (datetime(2021, 1, 6), timedelta(days=2), 367.5),  # same interval week 1
    ],
    ids=[
        "interval_week_52",
        "same_interval_week_53",
        "overlap_week_52_and_53",
        "overlap_week_52_53_and_1",
        "same_interval_week_1",
    ],
)
def test_Frequency52TimeIndex_get_interval_average_around_week_53(start_time, duration, expected_value):  # noqa: N802
    start_52 = datetime.fromisocalendar(2020, 1, 1)
    frequency_52 = timedelta(days=1)
    num_periods_52 = 52 * 7 * 8
    values_52 = np.array(range(1, num_periods_52 + 1), dtype=float)
    is_52_week_years = False

    time_index_52 = FixedFrequencyTimeIndex(
        start_time=start_52,
        period_duration=frequency_52,
        num_periods=num_periods_52,
        is_52_week_years=True,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    result = time_index_52.get_period_average(
        vector=values_52,
        start_time=start_time,
        duration=duration,
        is_52_week_years=is_52_week_years,
    )

    assert result == expected_value, f"Expected value {expected_value}, got {result}"

@pytest.mark.parametrize(
    ("start_time", "duration", "expected_value"),
    [
        (datetime(2026, 12, 23), timedelta(days=2), 360.5),     # interval week 52
        (datetime(2026, 12, 30), timedelta(days=2), 360.5),     # interval week 53
        (datetime(2026, 12, 27), timedelta(days=2), 361),       # overlap week 52 and 53
        (datetime(2026, 12, 26), timedelta(weeks=2), 233.5),    # overlap week 52, 53 and 1
        (datetime(2027, 1, 6), timedelta(days=2), 3.5),         # interval week 1
    ],
    ids=[
        "interval_week_52",
        "interval_week_53",
        "overlap_week_52_and_53",
        "overlap_week_52_53_and_1",
        "interval_week_1",
    ],
)
def test_FrequencyTimeIndex_get_interval_average_no_values(start_time, duration, expected_value):  # noqa: N802
    start_52 = datetime.fromisocalendar(2020, 1, 1)
    frequency_52 = timedelta(days=1)
    num_periods_52 = 52 * 7 * 8
    values_52 = np.tile(np.array(range(1, num_periods_52 // 8 + 1), dtype=float), 8)
    request_52_week_years = False

    time_index_52 = FixedFrequencyTimeIndex(
        start_time=start_52,
        period_duration=frequency_52,
        num_periods=num_periods_52,
        is_52_week_years=True,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    result = time_index_52.get_period_average(values_52, start_time, duration, is_52_week_years=request_52_week_years)

    assert result == expected_value, f"Expected value {expected_value}, got {result}"
