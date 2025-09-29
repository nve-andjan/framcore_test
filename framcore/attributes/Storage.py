from __future__ import annotations

from typing import TYPE_CHECKING

from framcore import Base
from framcore.attributes import Loss, ObjectiveCoefficient, ReservoirCurve, SoftBound, StockVolume, TargetBound

if TYPE_CHECKING:
    from framcore.loaders import Loader


class Storage(Base):
    """
    Represents all types of storage this system supports.

    Subclasses are supposed to restrict which attributes that are
    used, not add more.
    """

    def __init__(
        self,
        capacity: StockVolume,
        volume: StockVolume | None = None,
        loss: Loss | None = None,
        reservoir_curve: ReservoirCurve | None = None,
        max_soft_bound: SoftBound | None = None,
        min_soft_bound: SoftBound | None = None,
        target_bound: TargetBound | None = None,
        initial_storage_percentage: float | None = None,
    ) -> None:
        """Create new storage."""
        super().__init__()

        self._check_type(capacity, StockVolume)
        self._check_type(volume, (StockVolume, type(None)))
        self._check_type(loss, (StockVolume, type(None)))
        self._check_type(reservoir_curve, (ReservoirCurve, type(None)))
        self._check_type(max_soft_bound, (SoftBound, type(None)))
        self._check_type(min_soft_bound, (SoftBound, type(None)))
        self._check_type(target_bound, (TargetBound, type(None)))
        self._check_type(initial_storage_percentage, (float, type(None)))

        if initial_storage_percentage is not None:
            self._check_float(initial_storage_percentage, lower_bound=0.0, upper_bound=1.0)

        self._capacity = capacity

        self._loss = loss
        self._reservoir_curve = reservoir_curve
        self._max_soft_bound = max_soft_bound
        self._min_soft_bound = min_soft_bound
        self._target_bound = target_bound
        self._initial_storage_percentage = initial_storage_percentage

        self._cost_terms: dict[str, ObjectiveCoefficient] = dict()

        if volume is None:
            volume = StockVolume()
        self._volume = volume

    def get_capacity(self) -> StockVolume:
        """Get the capacity."""
        return self._capacity

    def get_volume(self) -> StockVolume:
        """Get the volume."""
        return self._volume

    def add_cost_term(self, key: str, cost_term: ObjectiveCoefficient) -> None:
        """Add a cost term."""
        self._check_type(key, str)
        self._check_type(cost_term, ObjectiveCoefficient)
        self._cost_terms[key] = cost_term

    def get_cost_terms(self) -> dict[str, ObjectiveCoefficient]:
        """Get the cost terms."""
        return self._cost_terms

    def get_loss(self) -> Loss | None:
        """Get the loss."""
        return self._loss

    def set_loss(self, value: Loss | None) -> None:
        """Set the loss."""
        self._check_type(value, (Loss, type(None)))
        self._loss = value

    def get_reservoir_curve(self) -> ReservoirCurve | None:
        """Get the reservoir curve."""
        return self._reservoir_curve

    def set_reservoir_curve(self, value: ReservoirCurve | None) -> None:
        """Set the reservoir curve."""
        self._check_type(value, (ReservoirCurve, type(None)))
        self._reservoir_curve = value

    def get_max_soft_bound(self) -> SoftBound | None:
        """Get the max soft bound."""
        return self._max_soft_bound

    def set_max_soft_bound(self, value: SoftBound | None) -> None:
        """Set the max soft bound."""
        self._check_type(value, (SoftBound, type(None)))
        self._max_soft_bound = value

    def get_min_soft_bound(self) -> SoftBound | None:
        """Get the min soft bound."""
        return self._min_soft_bound

    def set_min_soft_bound(self, value: SoftBound | None) -> None:
        """Set the min soft bound."""
        self._check_type(value, (SoftBound, type(None)))
        self._min_soft_bound = value

    def get_target_bound(self) -> TargetBound | None:
        """Get the target bound."""
        return self._target_bound

    def set_target_bound(self, value: TargetBound | None) -> None:
        """Set the target bound."""
        self._check_type(value, (TargetBound, type(None)))
        self._target_bound = value

    def get_initial_storage_percentage(self) -> float | None:
        """Get the initial storage percentage (float in [0, 1])."""
        return self._initial_storage_percentage

    def set_initial_storage_percentage(self, value: float) -> None:
        """Set the initial storage percentage (float in [0, 1])."""
        self._check_float(value, lower_bound=0.0, upper_bound=1.0)
        self._initial_storage_percentage = value

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in attributes to loaders."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self.get_capacity())
        add_loaders_if(loaders, self.get_loss())
        add_loaders_if(loaders, self.get_volume())
        add_loaders_if(loaders, self.get_max_soft_bound())
        add_loaders_if(loaders, self.get_min_soft_bound())
        add_loaders_if(loaders, self.get_reservoir_curve())
        add_loaders_if(loaders, self.get_target_bound())

        for cost in self.get_cost_terms().values():
            add_loaders_if(loaders, cost)
