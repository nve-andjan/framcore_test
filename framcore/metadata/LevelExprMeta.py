from __future__ import annotations

from framcore.expressions import Expr, ensure_expr
from framcore.metadata.ExprMeta import ExprMeta  # NB! full import path needed for inheritance to work
from framcore.timevectors import TimeVector


class LevelExprMeta(ExprMeta):
    """
    LevelExprMeta represent an Expr. Subclass of ExprMeta.

    When used, all components must have a ExprMeta.
    """

    def __init__(self, value: Expr | TimeVector) -> None:
        """Create new LevelExprMeta with float value."""
        self._value = ensure_expr(value, is_level=True)
