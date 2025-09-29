from datetime import timedelta

from framcore.timeindexes.ProfileTimeIndex import ProfileTimeIndex  # NB! full import path needed for inheritance to work


class OneYearProfileTimeIndex(ProfileTimeIndex):
    """Fixed frequency over one year."""

    def __init__(self, period_duration: timedelta, is_52_week_years: bool) -> None:
        """
        Initialize a OneYearProfileTimeIndex with a fixed frequency over one year.

        Args:
            period_duration (timedelta): Duration of each period.
            is_52_week_years (bool): Whether to use 52-week years.

        """
        super().__init__(1981, 1, period_duration, is_52_week_years)
