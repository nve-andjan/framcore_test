from datetime import timedelta

from framcore.timeindexes.ProfileTimeIndex import ProfileTimeIndex  # NB! full import path needed for inheritance to work


class DailyIndex(ProfileTimeIndex):
    """One or more whole years with daily resolution."""

    def __init__(
        self,
        start_year: int,
        num_years: int,
        is_52_week_years: bool = True,
    ) -> None:
        """One or more whole years with daily resolution."""
        super().__init__(
            start_year=start_year,
            num_years=num_years,
            period_duration=timedelta(days=1),
            is_52_week_years=is_52_week_years,
        )
