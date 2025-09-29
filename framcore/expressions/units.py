from __future__ import annotations

import contextlib
import re

import sympy
from sympy import Expr as SymPyExpr
from sympy.core.power import Pow
from sympy.core.symbol import Symbol
from sympy.physics.units import Quantity, giga, gram, hour, kilo, mega, meter, second, tera, tonne, watt, year
from sympy.physics.units.prefixes import Prefix

EUR = Quantity("EUR", abbrev="€")

_SUPPORTED_UNITS = {
    "second": second,
    "s": second,
    "hour": hour,
    "h": hour,
    "year": year,
    "y": year,
    "watt": watt,
    "g": gram,
    "gram": gram,
    "kg": kilo * gram,
    "t": tonne,
    "tonne": tonne,
    "meter": meter,
    "m": meter,
    "m3": meter**3,
    "Mm3": mega * meter**3,
    "m3/s": meter**3 / second,
    "kilo": kilo,
    "mega": mega,
    "giga": giga,
    "tera": tera,
    "kWh": kilo * watt * hour,
    "MWh": mega * watt * hour,
    "GWh": giga * watt * hour,
    "TWh": tera * watt * hour,
    "kW": kilo * watt,
    "MW": mega * watt,
    "GW": giga * watt,
    "TW": tera * watt,
    "EUR": EUR,
    "€": EUR,
}

_FASTPATH_CONVERSION_FACTORS = {
    ("MW", "GW"): 0.001,
    ("MWh", "TWh"): 1e-6,
    ("m3", "Mm3"): 1e-6,
    ("kWh/m3", "GWh/Mm3"): 1.0,
    ("EUR/MWh", "EUR/GWh"): 1000.0,
    ("GWh/year", "MW"): 0.11407955544967756,
    ("Mm3/year", "m3/s"): 0.03168876540268821,
    ("t/MWh", "t/GWh"): 1000.0,
}

_FASTPATH_INCOMPATIBLE_CONVERSIONS = {
    ("MW", "m3/s"),
    ("m3/s", "MW"),
    ("GWh", "Mm3"),
    ("Mm3", "GWh"),
}

_DEBUG = False

_COLLECT_FASTPATH_DATA = False
_OBSERVED_UNIT_CONVERSIONS = set()


def get_unit_conversion_factor(from_unit: str | None, to_unit: str | None) -> float:
    """Get the conversion factor from one unit to another."""
    if from_unit == to_unit:
        return 1.0

    if from_unit is None or to_unit is None:
        message = f"Incompatible units: from_unit {from_unit} to_unit {to_unit}"
        raise ValueError(message)

    fastpath = _fastpath_get_unit_conversion_factor(from_unit, to_unit)

    if _DEBUG is False and fastpath is not None:
        return fastpath

    if fastpath is None:
        has_multiplier = False
        with contextlib.suppress(Exception):
            ix = from_unit.index("*")
            multiplier = float(from_unit[:ix])
            base_from_unit = from_unit[ix + 1 :].strip()
            has_multiplier = True

        if has_multiplier:
            fastpath = _fastpath_get_unit_conversion_factor(base_from_unit, to_unit)
            fastpath = fastpath if fastpath is None else fastpath * multiplier
            if _DEBUG is False and fastpath is not None:
                return fastpath

    if _COLLECT_FASTPATH_DATA and fastpath is None:
        if has_multiplier:
            _OBSERVED_UNIT_CONVERSIONS.add((base_from_unit, to_unit))
        else:
            _OBSERVED_UNIT_CONVERSIONS.add((from_unit, to_unit))

    fallback = _fallback_get_unit_conversion_factor(from_unit, to_unit)

    if _DEBUG and fastpath is not None and fallback != fastpath:
        message = f"Different results!\nfrom_unit {from_unit} to_unit {to_unit}\nfastpath {fastpath} fallback {fallback}"
        raise RuntimeError(message)

    if _unit_has_no_floats(from_unit) and _unit_has_no_floats(to_unit):
        _FASTPATH_CONVERSION_FACTORS[(from_unit, to_unit)] = fallback

    return fallback


def _unit_has_no_floats(unit: str) -> bool:
    if not unit:
        return True
    floats_in_str = re.findall(r"[-+]?(?:\d*\.*\d+)", unit)
    if not floats_in_str:
        return True
    floats_in_str: list[float] = [float(x) for x in floats_in_str]
    return all(x.is_integer() for x in floats_in_str)


def validate_unit_conversion_fastpaths() -> bool:
    """Run-Time validation of fastpaths."""
    errors = []
    for (from_unit, to_unit), result in _FASTPATH_CONVERSION_FACTORS.items():
        sympy_result = None
        with contextlib.suppress(Exception):
            sympy_result = _fallback_get_unit_conversion_factor(from_unit, to_unit)
        if result != sympy_result:
            message = f"'{from_unit}' to '{to_unit}' failed. Fastpath: {result}, SymPy: {sympy_result}"
            errors.append(message)
    for from_unit, to_unit in _FASTPATH_INCOMPATIBLE_CONVERSIONS:
        with contextlib.suppress(Exception):
            sympy_result = _fallback_get_unit_conversion_factor(from_unit, to_unit)
            message = f"'{from_unit}' to '{to_unit}'. Fastpath claim incompatible units, but SymPy fallback returned {sympy_result}"
            errors.append(message)
    if errors:
        message = "\n".join(errors)
        raise RuntimeError(message)


def _fastpath_get_unit_conversion_factor(from_unit: str, to_unit: str) -> float | None:
    """Try to look up the result."""
    key = (from_unit, to_unit)
    if key in _FASTPATH_CONVERSION_FACTORS:
        return _FASTPATH_CONVERSION_FACTORS[key]
    if key in _FASTPATH_INCOMPATIBLE_CONVERSIONS:
        message = f"Cannot convert from '{from_unit}' to '{to_unit}'"
        raise ValueError(message)
    return None


def _fallback_get_unit_conversion_factor(from_unit: str, to_unit: str) -> float | str:
    """Calculate conversion factor using sympy."""
    from_unit_sym = _unit_str_to_sym(from_unit)
    to_unit_sym = _unit_str_to_sym(to_unit)

    conversion_expr = from_unit_sym / to_unit_sym

    value = _get_scalar_from_expr(conversion_expr)

    if not isinstance(value, float):
        s = f"Incompatible units in expression: {conversion_expr}\nSimplified: {value}"
        message = f"Cannot convert from '{from_unit}' to '{to_unit}':\n{s}"
        raise ValueError(message)

    return value


def _unit_str_to_sym(unit: str) -> SymPyExpr:
    """Convert str unit to valid sympy representation or error."""
    unit = unit.strip()
    x = sympy.sympify(unit, locals=_SUPPORTED_UNITS)
    unsupported_args = [arg for arg in x.args if not (isinstance(arg, Prefix | Quantity | Pow | Symbol) or arg.is_number)]
    if unsupported_args:
        message = f"Unit string '{unit}' not valid. Unsupported args: {unsupported_args}"
        raise ValueError(message)
    return x


def _get_scalar_from_expr(expr_sym: SymPyExpr) -> float | str:
    """Get scalar value from a sympy expression."""
    simplified_expr = expr_sym.simplify()
    if not simplified_expr.is_number:
        for prefix in _SUPPORTED_UNITS.values():
            if isinstance(prefix, Prefix):
                expr_sym = expr_sym.subs(prefix, prefix.scale_factor)
        simplified_expr = expr_sym.simplify()
    try:
        return float(simplified_expr)
    except Exception:
        return str(simplified_expr)


def is_convertable(unit_from: str, unit_to: str) -> bool:
    """Return True if from_unit can be converted to to_unit else False."""
    with contextlib.suppress(Exception):
        get_unit_conversion_factor(unit_from, unit_to)
        return True
    return False
