from datetime import datetime, timedelta

import numpy as np

from framcore.timeindexes import ProfileTimeIndex


def weeks_in_isoyear(year: int):
    last_day = datetime.fromisocalendar(year+1, 1, 1) - timedelta(days=1)
    return last_day.isocalendar()[1]

def test_time_vector_conversions():
    hourly_iso = ProfileTimeIndex(2025, 3, timedelta(hours=1), is_52_week_years=False)
    weekly_iso = ProfileTimeIndex(2025, 3, timedelta(weeks=1), is_52_week_years=False)
    weekly_values = np.array([week+1.0 for year in range(2025, 2028) for week in range(weeks_in_isoyear(year))])
    hourly_values = np.zeros(len(weekly_values) * 24 * 7)

    weekly_iso.write_into_fixed_frequency(hourly_values, hourly_iso, weekly_values)
    assert np.all(hourly_values[0:24*7] == 1.0)
    assert np.all(hourly_values[-24*7:] == 52.0)

    hourly_iso.write_into_fixed_frequency(weekly_values, weekly_iso, hourly_values)
    assert weekly_values[0] == 1.0
    assert weekly_values[-1] == 52.0

    hourly52 = ProfileTimeIndex(2025, 3, timedelta(hours=1), is_52_week_years=True)
    hourly52_values = np.zeros(3*52*7*24)

    weekly_iso.write_into_fixed_frequency(hourly52_values, hourly52, weekly_values)
    assert np.all(hourly52_values[0:24*7] == 1.0)

    tmp = hourly52_values.reshape(3, -1)
    assert all(np.array_equal(tmp[i], tmp[0]) for i in range(1, len(tmp)))

    new_weekly_values = np.zeros(len(weekly_values))
    hourly52.write_into_fixed_frequency(new_weekly_values, weekly_iso, hourly52_values)
    assert np.array_equal(new_weekly_values[:52], hourly52_values[:52*168][::168])
    assert np.array_equal(new_weekly_values[52:104], hourly52_values[:52*168][::168])
    assert np.array_equal(new_weekly_values[104], new_weekly_values[103])
    assert np.array_equal(new_weekly_values[105:], hourly52_values[:52*168][::168])
