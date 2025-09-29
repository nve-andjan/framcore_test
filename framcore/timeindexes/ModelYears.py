from datetime import datetime

from framcore.timeindexes.ListTimeIndex import ListTimeIndex  # NB! full import path needed for inheritance to work


class ModelYears(ListTimeIndex):
    """ModelYears represents a collection of years as a ListTimeIndex."""

    def __init__(self, years: list[int]) -> None:
        """Initialize ModelYears with a list of years."""
        datetime_list = [datetime.fromisocalendar(year, 1, 1) for year in years]
        datetime_list.append(datetime.fromisocalendar(years[-1] + 1, 1, 1))
        super().__init__(
            datetime_list=datetime_list,
            is_52_week_years=False,
            extrapolate_first_point=True,
            extrapolate_last_point=True,
        )
