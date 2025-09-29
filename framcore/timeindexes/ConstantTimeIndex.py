from datetime import datetime, timedelta

from framcore.timeindexes.SinglePeriodTimeIndex import SinglePeriodTimeIndex  # NB! full import path needed for inheritance to work


class ConstantTimeIndex(SinglePeriodTimeIndex):
    """Used in ConstantTimeVector."""

    def __init__(self) -> None:
        """Represent a specified year."""
        super().__init__(
            start_time=datetime.fromisocalendar(1985, 1, 1),
            period_duration=timedelta(weeks=52),
            is_52_week_years=True,
            extrapolate_first_point=True,
            extrapolate_last_point=True,
        )
