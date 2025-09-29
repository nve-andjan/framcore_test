from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framcore.loaders import Loader


class TargetBound:
    """
    Represents a target bound attribute.

    This class can be extended to define specific bounds for targets in the energy model.
    """

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in attributes to loaders."""
        return
