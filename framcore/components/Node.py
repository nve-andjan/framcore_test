from __future__ import annotations

from typing import TYPE_CHECKING

from framcore.attributes import Price, ShaddowPrice, Storage
from framcore.components import Component

if TYPE_CHECKING:
    from framcore.loaders import Loader


class Node(Component):
    """Node class. Subclass of Component."""

    def __init__(
        self,
        commodity: str,
        is_exogenous: bool = False,  # TODO
        price: ShaddowPrice | None = None,
        storage: Storage | None = None,
    ) -> None:
        """Initialize the Node class."""
        super().__init__()
        self._check_type(commodity, str)
        self._check_type(is_exogenous, bool)
        self._check_type(price, (ShaddowPrice, type(None)))
        self._check_type(storage, (Storage, type(None)))

        self._commodity = commodity
        self._is_exogenous = is_exogenous

        self._storage = storage

        if price is None:
            price = Price()

        self._price: Price = price

    def set_exogenous(self) -> None:
        """Set internal is_exogenous flag to True."""
        self._check_type(self._is_exogenous, bool)
        self._is_exogenous = True

    def set_endogenous(self) -> None:
        """Set internal is_exogenous flag to False."""
        self._check_type(self._is_exogenous, bool)
        self._is_exogenous = False

    def is_exogenous(self) -> bool:
        """Return True if Node is exogenous (i.e. has fixed prices determined outside the model) else False."""
        return self._is_exogenous

    def get_price(self) -> ShaddowPrice:
        """Return price."""
        return self._price

    def get_storage(self) -> Storage | None:
        """Get Storage if any."""
        return self._storage

    def get_commodity(self) -> str:
        """Return commodity."""
        return self._commodity

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add loaders stored in attributes to loaders."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self.get_price())
        add_loaders_if(loaders, self.get_storage())

    def _replace_node(self, old: str, new: str) -> None:
        return None

    def _get_simpler_components(self, _: str) -> dict[str, Component]:
        return dict()
