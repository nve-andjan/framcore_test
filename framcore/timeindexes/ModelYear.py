from datetime import datetime, timedelta

from framcore.timeindexes.SinglePeriodTimeIndex import SinglePeriodTimeIndex  # NB! full import path needed for inheritance to work


class ModelYear(SinglePeriodTimeIndex):
    """ModelYear represent one 52-week-year. No extrapolation."""

    def __init__(self, year: int) -> None:
        """Represent a specified year. Use 52-week-year starting on monday in week 1. No extrapolation."""
        super().__init__(
            start_time=datetime.fromisocalendar(year, 1, 1),
            period_duration=timedelta(weeks=52),
            is_52_week_years=True,
            extrapolate_first_point=False,
            extrapolate_last_point=False,
        )
