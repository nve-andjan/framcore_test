"""ElasticDemand attribute class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from framcore import Base
from framcore.attributes import Elasticity, Price

# TODO: Discuss price interval validation. Should we check in init? How?

if TYPE_CHECKING:
    from framcore.loaders import Loader


class ElasticDemand(Base):
    """
    ElasticDemand class representing the price elasticity of a demand Component.

    Attributes:
        _price_elasticity: The price elasticity factor of the demand consumer.
        _min_price: Lower limit for price elasticity.
        _normal_price: Price for which the demand is inelastic. If it deviates from this price, the consumer will adjust
                       it's consumption according to the _price_elasticity factor.
        _max_price: Upper limit for price elasticity / reservation price level.

    """

    def __init__(
        self,
        price_elasticity: Elasticity,
        min_price: Price,
        normal_price: Price,
        max_price: Price,
    ) -> None:
        """Initialize the ElasticDemand class."""
        self._check_type(price_elasticity, Elasticity)
        self._check_type(min_price, Price)
        self._check_type(normal_price, Price)
        self._check_type(max_price, Price)

        self._price_elasticity = price_elasticity
        self._min_price = min_price
        self._normal_price = normal_price
        self._max_price = max_price

    def get_price_elasticity(self) -> Elasticity:
        """Get the price elasticity."""
        return self._price_elasticity

    def set_price_elasticity(self, elasticity: Price) -> None:
        """Set the price elasticity."""
        self._check_type(elasticity, Elasticity)
        self._price_elasticity = elasticity

    def get_min_price(self) -> Price:
        """Get the minimum price."""
        return self._min_price

    def set_min_price(self, min_price: Price) -> None:
        """Set the minimum price."""
        self._check_type(min_price, Price)
        self._min_price = min_price

    def get_normal_price(self) -> Price:
        """Get the normal price."""
        return self._normal_price

    def set_normal_price(self, normal_price: Price) -> None:
        """Set the normal price."""
        self._check_type(normal_price, Price)
        self._normal_price = normal_price

    def get_max_price(self) -> Price:
        """Get the maximum price."""
        return self._max_price

    def set_max_price(self, max_price: Price) -> None:
        """Set the maximum price."""
        self._check_type(max_price, Price)
        self._max_price = max_price

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add all loaders stored in attributes to loaders."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self._normal_price)
        add_loaders_if(loaders, self._price_elasticity)
        add_loaders_if(loaders, self._max_price)
        add_loaders_if(loaders, self._min_price)
