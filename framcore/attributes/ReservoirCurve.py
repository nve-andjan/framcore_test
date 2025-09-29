from __future__ import annotations

from typing import TYPE_CHECKING

from framcore import Base

if TYPE_CHECKING:
    from framcore.loaders import Loader


class ReservoirCurve(Base):
    """
    Represents a reservoir curve attribute.

    Attributes
    ----------
    _value : str | None
        The value representing the reservoir curve.

    """

    def __init__(self, value: str | None) -> None:
        """
        Initialize a ReservoirCurve instance.

        Parameters
        ----------
        value : str | None
            The value representing the reservoir curve.

        """
        self._check_type(value, (str, type(None)))
        self._value = value

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in attributes to loaders."""
        return
