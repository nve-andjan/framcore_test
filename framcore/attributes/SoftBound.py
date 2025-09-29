from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framcore.loaders import Loader


class SoftBound:
    """
    Represents a soft bound attribute.

    This class can be extended to define soft bounds for various parameters.

    """

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in attributes to loaders."""
        return
