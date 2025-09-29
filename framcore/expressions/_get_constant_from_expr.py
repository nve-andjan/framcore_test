"""
Implementation of _get_constant_from_expr.

The first implementation used the _sympy_fallback function in all cases.
This turned out to be very slow for large expressions. Therefore,
we collected data on common expressions that turn up in aggregation,
and added fast paths for these cases.

Since this results in more code than the original,
we put this function in its own file.
"""

from __future__ import annotations

from time import time
from typing import TYPE_CHECKING

import sympy

from framcore.curves import Curve
from framcore.events import send_warning_event
from framcore.expressions import Expr
from framcore.expressions._utils import _ensure_real_expr, _load_model_and_create_model_db, _lookup_expr_from_constants_with_units
from framcore.expressions.units import _get_scalar_from_expr, _unit_str_to_sym, get_unit_conversion_factor
from framcore.querydbs import QueryDB
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex
from framcore.timevectors import ConstantTimeVector, TimeVector

if TYPE_CHECKING:
    from framcore import Model

_DEBUG = False
_DEBUG_ROUND_DECIMALS = 5
_WARN_IF_FALLBACK = True
_WARN_MAX_ELAPSED_SECONDS = 0.1

_NUM_LEAF = 0
_NUM_FALLBACK = 0
_NUM_FASTPATH_PRODUCT = 0
_NUM_FASTPATH_AGGREGATION = 0
_NUM_FASTPATH_SUM = 0


def _get_case_counts() -> dict[str, int]:
    """
    Return dict of counts for different cases of _get_constant_from_expr.

    Useful for fastpath development.
    """
    return {
        "fastpath_leaf": _NUM_LEAF,
        "fallback": _NUM_FALLBACK,
        "fastpath_sum": _NUM_FASTPATH_SUM,
        "fastpath_product": _NUM_FASTPATH_PRODUCT,
        "fastpath_aggregation": _NUM_FASTPATH_AGGREGATION,
    }


def _get_constant_from_expr(
    expr: Expr,
    db: QueryDB | Model,
    unit: str | None,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    is_max: bool,
) -> float:
    if not isinstance(expr, Expr):
        message = f"Expected Expr, got {expr}"
        raise ValueError(message)

    db = _load_model_and_create_model_db(db)

    real_expr = _ensure_real_expr(expr, db)

    constants_with_units = dict()

    expr_str = _update_constants_with_units(
        constants_with_units,
        real_expr,
        db,
        data_dim,
        scen_dim,
        is_max,
    )

    # counts for debug and optimization
    global _NUM_LEAF  # noqa: PLW0603
    global _NUM_FALLBACK  # noqa: PLW0603
    global _NUM_FASTPATH_PRODUCT  # noqa: PLW0603
    global _NUM_FASTPATH_AGGREGATION  # noqa: PLW0603
    global _NUM_FASTPATH_SUM  # noqa: PLW0603

    fastpath = None

    if real_expr.is_leaf():
        _NUM_LEAF += 1
        fastpath = _fastpath_leaf(constants_with_units, real_expr, unit)

    elif _is_fastpath_sum(expr):
        _NUM_FASTPATH_SUM += 1
        fastpath = _fastpath_sum(constants_with_units, real_expr, unit)

    elif _is_fastpath_product(real_expr):
        _NUM_FASTPATH_PRODUCT += 1
        fastpath = _fastpath_product(constants_with_units, real_expr, unit)

    elif _is_fastpath_aggregation(real_expr):
        _NUM_FASTPATH_AGGREGATION += 1
        fastpath = _fastpath_aggregation(constants_with_units, real_expr, unit)

    if fastpath is not None and _DEBUG is not True:
        return fastpath

    _NUM_FALLBACK += 1
    t = time()
    fallback = _sympy_fallback(constants_with_units, expr_str, unit)
    elapsed_seconds_fallback = time() - t

    if _DEBUG and fastpath is not None and round(fastpath, _DEBUG_ROUND_DECIMALS) != round(fallback, _DEBUG_ROUND_DECIMALS):
        message = f"Different results!\nExpr {real_expr}\nwith symbolic representation {expr_str}\nfastpath {fastpath} and fallback {fallback}"
        raise RuntimeError(message)

    if _DEBUG is False and _WARN_IF_FALLBACK is True and elapsed_seconds_fallback > _WARN_MAX_ELAPSED_SECONDS:
        message = f"fallback used {elapsed_seconds_fallback} seconds for (symbolic) expr: {expr_str}"
        send_warning_event(sender=_get_constant_from_expr, message=message)

    return fallback


def _update_constants_with_units(
    constants_with_units: dict[str, tuple],
    real_expr: Expr,
    db: QueryDB,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    is_max: bool,
) -> str:
    """Extract symbol, constant value and unit info from all leaf expressions of real_expr."""
    # To avoid circular import TODO: improve?
    from framcore.expressions.queries import _get_level_value_from_timevector

    if real_expr.is_leaf():
        is_level = real_expr.is_level()
        is_profile = real_expr.is_profile()

        src = real_expr.get_src()

        if isinstance(src, str) and db.has_key(src):
            obj = db.get(src)
            assert not isinstance(obj, Expr), f"{obj}"
            assert isinstance(obj, TimeVector | Curve), f"{obj}"

        elif isinstance(src, ConstantTimeVector):
            obj: ConstantTimeVector = src
            src = obj.get_expr_str()
        else:
            message = f"Unexpected value for src: {src}\nin expr {real_expr}"
            raise ValueError(message)

        if src in constants_with_units:
            sym, value, unit = constants_with_units[src]
            return sym

        if isinstance(obj, TimeVector):
            obj: TimeVector

            # added to support any_expr * ConstantTimeVector
            times_constant_case = (not is_profile) and isinstance(obj, ConstantTimeVector)

            if is_level or times_constant_case:
                unit = obj.get_unit()
                profile_expr = real_expr.get_profile()
                value = _get_level_value_from_timevector(obj, db, unit, data_dim, scen_dim, is_max, profile_expr)
                sym = f"x{len(constants_with_units)}"
                constants_with_units[src] = (sym, float(value), unit)
                return sym

            if not is_profile:
                message = f"Unsupported case where expr is not level and not profile:\nexpr: {real_expr}\nobj: {obj}"
                raise ValueError(message)

            assert is_profile

            raise NotImplementedError("Profile TimeVector not implemented yet")
        raise NotImplementedError("Curve not implemented yet")

    ops, args = real_expr.get_operations(expect_ops=True, copy_list=False)

    x = _update_constants_with_units(constants_with_units, args[0], db, data_dim, scen_dim, is_max)
    out = f"{x}"
    for op, arg in zip(ops, args[1:], strict=True):
        x = _update_constants_with_units(constants_with_units, arg, db, data_dim, scen_dim, is_max)
        out = f"{out} {op} {x}"

    return f"({out})"


def _is_fastpath_sum(expr: Expr) -> bool:
    """E.g. x0 + x1 + x2 + .. where x is leaf."""
    if expr.is_leaf():
        return True
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if ops[0] not in "+-":
        return False
    return all(arg.is_leaf() for arg in args)


def _is_fastpath_product(expr: Expr) -> bool:
    """E.g. x1 * (x2 + x3), or x1 * x2 * x3 where x is leaf."""
    if expr.is_leaf():
        return True
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if not all(op == "*" for op in ops):
        return False
    return all(arg.is_leaf() or _is_fastpath_sum(arg) for arg in args)


def _is_fastpath_sum(expr: Expr) -> bool:
    """x1 + x2 + .. + xn where x is leaf and n >= 1."""
    if expr.is_leaf():
        return True
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if ops[0] not in "+-":
        return False
    return all(arg.is_leaf() for op, arg in zip(ops, args[1:], strict=True))


def _is_fastpath_sum_of_products(expr: Expr) -> bool:
    """E.g. x1 * (x2 + x3) + x4 * x5 where x is leaf."""
    if expr.is_leaf():
        return True
    if _is_fastpath_product(expr):
        return True
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if ops[0] not in "+-":
        return False
    return all(_is_fastpath_product(arg) for arg in args)


def _is_fastpath_aggregation(expr: Expr) -> bool:
    """E.g. ((x1 * (x2 + x3) + x4 * x5) / (x6 + x7)) where x is leaf."""
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if ops != "/":
        return False
    try:
        numerator, denominator = args
    except Exception:
        return False
    if not _is_fastpath_sum_of_products(numerator):
        return False
    return _is_fastpath_sum(denominator)


def _fastpath_leaf(
    constants_with_units: dict[str, tuple],
    expr: Expr,
    target_unit: str | None,
) -> float:
    __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, expr)
    if unit == target_unit:
        return value
    return get_unit_conversion_factor(unit, target_unit) * value


def _fastpath_sum(
    constants_with_units: dict[str, tuple],
    expr: Expr,
    target_unit: str | None,
) -> float:
    d = _get_fastpath_sum_dict(constants_with_units, expr)

    out = 0.0
    for unit, value in d.items():
        if value == 0.0:
            continue
        if unit == target_unit:
            out += value
        else:
            out += value * get_unit_conversion_factor(unit, target_unit)

    return out


def _fastpath_product(
    constants_with_units: dict[str, tuple],
    expr: Expr,
    target_unit: str | None,
) -> float:
    d = _get_fastpath_product_dict(constants_with_units, expr)

    out = 1.0
    from_unit = None
    for unit, value in d.items():
        if value == 0.0:
            return 0.0
        out *= value
        if unit is None:
            continue
        from_unit = unit if from_unit is None else f"{from_unit} * {unit}"

    if not from_unit:
        return out

    return out * get_unit_conversion_factor(from_unit, target_unit)


def _fastpath_aggregation(  # noqa: C901, PLR0911
    constants_with_units: dict[str, tuple],
    expr: Expr,
    target_unit: str | None,
) -> float:
    __, args = expr.get_operations(expect_ops=True, copy_list=False)
    numerator, denominator = args

    num = _get_fastpath_aggregation_numerator_dict(constants_with_units, numerator)
    dem = _get_fastpath_aggregation_denominator_dict(constants_with_units, denominator)

    if len(dem) == len(num) == 1:
        num_unit, num_value = next(iter(num.items()))
        dem_unit, dem_value = next(iter(dem.items()))

        not_num_unit = num_unit is None
        not_dem_unit = dem_unit is None
        has_num_unit = num_unit is not None
        has_dem_unit = dem_unit is not None

        if not_num_unit and not_dem_unit:
            if target_unit is None:
                return num_value / dem_value
            message = f"Could not convert to {target_unit} with numerator {numerator} and denominator {denominator} for expr {expr}"
            raise ValueError(message)

        if not_dem_unit and has_num_unit:
            if target_unit == num_unit:
                return num_value / dem_value
            return get_unit_conversion_factor(num_unit, target_unit) * (num_value / dem_value)
        if has_dem_unit and not_num_unit:
            inverse_dem_unit = f"1/({dem_unit})"
            if target_unit == inverse_dem_unit:
                return num_value / dem_value
            return get_unit_conversion_factor(inverse_dem_unit, target_unit) * (num_value / dem_value)
        combined_unit = f"{num_unit}/({dem_unit})"
        if target_unit == combined_unit:
            return num_value / dem_value
        return get_unit_conversion_factor(combined_unit, target_unit) * (num_value / dem_value)

    combined_num_unit = ""
    for unit, value in num.items():
        op = "+" if value > 0 else "-"
        combined_num_unit = f"{combined_num_unit} {op} {abs(value)}"

    combined_dem_unit = ""
    for unit, value in num.items():
        op = "+" if value > 0 else "-"
        combined_dem_unit = f"{combined_dem_unit} {op} {abs(value)}"

    combined_unit = f"({combined_num_unit})/({combined_dem_unit})"

    return get_unit_conversion_factor(combined_unit, target_unit)


def _get_fastpath_sum_dict(
    constants_with_units: dict[str, tuple],
    expr: Expr,
) -> dict[str | None, float]:
    d = dict()
    if expr.is_leaf():
        __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, expr)
        return {unit: value}
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, args[0])
    d[unit] = value
    for op, arg in zip(ops, args[1:], strict=True):
        __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, arg)
        contribution = value if op == "+" else -value
        if unit not in d:
            d[unit] = contribution
        else:
            d[unit] += contribution
    return d


def _get_fastpath_product_dict(
    constants_with_units: dict[str, tuple],
    expr: Expr,
) -> dict[str | None, float]:
    d = dict()
    if expr.is_leaf():
        __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, expr)
        return {unit: value}
    __, args = expr.get_operations(expect_ops=True, copy_list=False)
    for arg in args:
        if _is_fastpath_sum(arg):
            values = _get_fastpath_sum_dict(constants_with_units, arg)
        else:
            __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, arg)
            values = {unit: value}
        for unit, value in values.items():
            if unit not in d:
                d[unit] = value
            else:
                d[unit] *= value
    return d


def _get_fastpath_product_unit(d: dict[str | None, float]) -> tuple[float, str | None]:
    combined_value = 1.0
    combined_unit = []
    for unit, value in d.items():
        combined_value *= value
        if unit is not None:
            combined_unit.append(unit)
    if not combined_unit:
        return combined_value, None
    return combined_value, "*".join(sorted(f"({s})" for s in combined_unit))


def _get_fastpath_aggregation_numerator_dict(
    constants_with_units: dict[str, tuple],
    expr: Expr,
) -> dict[str | None, float]:
    if expr.is_leaf():
        __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, expr)
        return {unit: value}
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    out = dict()
    value, unit = _get_fastpath_product_unit(_get_fastpath_product_dict(constants_with_units, args[0]))
    out[unit] = value
    for op, arg in zip(ops, args[1:], strict=True):
        value, unit = _get_fastpath_product_unit(_get_fastpath_product_dict(constants_with_units, arg))
        contribution = value if op == "+" else -value
        if unit not in out:
            out[unit] = contribution
        else:
            out[unit] += contribution
    return out


def _get_fastpath_aggregation_denominator_dict(
    constants_with_units: dict[str, tuple],
    expr: Expr,
) -> dict[str | None, float]:
    if expr.is_leaf():
        __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, expr)
        return {unit: value}
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    d = dict()
    __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, args[0])
    d[unit] = value
    for op, arg in zip(ops, args[1:], strict=True):
        __, value, unit = _lookup_expr_from_constants_with_units(constants_with_units, arg)
        if value == 0.0:
            continue
        contribution = value if op == "+" else -value
        if unit not in d:
            d[unit] = contribution
        else:
            d[unit] += contribution
    return d


def _sympy_fallback(constants_with_units: dict[str, tuple], expr_str: str, target_unit: str | None) -> float:
    """Convert expr to sympy expr, substitue in constants with units, and let sympy evaluate."""
    expr_sym = sympy.sympify(expr_str)
    for src, (sym, value, unit) in constants_with_units.items():
        sympy_sym = sympy.Symbol(sym)

        if unit is not None:
            unit_sym = _unit_str_to_sym(unit)
            expr_sym = expr_sym.subs(sympy_sym, value * unit_sym)
        else:
            expr_sym = expr_sym.subs(sympy_sym, value)

    if target_unit:
        unit_sym = _unit_str_to_sym(target_unit)
        expr_sym = expr_sym / unit_sym

    value = _get_scalar_from_expr(expr_sym)
    if isinstance(value, str):
        message = f"Cannot convert expression '{expr_str}' with target_unit {target_unit} to scalar value. {value}."
        raise ValueError(message)

    return value
