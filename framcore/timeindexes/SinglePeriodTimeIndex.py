from __future__ import annotations

from datetime import datetime, timedelta

from framcore.timeindexes.FixedFrequencyTimeIndex import FixedFrequencyTimeIndex  # NB! full import path needed for inheritance to work


class SinglePeriodTimeIndex(FixedFrequencyTimeIndex):
    """FrequencyTimeIndex with just one single step."""

    def __init__(
        self,
        start_time: datetime,
        period_duration: timedelta,
        is_52_week_years: bool = False,
        extrapolate_first_point: bool = False,
        extrapolate_last_point: bool = False,
    ) -> None:
        """
        Initialize a SinglePeriodTimeIndex with a single time period.

        Args:
            start_time (datetime): The start time of the period.
            period_duration (timedelta): The duration of the period.
            is_52_week_years (bool, optional): Whether to use 52-week years. Defaults to False.
            extrapolate_first_point (bool, optional): Whether to extrapolate the first point. Defaults to False.
            extrapolate_last_point (bool, optional): Whether to extrapolate the last point. Defaults to False.

        """
        super().__init__(
            start_time=start_time,
            period_duration=period_duration,
            num_periods=1,
            is_52_week_years=is_52_week_years,
            extrapolate_first_point=extrapolate_first_point,
            extrapolate_last_point=extrapolate_last_point,
        )
