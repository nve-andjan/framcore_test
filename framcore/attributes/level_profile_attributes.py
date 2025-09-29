from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from framcore import Base
from framcore.expressions import (
    Expr,
    ensure_expr,
    get_level_value,
    get_profile_vector,
    get_timeindexes_from_expr,
    get_units_from_expr,
)
from framcore.expressions._get_constant_from_expr import _get_constant_from_expr
from framcore.querydbs import QueryDB
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex, TimeIndex
from framcore.timevectors import ConstantTimeVector, ReferencePeriod, TimeVector

if TYPE_CHECKING:
    from framcore import Model
    from framcore.loaders import Loader


# TODO: Name all abstract classes Abstract[clsname]
class LevelProfile(Base, ABC):
    """Attributes representing data the form level * profile + intercept."""

    # must be overwritten by subclass when otherwise
    # don't change the defaults
    _IS_ABSTRACT: bool = True
    _IS_STOCK: bool = False
    _IS_FLOW: bool = False
    _IS_NOT_NEGATIVE: bool = True
    _IS_MAX_AND_ZERO_ONE: bool = False

    # must be set by subclass when applicable
    _IS_INGOING: bool | None = None
    _IS_COST: bool | None = None
    _IS_UNITLESS: bool | None = None

    def __init__(
        self,
        level: Expr | TimeVector | str | None = None,
        profile: Expr | TimeVector | str | None = None,
        value: float | int | None = None,  # To support Price(value=20, unit="EUR/MWh")
        unit: str | None = None,
        level_shift: Expr | None = None,
        intercept: Expr | None = None,
        scale: Expr | None = None,
    ) -> None:
        """Validate all Expr fields."""
        self._assert_invariants()

        self._check_type(value, (float, int, type(None)))
        self._check_type(unit, (str, type(None)))
        self._check_type(level, (Expr, TimeVector, str, type(None)))
        self._check_type(profile, (Expr, TimeVector, str, type(None)))
        self._check_type(level_shift, (Expr, type(None)))
        self._check_type(intercept, (Expr, type(None)))
        self._check_type(scale, (Expr, type(None)))
        self._level = self._ensure_level_expr(level, value, unit)
        self._profile = self._ensure_profile_expr(profile)
        self._level_shift: Expr | None = None
        self._intercept: Expr | None = None
        self._scale: Expr | None = None

    def _assert_invariants(self) -> None:
        abstract = self._IS_ABSTRACT
        max_level_profile = self._IS_MAX_AND_ZERO_ONE
        stock = self._IS_STOCK
        flow = self._IS_FLOW
        unitless = self._IS_UNITLESS
        ingoing = self._IS_INGOING
        cost = self._IS_COST
        not_negative = self._IS_NOT_NEGATIVE

        assert not abstract, "Abstract types should only be used for type hints and checks."
        assert isinstance(max_level_profile, bool)
        assert isinstance(stock, bool)
        assert isinstance(flow, bool)
        assert isinstance(not_negative, bool)
        assert isinstance(ingoing, bool | type(None))
        assert isinstance(unitless, bool | type(None))
        assert isinstance(cost, bool | type(None))
        assert not (flow and stock)
        if flow or stock:
            assert not unitless, "flow and stock must have unit that is not None."
            assert not_negative, "flow and stock cannot have negative values."
        if ingoing is True:
            assert cost is None, "cost must be None when ingoing is True."
        if cost is True:
            assert ingoing is None, "ingoing must be None when cost is True."

        parent = super()
        if isinstance(parent, LevelProfile) and not parent._IS_ABSTRACT:  # noqa: SLF001
            self._assert_same_behaviour(parent)

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in expressions to loaders."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self.get_level())
        add_loaders_if(loaders, self.get_profile())

    def clear(self) -> None:
        """
        Set all internal fields to None.

        You may want to use this to get exogenous flow to use capacities instead of volume.
        """
        self._level = None
        self._profile = None
        self._level_shift = None
        self._intercept = None
        self._scale = None

    def is_stock(self) -> bool:
        """
        Return True if attribute is a stock variable.

        Return False if attribute is not a stock variable.
        """
        return self._IS_STOCK

    def is_flow(self) -> bool:
        """
        Return True if attribute is a flow variable.

        Return False if attribute is not a flow variable.
        """
        return self._IS_FLOW

    def is_not_negative(self) -> bool:
        """
        Return True if attribute is not allowed to have negative values.

        Return False if attribute can have both positive and negative values.
        """
        return self._IS_NOT_NEGATIVE

    def is_max_and_zero_one(self) -> bool:
        """
        When True level should be max (not average) and corresponding profile should be zero_one (not mean_one).

        When False level should be average (not max) and corresponding profile should be mean_one (not zero_one).
        """
        return self._IS_MAX_AND_ZERO_ONE

    def is_ingoing(self) -> bool | None:
        """
        Return True if attribute is ingoing.

        Return True if attribute is outgoing.

        Return None if not applicable.
        """
        return self._IS_INGOING

    def is_cost(self) -> bool | None:
        """
        Return True if attribute is objective function cost coefficient.

        Return False if attribute is objective function revenue coefficient.

        Return None if not applicable.
        """
        return self._IS_COST

    def is_unitless(self) -> bool | None:
        """
        Return True if attribute is known to be unitless.

        Return False if attribute is known to have a unit that is not None.

        Return None if not applicable.
        """
        return self._IS_UNITLESS

    def has_level(self) -> bool:
        """Return True if get_level will return value not None."""
        return (self._level is not None) or (self._level_shift is not None)

    def has_profile(self) -> bool:
        """Return True if get_profile will return value not None."""
        return self._profile is not None

    def has_intercept(self) -> bool:
        """Return True if get_intercept will return value not None."""
        return self._intercept is not None

    def copy_from(self, other: LevelProfile) -> None:
        """Copy fields from other."""
        self._check_type(other, LevelProfile)
        self._assert_same_behaviour(other)
        self._level = other._level
        self._profile = other._profile
        self._level_shift = other._level_shift
        self._intercept = other._intercept
        self._scale = other._scale

    def get_level(self) -> Expr | None:
        """Get level part of (level * profile + intercept)."""
        level = self._level

        if level is None:
            return None

        if level.is_leaf():
            level = Expr(
                src=level.get_src(),
                operations=level.get_operations(expect_ops=False, copy_list=True),
                is_stock=level.is_stock(),
                is_flow=level.is_flow(),
                is_level=True,
                is_profile=False,
                profile=self._profile,  # TODO: not always?
            )

        if self._level_shift is not None:
            level += self._level_shift

        if self._scale is not None:
            level *= self._scale

        return level

    def set_level(self, level: Expr | TimeVector | str | None) -> None:
        """Set level part of (level * profile + intercept)."""
        self._check_type(level, (Expr, TimeVector, str, type(None)))
        self._level = self._ensure_level_expr(level)

    def get_profile(self) -> Expr | None:
        """Get profile part of (level * profile + intercept)."""
        return self._profile

    def set_profile(self, profile: Expr | TimeVector | str | None) -> None:
        """Set profile part of (level * profile + intercept)."""
        self._check_type(profile, (Expr, TimeVector, str, type(None)))
        self._profile = self._ensure_profile_expr(profile)

    def get_intercept(self) -> Expr | None:
        """Get intercept part of (level * profile + intercept)."""
        intercept = self._intercept
        if self._scale is not None:
            intercept *= self._scale
        return intercept

    def set_intercept(self, value: Expr | None) -> None:
        """Set intercept part of (level * profile + intercept)."""
        self._check_type(value, (Expr, type(None)))
        if value is not None:
            self._check_level_expr(value)
        self._intercept = value

    def get_level_unit_set(
        self,
        db: QueryDB | Model,
    ) -> set[TimeIndex]:
        """
        Return set with all units behind level expression.

        Useful for discovering valid unit input to get_level_value.
        """
        if not self.has_level():
            return set()
        return get_units_from_expr(db, self.get_level())

    def get_profile_timeindex_set(
        self,
        db: QueryDB | Model,
    ) -> set[TimeIndex]:
        """
        Return set with all TimeIndex behind profile expression.

        Can be used to run optimized queries, i.e. not asking for
        finer time resolutions than necessary.
        """
        if not self.has_profile():
            return set()
        return get_timeindexes_from_expr(db, self.get_profile())

    def get_scenario_vector(
        self,
        db: QueryDB | Model,
        scenario_horizon: FixedFrequencyTimeIndex,
        level_period: SinglePeriodTimeIndex,
        unit: str | None,
        is_float32: bool = True,
    ) -> NDArray:
        """Return vector with values along the given scenario horizon using level over level_period."""
        return self._get_scenario_vector(db, scenario_horizon, level_period, unit, is_float32)

    def get_data_value(
        self,
        db: QueryDB | Model,
        scenario_horizon: FixedFrequencyTimeIndex,
        level_period: SinglePeriodTimeIndex,
        unit: str | None,
        is_max_level: bool | None = None,
    ) -> float:
        """Return float for level_period."""
        return self._get_data_value(db, scenario_horizon, level_period, unit, is_max_level)

    def shift_intercept(self, value: float, unit: str | None) -> None:
        """Modify the intercept part of (level*profile + intercept) of an attribute by adding a constant value."""
        expr = ensure_expr(
            ConstantTimeVector(self._ensure_float(value), unit=unit, is_max_level=False),
            is_level=True,
            is_profile=False,
            is_stock=self._IS_STOCK,
            is_flow=self._IS_FLOW,
            profile=None,
        )
        if self._intercept is None:
            self._intercept = expr
        else:
            self._intercept += expr

    def shift_level(
        self,
        value: float | int,
        unit: str | None = None,
        reference_period: ReferencePeriod | None = None,
        is_max_level: bool | None = None,
        use_profile: bool = False,
    ) -> None:
        """Modify the level part of (level*profile + intercept) of an attribute by adding a constant value."""
        self._check_type(value, (float, int))
        self._check_type(unit, (str, type(None)))
        self._check_type(reference_period, (ReferencePeriod, type(None)))
        self._check_type(is_max_level, (bool, type(None)))
        self._check_type(use_profile, bool)

        if is_max_level is None:
            is_max_level = self._IS_MAX_AND_ZERO_ONE

        expr = ensure_expr(
            ConstantTimeVector(
                self._ensure_float(value),
                unit=unit,
                is_max_level=is_max_level,
                reference_period=reference_period,
            ),
            is_level=True,
            is_profile=False,
            is_stock=self._IS_STOCK,
            is_flow=self._IS_FLOW,
            profile=self._profile if use_profile else None,
        )
        if self._level_shift is None:
            self._level_shift = expr
        else:
            self._level_shift += expr

    def scale(self, value: float | int) -> None:
        """Modify the value (level*profile + intercept) of an attribute by multiplying with a constant value."""
        expr = ensure_expr(
            ConstantTimeVector(self._ensure_float(value), unit=None, is_max_level=False),
            is_level=True,
            is_profile=False,
            profile=None,
        )
        if self._scale is None:
            self._scale = expr
        else:
            self._scale *= expr

    def _ensure_level_expr(
        self,
        level: Expr | str | TimeVector | None,
        value: float | int | None = None,
        unit: str | None = None,
        reference_period: ReferencePeriod | None = None,
    ) -> Expr | None:
        if value is not None:
            level = ConstantTimeVector(
                scalar=float(value),
                unit=unit,
                is_max_level=self._IS_MAX_AND_ZERO_ONE,
                is_zero_one_profile=None,
                reference_period=reference_period,
            )
        if level is None:
            return None

        if isinstance(level, Expr):
            self._check_level_expr(level)
            return level

        return Expr(
            src=level,
            is_flow=self._IS_FLOW,
            is_stock=self._IS_STOCK,
            is_level=True,
            is_profile=False,
            profile=None,
        )

    def _check_level_expr(self, expr: Expr) -> None:
        assert expr.is_stock() == self._IS_STOCK
        assert expr.is_flow() == self._IS_FLOW
        assert expr.is_level() is True
        assert expr.is_profile() is False

    def _check_profile_expr(self, expr: Expr) -> None:
        assert expr.is_stock() is False
        assert expr.is_flow() is False
        assert expr.is_level() is False
        assert expr.is_profile() is True

    def _ensure_profile_expr(
        self,
        value: Expr | str | TimeVector | None,
    ) -> Expr | None:
        if value is None:
            return None

        if isinstance(value, Expr):
            self._check_profile_expr(value)
            return value

        return Expr(
            src=value,
            is_flow=False,
            is_stock=False,
            is_level=False,
            is_profile=True,
            profile=None,
        )

    def _get_data_value(
        self,
        db: QueryDB,
        scenario_horizon: FixedFrequencyTimeIndex,
        level_period: SinglePeriodTimeIndex,
        unit: str | None,
        is_max_level: bool | None,
    ) -> float:
        # NB! don't type check db, as this is done in get_level_value and get_profile_vector
        self._check_type(scenario_horizon, FixedFrequencyTimeIndex)
        self._check_type(level_period, SinglePeriodTimeIndex)
        self._check_type(unit, (str, type(None)))
        self._check_type(is_max_level, (bool, type(None)))

        level_expr = self.get_level()

        if is_max_level is None:
            is_max_level = self._IS_MAX_AND_ZERO_ONE

        self._check_type(level_expr, (Expr, type(None)))
        assert isinstance(level_expr, Expr), "Attribute level Expr is None. Have you called Solver.solve yet?"

        level_value = get_level_value(
            expr=level_expr,
            db=db,
            scen_dim=scenario_horizon,
            data_dim=level_period,
            unit=unit,
            is_max=is_max_level,
        )

        intercept = None
        if self._intercept is not None:
            intercept = _get_constant_from_expr(
                self._intercept,
                db,
                unit=unit,
                data_dim=level_period,
                scen_dim=scenario_horizon,
                is_max=is_max_level,
            )

        if intercept is None:
            return level_value

        return level_value + intercept

    def _get_scenario_vector(
        self,
        db: QueryDB | Model,
        scenario_horizon: FixedFrequencyTimeIndex,
        level_period: SinglePeriodTimeIndex,
        unit: str | None,
        is_float32: bool = True,
    ) -> NDArray:
        """Return vector with values along the given scenario horizon using level over level_period."""
        # NB! don't type check db, as this is done in get_level_value and get_profile_vector
        self._check_type(scenario_horizon, FixedFrequencyTimeIndex)
        self._check_type(level_period, SinglePeriodTimeIndex)
        self._check_type(unit, (str, type(None)))
        self._check_type(is_float32, bool)

        level_expr = self.get_level()

        self._check_type(level_expr, (Expr, type(None)))
        assert isinstance(level_expr, Expr), "Attribute level Expr is None. Have you called Solver.solve yet?"

        level_value = get_level_value(
            expr=level_expr,
            db=db,
            scen_dim=scenario_horizon,
            data_dim=level_period,
            unit=unit,
            is_max=self._IS_MAX_AND_ZERO_ONE,
        )

        profile_expr = self.get_profile()

        if profile_expr is None:
            profile_vector = np.ones(
                scenario_horizon.get_num_periods(),
                dtype=np.float32 if is_float32 else np.float64,
            )
        else:
            profile_vector = get_profile_vector(
                expr=profile_expr,
                db=db,
                scen_dim=scenario_horizon,
                data_dim=level_period,
                is_zero_one=self._IS_MAX_AND_ZERO_ONE,
                is_float32=is_float32,
            )

        intercept = None
        if self._intercept is not None:
            intercept = _get_constant_from_expr(
                self._intercept,
                db,
                unit=unit,
                data_dim=level_period,
                scen_dim=scenario_horizon,
                is_max=self._IS_MAX_AND_ZERO_ONE,
            )

        if intercept is None:
            return level_value * profile_vector

        return level_value * profile_vector + intercept

    def _has_same_behaviour(self, other: LevelProfile) -> bool:
        return all(
            (
                self._IS_FLOW == other._IS_FLOW,
                self._IS_STOCK == other._IS_STOCK,
                self._IS_NOT_NEGATIVE == other._IS_NOT_NEGATIVE,
                self._IS_MAX_AND_ZERO_ONE == other._IS_MAX_AND_ZERO_ONE,
                self._IS_INGOING == other._IS_INGOING,
                self._IS_COST == other._IS_COST,
                self._IS_UNITLESS == other._IS_UNITLESS,
            ),
        )

    def _assert_same_behaviour(self, other: LevelProfile) -> None:
        if not self._has_same_behaviour(other):
            message = f"Not same behaviour for {self} and {other}"
            raise ValueError(message)

    def __eq__(self, other) -> bool:  # noqa: ANN001
        """Return True if other is equal to self."""
        if not isinstance(other, LevelProfile):
            return False
        if not self._has_same_behaviour(other):
            return False
        return all(
            (
                self._level == other._level,
                self._profile == other._profile,
                self._level_shift == other._level_shift,
                self._intercept == other._intercept,
                self._scale == other._scale,
            ),
        )

    def __hash__(self) -> int:
        """Compute hash of self."""
        return hash(
            (
                type(self).__name__,
                self._level,
                self._profile,
                self._level_shift,
                self._intercept,
                self._scale,
            ),
        )


# Abstract subclasses intended type hints and checks


class FlowVolume(LevelProfile):
    """Represents a flow volume attribute, indicating that the attribute is a flow variable."""

    _IS_FLOW = True


class Coefficient(LevelProfile):
    """Represents a coefficient attribute, used as a base class for various coefficient types."""

    pass


class ArrowCoefficient(Coefficient):
    """Represents an arrow coefficient attribute, used for efficiency, loss, and conversion coefficients."""

    pass


class ShaddowPrice(Coefficient):
    """Represents a shadow price attribute, indicating that the attribute has unit might be negative."""

    _IS_UNITLESS = False
    _IS_NOT_NEGATIVE = False


class ObjectiveCoefficient(Coefficient):
    """Represents an objective coefficient attribute, indicating cost or revenue coefficients in the objective function."""

    _IS_UNITLESS = False
    _IS_NOT_NEGATIVE = False


# concrete subclasses intended for final use


class Price(ShaddowPrice):
    """Represents a price attribute, inheriting from ShaddowPrice."""

    _IS_ABSTRACT = False


class WaterValue(ShaddowPrice):
    """Represents a water value attribute, inheriting from ShaddowPrice."""

    _IS_ABSTRACT = False


class Cost(ObjectiveCoefficient):
    """Represents a cost attribute, indicating cost coefficients in the objective function."""

    _IS_ABSTRACT = False
    _IS_COST = True


class ReservePrice(ObjectiveCoefficient):
    """Represents a reserve price attribute, indicating revenue coefficients in the objective function."""

    _IS_ABSTRACT = False
    _IS_COST = False


class Elasticity(Coefficient):  # TODO: How do this work?
    """Represents an elasticity coefficient attribute, indicating a unitless coefficient."""

    _IS_ABSTRACT = False
    _IS_UNITLESS = True


class Proportion(Coefficient):  # TODO: How do this work?
    """Represents a proportion coefficient attribute, indicating a unitless coefficient."""

    _IS_ABSTRACT = False
    _IS_UNITLESS = True


class Hours(Coefficient):  # TODO: How do this work?
    """Represents an hours coefficient attribute, indicating a time-related coefficient."""

    _IS_ABSTRACT = False


class Efficiency(ArrowCoefficient):
    """Represents an efficiency coefficient attribute, indicating a unitless coefficient."""

    _IS_ABSTRACT = False
    _IS_UNITLESS = True


class Loss(ArrowCoefficient):
    """Represents a loss coefficient attribute, indicating a unitless coefficient."""

    _IS_ABSTRACT = False
    _IS_UNITLESS = True


class Conversion(ArrowCoefficient):
    """Represents a conversion coefficient attribute, used for conversion factors in the model."""

    _IS_ABSTRACT = False


class AvgFlowVolume(FlowVolume):
    """Represents an average flow volume attribute, indicating a flow variable with average values."""

    _IS_ABSTRACT = False


class MaxFlowVolume(FlowVolume):
    """Represents a maximum flow volume attribute, indicating a flow variable with maximum values."""

    _IS_ABSTRACT = False
    _IS_MAX_AND_ZERO_ONE = True


class StockVolume(LevelProfile):
    """Represents a stock volume attribute, indicating a stock variable with maximum values."""

    _IS_ABSTRACT = False
    _IS_STOCK = True
    _IS_MAX_AND_ZERO_ONE = True
