from datetime import timedelta

from framcore.timeindexes.ProfileTimeIndex import ProfileTimeIndex  # NB! full import path needed for inheritance to work


class HourlyIndex(ProfileTimeIndex):
    """One or more whole years with hourly resolution."""

    def __init__(
        self,
        start_year: int,
        num_years: int,
        is_52_week_years: bool = True,
    ) -> None:
        """One or more whole years with hourly resolution."""
        super().__init__(
            start_year=start_year,
            num_years=num_years,
            period_duration=timedelta(hours=1),
            is_52_week_years=is_52_week_years,
        )
