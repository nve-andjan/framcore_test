from datetime import datetime, timedelta

from framcore.timeindexes.SinglePeriodTimeIndex import SinglePeriodTimeIndex  # NB! full import path needed for inheritance to work


class IsoCalendarDay(SinglePeriodTimeIndex):
    """
    Represents a single ISO calendar day using year, week, and day values.

    Inherits from SinglePeriodTimeIndex and provides a time index for one day,
    constructed from datetime.fromisocalendar(year, week, day).

    """

    def __init__(self, year: int, week: int, day: int) -> None:
        """
        IsoCalendarDay represent a day from datetime.fromisocalendar(year, week, day).

        No extrapolation.

        is_52_week_years=False

        Useful for testing.
        """
        super().__init__(
            start_time=datetime.fromisocalendar(year, week, day),
            period_duration=timedelta(days=1),
            is_52_week_years=False,
            extrapolate_first_point=False,
            extrapolate_last_point=False,
        )
