from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.expressions._get_constant_from_expr import _get_constant_from_expr
from framcore.expressions._utils import _load_model_and_create_model_db
from framcore.expressions.units import get_unit_conversion_factor
from framcore.querydbs import QueryDB
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex, TimeIndex
from framcore.timevectors import TimeVector

if TYPE_CHECKING:
    from framcore import Model


def get_level_value(
    expr: Expr,
    db: QueryDB | Model,
    unit: str | None,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    is_max: bool,
) -> float:
    """
    Evaluate expr representing a (possibly aggregated) level.

    The follwing will be automatically handeled for you:
      - conversion to requested unit
      - conversion to requested reference period
      - conversion to requested level type
      - fetching from different data objecs

    expr = sum(scale[i] * level[i]) where

        scale[i] >= 0 and is unitless
        level[i] is a unitful level expr

        level[i] is either "avg" or "max" type of level

        if "avg", it has a reference period (startyear, startyear + numyears) and a corresponding
        "mean_one" profile, for which mean(values) = 1 for values covering the reference period

        "avg" and "max" level type must be converted to the same standard to be added correctly.

        Two "avg" types with different reference period must be converted to same reference period
        to be added correctly.

        The query parameter scen_dim tells which reference period to convert to.

        The query parameter is_max tells which level type to convert to.
    """
    db = _load_model_and_create_model_db(db)
    return _get_level_value(expr, db, unit, data_dim, scen_dim, is_max)


def get_profile_vector(
    expr: Expr,
    db: QueryDB | Model,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    is_zero_one: bool,
    is_float32: bool = True,
) -> NDArray:
    """
    Evaluate expr representing a (possibly aggregated) profile.

    expr = sum(weight[i] * profile[i]) where

        weight[i] >= 0 and is unitless
        profile[i] is a unitless profile expr

        profile[i] is either "zero_one" or "mean_one" type of profile

        "zero_one" and "mean_one" profile type must be converted to the
        same standard to be added correctly.

        The query parameter data_dim is used to compute weight[i].

        The query parameter scen_dim specifies the out vector dimension.

        The query parameter is_zero_one tells which profile type the output
        vector should be converted to.
    """
    db = _load_model_and_create_model_db(db)
    # TODO: Implement checks cleaner
    return _get_profile_vector(expr, db, data_dim, scen_dim, is_zero_one, is_float32)


def get_units_from_expr(db: QueryDB | Model, expr: Expr) -> set[str]:
    """Find all units behind an expression. Useful for queries involving conversion factors."""
    db = _load_model_and_create_model_db(db)

    units: set[str] = set()

    _recursively_update_units(units, db, expr)

    return units


def get_timeindexes_from_expr(db: QueryDB | Model, expr: Expr) -> set[TimeIndex]:
    """
    Find all timeindexes behind an expression.

    Useful for optimized queries (not asking for more data than necessary).
    """
    db = _load_model_and_create_model_db(db)

    timeindexes: set[TimeIndex] = set()

    _recursively_update_timeindexes(timeindexes, db, expr)

    return timeindexes


def _get_level_value(
    expr: Expr,
    db: QueryDB,
    unit: str | None,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    is_max: bool,
) -> float:
    # TODO: Implement checks cleaner
    assert isinstance(expr, Expr), f"{expr}"

    cache_key = ("_get_constant_from_expr", expr, unit, data_dim, scen_dim, is_max)
    if db.has_key(cache_key):
        return db.get(cache_key)
    t0 = time.perf_counter()
    output_value = _get_constant_from_expr(expr, db, unit, data_dim, scen_dim, is_max)
    t1 = time.perf_counter()
    db.put(cache_key, output_value, elapsed_seconds=t1 - t0)

    return output_value


def _get_profile_vector(
    expr: Expr,
    db: QueryDB,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    is_zero_one: bool,
    is_float32: bool = True,
) -> NDArray:
    assert isinstance(expr, Expr), f"{expr}"

    if expr.is_leaf():
        src = expr.get_src()

        if isinstance(src, str):
            obj = db.get(src)
        else:
            assert isinstance(src, TimeVector)
            obj = src

        if isinstance(obj, Expr):
            assert obj.is_profile(), f"{obj}"
            return _get_profile_vector(obj, db, data_dim, scen_dim, is_zero_one, is_float32)

        assert isinstance(obj, TimeVector)
        cache_key = ("_get_profile_vector_from_timevector", obj, data_dim, scen_dim, is_zero_one, is_float32)
        if db.has_key(cache_key):
            vector: NDArray = db.get(cache_key)
            return vector.copy()
        t0 = time.perf_counter()
        vector = _get_profile_vector_from_timevector(obj, scen_dim, is_zero_one, is_float32)
        t1 = time.perf_counter()
        db.put(cache_key, vector, elapsed_seconds=t1 - t0)
        return vector

    ops, args = expr.get_operations(expect_ops=True, copy_list=False)

    tmp = np.zeros(scen_dim.get_num_periods(), dtype=np.float32 if is_float32 else np.float64)

    if "+" in ops:
        out = _get_profile_vector(args[0], db, data_dim, scen_dim, is_zero_one, is_float32)
        for op, arg in zip(ops, args[1:], strict=True):
            assert op == "+", f"{ops}  {args}"
            tmp = _get_profile_vector(arg, db, data_dim, scen_dim, is_zero_one, is_float32)
            np.add(out, tmp, out=out)
        return out

    if not all(op == "*" for op in ops):
        message = f"Expected w1*w2*..*wn*profile. Got operations {ops} for expr {expr}"
        raise ValueError(message)

    profiles = [arg for arg in args if arg.is_profile()]
    weights = [arg for arg in args if not arg.is_profile()]
    if len(profiles) != 1:
        message = f"Got {len(profiles)} profiles in expr {expr}"
        raise ValueError(message)
    total_weight = 0.0
    is_max = False  # use avg-values to calculate weights
    for weight_expr in weights:
        total_weight += _get_constant_from_expr(weight_expr, db, None, data_dim, scen_dim, is_max)
    out = _get_profile_vector(profiles[0], db, data_dim, scen_dim, is_zero_one, is_float32)
    np.multiply(out, total_weight, out=out)
    return out


def _get_profile_vector_from_timevector(
    timevector: TimeVector,
    scen_dim: FixedFrequencyTimeIndex,
    target_is_zero_one: bool,
    is_float32: bool,
) -> NDArray:
    out = np.zeros(scen_dim.get_num_periods(), dtype=np.float32 if is_float32 else np.float64)

    tv_is_zero_one = timevector.is_zero_one_profile()  # OPPGAVE endrer TimeVector-API
    assert isinstance(tv_is_zero_one, bool)
    assert isinstance(timevector.get_unit(), type(None))
    values = timevector.get_vector(is_float32)
    timeindex = timevector.get_timeindex()
    timeindex.write_into_fixed_frequency(out, scen_dim, values)

    # CASE HANDLED:
    # Both profiles are mean one within their respective reference periods.
    # We convert timevector ref period to target reference period by
    # making sure the mean value of 'out' is 1 within the target reference period.
    if not target_is_zero_one and not tv_is_zero_one:
        target_ref_period = scen_dim.get_reference_period()
        tv_ref_period = timevector.get_reference_period()
        if target_ref_period != tv_ref_period:
            tv_target_ref_period_mean = timeindex.get_period_average(
                vector=values,
                start_time=scen_dim.get_start_time(),
                duration=scen_dim.get_period_duration() * scen_dim.get_num_periods(),
                is_52_week_years=scen_dim.is_52_week_years(),
            )

            if tv_target_ref_period_mean == 0.0:
                message = f"TimeVector {timevector} has invalid mean value of 0.0 for target reference period {target_ref_period}."
                raise ValueError(message)

            np.multiply(out, 1 / tv_target_ref_period_mean, out=out)

    # TODO: Bør heller "ikke stole på"
    if target_is_zero_one != tv_is_zero_one:
        if target_is_zero_one:
            np.multiply(out, 1 / out.max(), out=out)  # convert to zero one profile standard
        elif not np.all(out == 0):
            np.multiply(out, 1 / out.mean(), out=out)  # convert to mean one profile standard")

    # TODO: handle different ref periods if is_avg
    return out


def _recursively_update_units(units: set[str], db: QueryDB, expr: Expr) -> None:
    if expr.is_leaf():
        src = expr.get_src()

        obj = src if isinstance(src, TimeVector) else db.get(key=src)

        if isinstance(obj, Expr):
            _recursively_update_units(units, db, obj)
        elif isinstance(obj, Curve):
            message = "Not yet implemented for Curve objects."
            raise NotImplementedError(message)
        elif isinstance(obj, TimeVector):
            unit = obj.get_unit()
            if unit is not None:
                units.add(unit)
        else:
            message = f"Got unexpected object {obj}."
            raise RuntimeError(message)
    __, args = expr.get_operations(expect_ops=False, copy_list=False)
    for arg in args:
        _recursively_update_units(units, db, arg)


def _recursively_update_units(units: set[str], db: QueryDB, expr: Expr) -> None:
    if expr.is_leaf():
        src = expr.get_src()
        obj = src if isinstance(src, TimeVector) else db.get(key=src)
        if isinstance(obj, Expr):
            _recursively_update_units(units, db, obj)
        elif isinstance(obj, Curve):
            message = "Not yet implemented for Curve objects."
            raise NotImplementedError(message)
        elif isinstance(obj, TimeVector):
            unit = obj.get_unit()
            if unit is not None:
                units.add(unit)
        else:
            message = f"Got unexpected object {obj}."
            raise RuntimeError(message)
    __, args = expr.get_operations(expect_ops=False, copy_list=False)
    for arg in args:
        _recursively_update_units(units, db, arg)


def _recursively_update_timeindexes(timeindexes: set[TimeIndex], db: QueryDB, expr: Expr) -> None:
    if expr.is_leaf():
        src = expr.get_src()
        obj = src if isinstance(src, TimeVector) else db.get(key=src)
        if isinstance(obj, Expr):
            _recursively_update_timeindexes(timeindexes, db, obj)
        elif isinstance(obj, Curve):
            pass
        elif isinstance(obj, TimeVector):
            timeindex = obj.get_timeindex()
            if timeindex is not None:
                timeindexes.add(timeindex)
        else:
            message = f"Got unexpected object {obj}."
            raise RuntimeError(message)
    __, args = expr.get_operations(expect_ops=False, copy_list=False)
    for arg in args:
        _recursively_update_timeindexes(timeindexes, db, arg)


def _get_level_value_from_timevector(  # noqa: C901
    timevector: TimeVector,
    db: QueryDB,
    target_unit: str | None,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    target_is_max: bool,
    profile_expr: Expr | None,
) -> float:
    tv_is_max = timevector.is_max_level()  # OPPGAVE endrer TimeVector-API

    is_float32 = True

    values = timevector.get_vector(is_float32)  # OPPGAVE endrer TimeVector-API

    # if DEFENSIVE_MODE:  # global i data-mng-modul
    # assert isinstance(values, np.ndarray)
    # assert len(values.shape) == 1

    timeindex = timevector.get_timeindex()
    from_unit = timevector.get_unit()

    starttime = data_dim.get_start_time()  # OPPGAVE endrer ConstantTimeIndex-API?
    timedelta = data_dim.get_period_duration()  # OPPGAVE endrer ConstantTimeIndex-API?
    scalar = timeindex.get_period_average(values, starttime, timedelta, data_dim.is_52_week_years())

    if from_unit is not None and target_unit is not None:
        scalar *= get_unit_conversion_factor(from_unit, target_unit)
    elif from_unit is None and target_unit is None:
        pass
    else:
        message = "Mismatch between 'target_unit' 'from_unit'. One is None while the other is not."  # more descriptive?
        raise ValueError(message)

    if not target_is_max:
        if not tv_is_max:  # from avg to avg
            avg_level = scalar
            tv_ref_period = timevector.get_reference_period()  # Vi lar ReferencePeriod være tidsindex som en lang periode
            if tv_ref_period is None:
                assert profile_expr is None, f"Timevector {timevector} has no reference period, profile_expr must therefore be None."
                return avg_level  # avg level fra timevector uten ref periode
            target_ref_period = scen_dim.get_reference_period()
            if target_ref_period is None:
                message = f"No reference period for scen_dim {scen_dim}"
                raise ValueError(message)
            if tv_ref_period != target_ref_period:
                # if DEFENSIVE_MODE:
                # tv_ref_period_mean = get_profile_vector(profile_expr, db, data_dim, tv_ref_period, is_float32, is_zero_one=False)
                # assert tv_ref_period_mean.size == 1
                # assert tv_ref_period_mean[0] == 1
                assert profile_expr, f"Profile Expr is None for TimeVector {timevector} when it should exist"
                tv_target_ref_period_mean = get_profile_vector(
                    profile_expr,
                    db,
                    data_dim,
                    scen_dim.copy_as_reference_period(target_ref_period),
                    is_zero_one=False,
                    is_float32=is_float32,
                )
                assert tv_target_ref_period_mean.size == 1
                avg_level = tv_target_ref_period_mean[0] * avg_level
            return avg_level
        # timevector fra max til avg
        max_level = scalar
        assert timevector.get_reference_period() is None

        zero_one_profile_vector_mean = 1
        if profile_expr is not None:  # only try to get profile if the level is actually associated with one.
            zero_one_profile_vector_mean = get_profile_vector(
                profile_expr,
                db,
                data_dim,
                scen_dim,
                is_zero_one=True,
                is_float32=is_float32,
            ).mean()
        return zero_one_profile_vector_mean * max_level

    assert target_is_max  # vi skal ha max level

    if not tv_is_max:
        avg_level = scalar
        tv_ref_period = timevector.get_reference_period()  # Vi lar ReferencePeriod være tidsindex som en lang periode
        if tv_ref_period is None:
            assert profile_expr is None, f"Timevector {timevector} has no reference period, profile_expr must therefore be None."
            return avg_level
        target_ref_period = scen_dim.get_reference_period()
        if target_ref_period is None:
            message = f"No reference period for scen_dim {scen_dim}"
            raise ValueError(message)
        if tv_ref_period != target_ref_period:
            tv_target_ref_period_mean = get_profile_vector(
                profile_expr,
                db,
                data_dim,
                scen_dim.copy_as_reference_period(target_ref_period),
                is_zero_one=False,
                is_float32=is_float32,
            )
            assert tv_target_ref_period_mean.size == 1
            avg_level = tv_target_ref_period_mean[0] * avg_level
        # avg_level med korrekt ref periode
        mean_one_profile_vector = get_profile_vector(profile_expr, db, data_dim, scen_dim, is_zero_one=False, is_float32=is_float32)
        return mean_one_profile_vector.max() * avg_level

    return scalar  # all good
