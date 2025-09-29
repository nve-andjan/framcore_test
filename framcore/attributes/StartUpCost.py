from __future__ import annotations

from typing import TYPE_CHECKING

from framcore import Base
from framcore.attributes import Cost, Efficiency, Hours, Proportion
from framcore.fingerprints import Fingerprint

if TYPE_CHECKING:
    from framcore.loaders import Loader


class StartUpCost(Base):
    """StartUpCost class representing the startup cost of a Component."""

    def __init__(
        self,
        startup_cost: Cost,
        min_stable_load: Proportion,
        start_hours: Hours,
        part_load_efficiency: Efficiency,
    ) -> None:
        """Initialize the StartUpCost class."""
        self._check_type(startup_cost, Cost)
        self._check_type(min_stable_load, Proportion)
        self._check_type(start_hours, Hours)
        self._check_type(part_load_efficiency, Efficiency)

        self._startup_cost = startup_cost
        self._min_stable_load = min_stable_load
        self._start_hours = start_hours
        self._part_load_efficiency = part_load_efficiency

    def get_startupcost(self) -> Cost:
        """Get the startup cost."""
        return self._startup_cost

    def set_startupcost(self, startupcost: Cost) -> None:
        """Set the startup cost."""
        self._check_type(startupcost, Cost)
        self._startup_cost = startupcost

    def get_fingerprint(self) -> Fingerprint:
        """Get the fingerprint of the startup cost."""
        return self.get_fingerprint_default()

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Get all loaders stored in attributes."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self.get_startupcost())
        add_loaders_if(loaders, self._start_hours)
        add_loaders_if(loaders, self._min_stable_load)
        add_loaders_if(loaders, self._part_load_efficiency)
