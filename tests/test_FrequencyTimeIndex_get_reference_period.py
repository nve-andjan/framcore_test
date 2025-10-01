import datetime as dt

import pytest

from framcore.timeindexes import FixedFrequencyTimeIndex


@pytest.mark.parametrize(
    ("start_time", "num_periods", "expected_num_years"),
    [
        (dt.datetime(1980, 12, 29), 52, 1),
        (dt.datetime(1980, 12, 29), 52+52, 2),
        (dt.datetime(1980, 12, 29), 52*10, 10),
    ],
    ids=[
        "one_year",
        "two_years",
        "ten_years",
    ],
)
def test_get_reference_period_with_52_week_time_format(start_time: dt.datetime, num_periods: int, expected_num_years: int):
    is_model_time = True # Model time with 52-weeks years
    period_duration = dt.timedelta(weeks=1)

    time_index = FixedFrequencyTimeIndex(
        start_time=start_time,
        period_duration=period_duration,
        is_52_week_years=is_model_time,
        num_periods=num_periods,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    reference_period = time_index.get_reference_period()

    assert reference_period is not None
    assert reference_period.get_num_years() == expected_num_years

@pytest.mark.parametrize(("start_time", "num_periods", "expected_num_years"), [
    (dt.datetime.fromisocalendar(1981, 1, 1), 53, 1),
    (dt.datetime.fromisocalendar(1981, 1, 1), 53+52, 2),
    (dt.datetime.fromisocalendar(1982, 1, 1), 52, 1),
    (dt.datetime.fromisocalendar(1982, 1, 1), 52+52, 2),
])
def test_get_reference_period_with_isotime_format(start_time: dt.datetime, num_periods: int, expected_num_years: int):
    is_model_time = False # ISO-time, possible to have week 53
    period_duration = dt.timedelta(weeks=1)

    time_index = FixedFrequencyTimeIndex(
        start_time=start_time,
        period_duration=period_duration,
        is_52_week_years=is_model_time,
        num_periods=num_periods,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    reference_period = time_index.get_reference_period()

    assert reference_period is not None
    assert reference_period.get_num_years() == expected_num_years

def test_if_not_whole_years_then_reference_period_is_none():
    is_model_time = True # Model time with 52-weeks years
    start_time = dt.datetime(1980, 12, 29) # Monday, week 1 of 1981, a 52-weeks year
    period_duration = dt.timedelta(weeks=1)
    num_periods = 51 # Not whole year

    time_index = FixedFrequencyTimeIndex(
        start_time=start_time,
        period_duration=period_duration,
        is_52_week_years=is_model_time,
        num_periods=num_periods,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    reference_period = time_index.get_reference_period()

    assert reference_period is None
