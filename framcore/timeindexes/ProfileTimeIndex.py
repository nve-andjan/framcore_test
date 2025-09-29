from datetime import datetime, timedelta

from framcore.timeindexes.FixedFrequencyTimeIndex import FixedFrequencyTimeIndex  # NB! full import path needed for inheritance to work


class ProfileTimeIndex(FixedFrequencyTimeIndex):
    """ProfileTimeIndex represent one or more whole years with fixed time resolution standard."""

    def __init__(
        self,
        start_year: int,
        num_years: int,
        period_duration: timedelta,
        is_52_week_years: bool,
    ) -> None:
        """Initialize the ProfileTimeIndex."""
        start_time = datetime.fromisocalendar(start_year, 1, 1)
        if not is_52_week_years:
            stop_time = datetime.fromisocalendar(start_year + num_years, 1, 1)
            num_periods = (stop_time - start_time).total_seconds() / period_duration.total_seconds()
        else:
            num_periods = timedelta(weeks=52 * num_years).total_seconds() / period_duration.total_seconds()
        assert num_periods.is_integer()
        num_periods = int(num_periods)
        super().__init__(
            start_time=start_time,
            period_duration=period_duration,
            num_periods=num_periods,
            is_52_week_years=is_52_week_years,
            extrapolate_first_point=False,
            extrapolate_last_point=False,
        )
