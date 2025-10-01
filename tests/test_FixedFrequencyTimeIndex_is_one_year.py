from datetime import datetime, timedelta

import pytest

from framcore.timeindexes import FixedFrequencyTimeIndex


@pytest.mark.parametrize(
    ("start_time", "period_duration", "num_periods", "is_52_week_years", "expected_result"),
    [
        # Modell time checks (52-week years)
        (datetime.fromisocalendar(2021, 1, 1), timedelta(weeks=1), 52, True, True), # Is one-year index modell time
        (datetime.fromisocalendar(2020, 1, 1), timedelta(weeks=1), 52, True, True), # Is one-year index modell time, even if 2020 is a 53-week year
        (datetime.fromisocalendar(2020, 2, 1), timedelta(weeks=1), 52, True, False), # Not start of year
        (datetime.fromisocalendar(2020, 1, 1), timedelta(weeks=2), 52, True, False), # Longer than one year
        (datetime.fromisocalendar(2020, 1, 1), timedelta(weeks=1), 53, True, False), # 2020 is a 53-week year, but model time is allways 52 weeks

        # ISO-time checks (52 or 53-week years)
        (datetime.fromisocalendar(2020, 1, 1), timedelta(weeks=1), 53, False, True), # 2020 is a 53-week year
        (datetime.fromisocalendar(2020, 1, 1), timedelta(weeks=1), 52, False, False), # ISO-time 2020 is a 53-week year, not 52
        (datetime.fromisocalendar(2021, 1, 1), timedelta(weeks=1), 53, False, False), # ISO-time 2021 is a 52-week year, not 53
        (datetime.fromisocalendar(2020, 2, 1), timedelta(weeks=1), 53, False, False), # Not start of year
        (datetime.fromisocalendar(2020, 1, 1), timedelta(weeks=2), 53, False, False), # Longer than one year
    ],
)
def test_is_one_year(start_time, period_duration, num_periods, is_52_week_years, expected_result):
    index = FixedFrequencyTimeIndex(
        start_time=start_time,
        period_duration=period_duration,
        num_periods=num_periods,
        is_52_week_years=is_52_week_years,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

    result = index.is_one_year()

    assert result is expected_result, f"Expected is_one_year to return {expected_result} for a one-year index."
