from __future__ import annotations

from framcore.expressions import Expr
from framcore.fingerprints import Fingerprint
from framcore.metadata import Div
from framcore.metadata.Meta import Meta  # NB! full import path needed for inheritance to work


class ExprMeta(Meta):
    """
    ExprMeta represent an Expr. Subclass of Meta.

    When used, all components must have a ExprMeta.
    """

    def __init__(self, value: Expr) -> None:
        """Create new ExprMeta with float value."""
        self._value = value
        self._check_type(value, Expr)

    def __repr__(self) -> str:
        """Overwrite __repr__ for better string representation."""
        return f"{type(self).__name__}(expr={self._value})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on expr."""
        if not isinstance(other, ExprMeta):
            return False
        return self._value == other._value

    def get_value(self) -> float:
        """Return expr."""
        return self._value

    def set_value(self, value: Expr) -> None:
        """Set expr value. TypeError if not expr."""
        self._check_type(value, Expr)
        self._value = value

    def combine(self, other: Meta) -> Expr | Div:
        """Sum Expr."""
        if isinstance(other, ExprMeta):
            return Expr(self._value + other.get_value())
        d = Div(self)
        d.set_value(other)
        return d

    def get_fingerprint(self) -> Fingerprint:
        """Get the fingerprint of the ScalarMeta."""
        return self.get_fingerprint_default()
