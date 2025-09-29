from datetime import datetime

from framcore.timeindexes.SinglePeriodTimeIndex import SinglePeriodTimeIndex  # NB! full import path needed for inheritance to work


class AverageYearRange(SinglePeriodTimeIndex):
    """AverageYearRange represents an average over a range of years."""

    def __init__(self, start_year: int, num_years: int) -> None:
        """Initialize AverageYearRange with a year range."""
        start_time = datetime.fromisocalendar(start_year, 1, 1)
        end_time = datetime.fromisocalendar(start_year + num_years, 1, 1)
        period_duration = end_time - start_time
        super().__init__(
            start_time=start_time,
            period_duration=period_duration,
            is_52_week_years=False,
            extrapolate_first_point=False,
            extrapolate_last_point=False,
        )
