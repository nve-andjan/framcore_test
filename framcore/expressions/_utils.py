from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.querydbs import QueryDB
from framcore.timevectors import ConstantTimeVector, TimeVector

if TYPE_CHECKING:
    from framcore import Model


def _load_model_and_create_model_db(db: QueryDB | Model) -> QueryDB:
    from framcore import Model

    if isinstance(db, Model):
        from framcore.querydbs import ModelDB

        db = ModelDB(db)

    if not isinstance(db, QueryDB):
        message = f"Expected db to be Model or QueryDB, got {db} of type {type(db).__name__}"
        raise ValueError(message)
    return db


def _lookup_expr_from_constants_with_units(
    constants_with_units: dict[str, tuple],
    expr: Expr,
) -> tuple[str, float, str | None]:
    src = expr.get_src()
    if isinstance(src, ConstantTimeVector):
        src = src.get_expr_str()
    sym, value, unit = constants_with_units[src]
    return sym, value, unit


def _is_real_expr(expr: Expr, db: QueryDB) -> bool:
    if expr.is_leaf():
        src = expr.get_src()
        if isinstance(src, TimeVector | Curve):
            return True
        obj = db.get(src)
        return not isinstance(obj, Expr)
    __, args = expr.get_operations(expect_ops=True, copy_list=False)
    return all(_is_real_expr(ex, db) for ex in args)


def _ensure_real_expr(expr: Expr, db: QueryDB) -> Expr:
    if _is_real_expr(expr, db):
        return expr
    expr = copy.deepcopy(expr)
    _extend_expr(expr, db)
    return expr


def _extend_expr(expr: Expr, db: QueryDB) -> None:
    if expr.is_leaf():
        src = expr.get_src()
        if isinstance(src, TimeVector | Curve):
            return
        obj = db.get(src)
        if isinstance(obj, Expr):
            for name, value in obj.__dict__.items():
                setattr(expr, name, value)
            _extend_expr(expr, db)
        assert isinstance(obj, TimeVector | Curve), f"Got {obj}"
        return
    __, args = expr.get_operations(expect_ops=True, copy_list=False)
    for ex in args:
        _extend_expr(ex, db)
