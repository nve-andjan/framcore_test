from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from framcore import Base
from framcore.attributes import Conversion, Efficiency, Loss
from framcore.querydbs import QueryDB
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex, TimeIndex

if TYPE_CHECKING:
    from framcore import Model
    from framcore.loaders import Loader


class Arrow(Base):
    """
    Arrow class is used by Flows to represent contribution of its commodity to Nodes.

    coefficient = conversion * (1 / efficiency) * (1 - loss)
    """

    def __init__(
        self,
        node: str,
        is_ingoing: bool,
        conversion: Conversion | None = None,
        efficiency: Efficiency | None = None,
        loss: Loss | None = None,
    ) -> None:
        """Initialize the Arrow class."""
        self._check_type(node, str)
        self._check_type(is_ingoing, bool)
        self._check_type(conversion, (Conversion, type(None)))
        self._check_type(efficiency, (Efficiency, type(None)))
        self._check_type(loss, (Loss, type(None)))
        self._node = node
        self._is_ingoing = is_ingoing
        self._conversion = conversion
        self._efficiency = efficiency
        self._loss = loss

    def get_node(self) -> str:
        """Get the node the arrow is pointing to."""
        return self._node

    def set_node(self, node: str) -> None:
        """Set the node the arrow is pointing to."""
        self._check_type(node, str)
        self._node = node

    def is_ingoing(self) -> bool:
        """
        Return True if arrow is ingoing.

        Ingoing means the flow variable supplies to node.
        Outgoing means the flow variable takes out of node.
        """
        return self._is_ingoing

    def get_conversion(self) -> Conversion | None:
        """Get the conversion."""
        return self._conversion

    def set_conversion(self, value: Conversion | None) -> None:
        """Set the conversion."""
        self._check_type(value, Conversion, type(None))
        self._conversion = value

    def get_efficiency(self) -> Efficiency | None:
        """Get the efficiency."""
        return self._efficiency

    def set_efficiency(self, value: Efficiency | None) -> None:
        """Set the efficiency."""
        self._check_type(value, Efficiency, type(None))
        self._efficiency = value

    def get_loss(self) -> Loss | None:
        """Get the loss."""
        return self._loss

    def set_loss(self, value: Loss | None) -> None:
        """Set the loss."""
        self._check_type(value, Loss, type(None))
        self._loss = value

    def has_profile(self) -> bool:
        """Return True if any of conversion, efficiency or loss has profile."""
        if self._conversion is not None and self._conversion.has_profile():
            return True
        if self._efficiency is not None and self._efficiency.has_profile():
            return True
        return bool(self._loss is not None and self._loss.has_profile())

    def get_conversion_unit_set(
        self,
        db: QueryDB | Model,
    ) -> set[str]:
        """Get set of units behind conversion level expr (if any)."""
        if self._conversion is None:
            return set()
        return self._conversion.get_level_unit_set()

    def get_profile_timeindex_set(
        self,
        db: QueryDB | Model,
    ) -> set[TimeIndex]:
        """
        Get set of timeindexes behind profile.

        Can be used to run optimized queries, i.e. not asking for
        finer time resolutions than necessary.
        """
        if self.has_profile() is None:
            return set()
        s = set()
        if self._conversion is not None:
            s.update(self._conversion.get_profile_timeindex_set(db))
        if self._loss is not None:
            s.update(self._loss.get_profile_timeindex_set(db))
        if self._efficiency is not None:
            s.update(self._efficiency.get_profile_timeindex_set(db))
        return s

    def get_scenario_vector(
        self,
        db: QueryDB | Model,
        scenario_horizon: FixedFrequencyTimeIndex,
        level_period: SinglePeriodTimeIndex,
        unit: str | None,
        is_float32: bool = True,
    ) -> NDArray:
        """Return vector with values along the given scenario horizon using level over level_period."""
        conversion_vector = None
        efficiency_vector = None
        loss_vector = None
        conversion_value = None
        efficiency_value = None
        loss_value = None

        if self._conversion is not None:
            if self._conversion.has_profile():
                conversion_vector = self._conversion.get_scenario_vector(
                    db=db,
                    scenario_horizon=scenario_horizon,
                    level_period=level_period,
                    unit=unit,
                    is_float32=is_float32,
                )
            elif self._conversion.has_level():
                conversion_value = self._conversion.get_data_value(
                    db=db,
                    scenario_horizon=scenario_horizon,
                    level_period=level_period,
                    unit=unit,
                )
                conversion_value = float(conversion_value)

        if self._efficiency is not None:
            if self._efficiency.has_profile():
                efficiency_vector = self._efficiency.get_scenario_vector(
                    db=db,
                    scenario_horizon=scenario_horizon,
                    level_period=level_period,
                    unit=None,
                    is_float32=is_float32,
                )
            elif self._efficiency.has_level():
                efficiency_value = self._efficiency.get_data_value(
                    db=db,
                    scenario_horizon=scenario_horizon,
                    level_period=level_period,
                    unit=None,
                )
                efficiency_value = float(efficiency_value)

        if self._loss is not None:
            if self._loss.has_profile():
                loss_vector = self._loss.get_scenario_vector(
                    db=db,
                    scenario_horizon=scenario_horizon,
                    level_period=level_period,
                    unit=None,
                    is_float32=is_float32,
                )
            elif self._loss.has_level():
                loss_value = self._loss.get_data_value(
                    db=db,
                    scenario_horizon=scenario_horizon,
                    level_period=level_period,
                    unit=None,
                )
                loss_value = float(loss_value)

        if conversion_value is not None:
            assert conversion_value >= 0, f"Arrow with invalid conversion ({conversion_value}): {self}"
            out = conversion_value
        else:
            out = 1.0

        if efficiency_value is not None:
            assert efficiency_value > 0, f"Arrow with invalid efficiency ({efficiency_value}): {self}"
            out = out / efficiency_value

        if loss_value is not None:
            assert loss_value >= 0 or loss_value < 1, f"Arrow with invalid loss ({loss_value}): {self}"
            out = out - out * loss_value

        if conversion_vector is not None:
            np.multiply(conversion_vector, out, out=conversion_vector)
            out = conversion_vector

        if efficiency_vector is not None:
            if isinstance(out, float):
                np.divide(out, efficiency_vector, out=efficiency_vector)
                out = efficiency_vector
            else:
                np.divide(out, efficiency_vector, out=out)

        if loss_vector is not None:
            if isinstance(out, float):
                np.multiply(out, loss_vector, out=loss_vector)
                np.subtract(out, loss_vector, out=loss_vector)
                out = loss_vector
            else:
                np.multiply(out, loss_vector, out=loss_vector)
                np.subtract(out, loss_vector, out=out)

        if isinstance(out, float):
            num_periods = scenario_horizon.get_num_periods()
            vector = np.ones(num_periods, dtype=np.float32 if is_float32 else np.float64)
            vector.fill(out)
            return vector

        return out

    def get_data_value(
        self,
        db: QueryDB | Model,
        scenario_horizon: FixedFrequencyTimeIndex,
        level_period: SinglePeriodTimeIndex,
        unit: str | None,
        is_max_level: bool = False,
    ) -> float:
        """Return float for level_period."""
        conversion_value = None
        efficiency_value = None
        loss_value = None

        if self._conversion is not None and self._conversion.has_level():
            conversion_value = self._conversion.get_data_value(
                db=db,
                scenario_horizon=scenario_horizon,
                level_period=level_period,
                unit=unit,
                is_max_level=is_max_level,
            )
            conversion_value = float(conversion_value)

        if self._efficiency is not None and self._efficiency.has_level():
            efficiency_value = self._efficiency.get_data_value(
                db=db,
                scenario_horizon=scenario_horizon,
                level_period=level_period,
                unit=None,
                is_max_level=is_max_level,
            )
            efficiency_value = float(efficiency_value)

        if self._loss is not None and self._loss.has_level():
            loss_value = self._loss.get_data_value(
                db=db,
                scenario_horizon=scenario_horizon,
                level_period=level_period,
                unit=None,
                is_max_level=is_max_level,
            )
            loss_value = float(loss_value)

        if conversion_value is not None:
            assert conversion_value >= 0, f"Arrow with invalid conversion ({conversion_value}): {self}"
            out = conversion_value
        else:
            out = 1.0

        if efficiency_value is not None:
            assert efficiency_value > 0, f"Arrow with invalid efficiency ({efficiency_value}): {self}"
            out = out / efficiency_value

        if loss_value is not None:
            assert loss_value >= 0 or loss_value < 1, f"Arrow with invalid loss ({loss_value}): {self}"
            out = out - out * loss_value

        return out

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in attributes to loaders."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self.get_conversion())
        add_loaders_if(loaders, self.get_loss())
        add_loaders_if(loaders, self.get_efficiency())
