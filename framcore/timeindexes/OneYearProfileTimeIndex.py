from datetime import timedelta

from framcore.timeindexes.ProfileTimeIndex import ProfileTimeIndex  # NB! full import path needed for inheritance to work


class OneYearProfileTimeIndex(ProfileTimeIndex):
    """Fixed frequency over one year."""

    def __init__(self, period_duration: timedelta, is_52_week_years: bool) -> None:
        """
        Initialize a OneYearProfileTimeIndex with a fixed frequency over one year.

        We use 1982 for 52-week years and 1981 for 53-week years.

        Args:
            period_duration (timedelta): Duration of each period.
            is_52_week_years (bool): Whether to use 52-week years.

        """
        year = 1982 if is_52_week_years else 1981
        super().__init__(year, 1, period_duration, is_52_week_years)
