"""Demand class."""

from framcore.attributes import Arrow, AvgFlowVolume, Conversion, ElasticDemand, FlowVolume, ReservePrice
from framcore.components import Component, Flow
from framcore.expressions import Expr, ensure_expr
from framcore.timevectors import TimeVector


class Demand(Component):
    """Demand class representing a simple demand with possible reserve price. Subclass of Component."""

    def __init__(
        self,
        node: str,
        capacity: FlowVolume | None = None,
        reserve_price: ReservePrice | None = None,
        elastic_demand: ElasticDemand | None = None,
        temperature_profile: Expr | str | TimeVector | None = None,
        consumption: AvgFlowVolume | None = None,
    ) -> None:
        """Initialize the Demand class."""
        super().__init__()
        self._check_type(node, str)
        self._check_type(capacity, (FlowVolume, type(None)))
        self._check_type(reserve_price, (ReservePrice, type(None)))
        self._check_type(elastic_demand, (ElasticDemand, type(None)))
        self._check_type(consumption, (AvgFlowVolume, type(None)))

        if reserve_price is not None and elastic_demand is not None:
            message = "Cannot have 'reserve_price' and 'elastic_demand' at the same time."
            raise ValueError(message)

        self._node = node
        self._capacity = capacity
        self._reserve_price = reserve_price
        self._elastic_demand = elastic_demand
        self._temperature_profile = ensure_expr(temperature_profile, is_profile=True)

        if consumption is None:
            consumption = AvgFlowVolume()

        self._consumption: AvgFlowVolume = consumption

    def get_capacity(self) -> FlowVolume:
        """Get the capacity of the demand component."""
        return self._capacity

    def get_consumption(self) -> AvgFlowVolume:
        """Get the consumption of the demand component."""
        return self._consumption

    def get_node(self) -> str:
        """Get the node of the demand component."""
        return self._node

    def set_node(self, node: str) -> None:
        """Set the node of the demand component."""
        self._check_type(node, str)
        self.node = node

    def get_reserve_price(self) -> ReservePrice | None:
        """Get the reserve price level of the demand component."""
        return self._reserve_price

    def set_reserve_price_level(self, reserve_price: ReservePrice | None) -> None:  # TODO: Update
        """Set the reserve price level of the demand component."""
        self._check_type(reserve_price, (Expr, type(None)))
        if self._elastic_demand and reserve_price:
            message = "Cannot set reserve_price when elastic_demand is not None."
            raise ValueError(message)
        self._reserve_price = reserve_price

    def get_elastic_demand(self) -> ElasticDemand | None:
        """Get the elastic demand of the demand component."""
        return self._elastic_demand

    def set_elastic_demand(self, elastic_demand: ElasticDemand | None) -> None:
        """Set the elastic demand of the demand component."""
        self._check_type(elastic_demand, (ElasticDemand, type(None)))
        if self._reserve_price is not None and elastic_demand is not None:
            message = "Cannot set elastic_demand when reserve_price_level is not None."
            raise ValueError(message)
        self._elastic_demand = elastic_demand

    def get_temperature_profile(self) -> Expr | None:
        """Get the temperature profile of the demand component."""
        return self._temperature_profile

    def set_temperature_profile(self, temperature_profile: Expr | str | None) -> None:
        """Set the temperature profile of the demand component."""
        self._check_type(temperature_profile, (Expr, str, TimeVector, type(None)))
        self._temperature_profile = ensure_expr(temperature_profile, is_profile=True)

    """Implementation of Component interface"""

    def _replace_node(self, old: str, new: str) -> None:
        if old == self._node:
            self._node = new
        else:
            message = f"{old} not found in {self}. Expected existing node {self._node}."
            raise ValueError(message)

    def _get_simpler_components(self, base_name: str) -> dict[str, Component]:
        return {base_name + "_Flow": self._create_flow()}

    def _create_flow(self) -> Flow:
        is_exogenous = self._elastic_demand is None and self._reserve_price is None

        flow = Flow(
            main_node=self._node,
            max_capacity=self._capacity,
            min_capacity=self._capacity if is_exogenous else None,
            volume=self._consumption,
            arrow_volumes=None,
            is_exogenous=is_exogenous,
        )

        power_arrow = Arrow(self._node, False, conversion=Conversion(value=1))
        flow.add_arrow(power_arrow)

        if self._reserve_price is not None:
            flow.add_cost_term("reserve_price", self._reserve_price)

        # TODO: Implement correctly when Curve is ready. For now, model as inelastic consumer w. reserve_price
        elif self._elastic_demand is not None:
            price = self._elastic_demand.get_max_price()
            reserve_price = ReservePrice(level=price.get_level(), profile=price.get_profile())
            flow.add_cost_term("reserve_price", cost_term=reserve_price)

        return flow
