from framcore.attributes import Arrow, AvgFlowVolume, Conversion, Cost, Efficiency, FlowVolume, StartUpCost
from framcore.components import Component, Flow
from framcore.components._PowerPlant import _PowerPlant

# TODO
# refactor to use _ensure_flow and _ensure_coeff by using check_type, and possibly other methods
# add exception to replace_nodes (see implementation in Demand)


class Thermal(_PowerPlant):
    """
    Represents a thermal power plant, subclassing PowerPlant.

    This class models a thermal power plant with attributes inherited from PowerPlant.
    Additionally, it includes specific attributes such as:
    - fuel node
    - efficiency
    - emission node
    - emission coefficient
    - startup costs

    This class is compatible with ThermalAggregator.
    """

    def __init__(
        self,
        power_node: str,
        fuel_node: str,
        efficiency: Efficiency,
        emission_node: str | None = None,
        emission_coefficient: Conversion | None = None,
        startupcost: StartUpCost | None = None,
        max_capacity: FlowVolume | None = None,
        min_capacity: FlowVolume | None = None,
        voc: Cost | None = None,
        production: AvgFlowVolume | None = None,
        fuel_demand: AvgFlowVolume | None = None,
        emission_demand: AvgFlowVolume | None = None,
    ) -> None:
        """
        Initialize a Thermal power plant instance.

        Args:
            power_node (str): The power node of the plant.
            fuel_node (str): The fuel node of the plant.
            efficiency (Efficiency): Efficiency of the plant.
            emission_node (str | None, optional): Emission node.
            emission_coefficient (Conversion | None, optional): Emission coefficient.
            startupcost (StartUpCost | None, optional): Startup cost.
            max_capacity (FlowVolume | None, optional): Maximum capacity.
            min_capacity (FlowVolume | None, optional): Minimum capacity.
            voc (Cost | None, optional): Variable operating cost.
            production (AvgFlowVolume | None, optional): Production volume.
            fuel_demand (AvgFlowVolume | None, optional): Fuel demand.
            emission_demand (AvgFlowVolume | None, optional): Emission demand.

        """
        super().__init__(
            power_node=power_node,
            max_capacity=max_capacity,
            min_capacity=min_capacity,
            voc=voc,
            production=production,
        )

        self._check_type(fuel_node, str)
        self._check_type(emission_node, (str, type(None)))
        self._check_type(emission_coefficient, (Conversion, type(None)))
        self._check_type(startupcost, (StartUpCost, type(None)))
        self._check_type(production, (AvgFlowVolume, type(None)))
        self._check_type(fuel_demand, (AvgFlowVolume, type(None)))
        self._check_type(emission_demand, (AvgFlowVolume, type(None)))

        self._fuel_node = fuel_node
        self._efficiency = efficiency
        self._emission_node = emission_node
        self._emission_coefficient = emission_coefficient
        self._startupcost = startupcost

        if production is None:
            production = AvgFlowVolume()

        if fuel_demand is None:
            fuel_demand = AvgFlowVolume()

        if emission_demand is None and emission_node is not None:
            emission_demand = AvgFlowVolume()

        self._production = production
        self._fuel_demand = fuel_demand
        self._emission_demand = emission_demand

    def get_fuel_node(self) -> str:
        """Get the fuel node of the thermal unit."""
        return self._fuel_node

    def set_fuel_node(self, fuel_node: str) -> None:
        """Set the fuel node of the thermal unit."""
        self._check_type(fuel_node, str)
        self._fuel_node = fuel_node

    def get_emission_node(self) -> str | None:
        """Get the emission node of the thermal unit."""
        return self._emission_node

    def set_emission_node(self, emission_node: str | None) -> None:
        """Set the emission node of the thermal unit."""
        self._check_type(emission_node, (str, type(None)))
        self._emission_node = emission_node

    def get_emission_coefficient(self) -> Conversion | None:
        """Get the emission coefficient of the thermal unit."""
        return self._emission_coefficient

    def set_emission_coefficient(self, emission_coefficient: Conversion | None) -> None:
        """Set the emission coefficient of the thermal unit."""
        self._check_type(emission_coefficient, (Conversion, type(None)))
        self._emission_coefficient = emission_coefficient

    def get_fuel_demand(self) -> AvgFlowVolume:
        """Get the fuel demand of the thermal unit."""
        return self._fuel_demand

    def get_emission_demand(self) -> AvgFlowVolume | None:
        """Get the emission demand of the thermal unit."""
        return self._emission_demand

    def set_emission_demand(self, value: AvgFlowVolume | None) -> None:
        """Set the emission demand of the thermal unit."""
        self._check_type(value, (AvgFlowVolume, type(None)))
        self._emission_demand = value

    def get_efficiency(self) -> Efficiency:
        """Get the efficiency of the thermal unit."""
        return self._efficiency

    def get_startupcost(self) -> StartUpCost | None:
        """Get the startup cost of the thermal unit."""
        return self._startupcost

    def set_startupcost(self, startupcost: StartUpCost | None) -> None:
        """Set the startup cost of the thermal unit."""
        self._check_type(startupcost, (StartUpCost, type(None)))
        self._startupcost = startupcost

    """Implementation of Component interface"""

    def _get_simpler_components(self, base_name: str) -> dict[str, Component]:
        return {base_name + "_Flow": self._create_flow()}

    def _replace_node(self, old: str, new: str) -> None:
        if self._power_node == old:
            self._power_node = new
        if self._fuel_node == old:
            self._fuel_node = new
        if (self._emission_node is not None) and (old == self._emission_node):
            self._emission_node = new

    def _create_flow(self) -> Flow:
        arrow_volumes: dict[Arrow, AvgFlowVolume] = dict()

        is_exogenous = self._max_capacity == self._min_capacity

        flow = Flow(
            main_node=self._power_node,
            max_capacity=self._max_capacity,
            min_capacity=self._min_capacity,
            startupcost=self._startupcost,
            volume=self._production,
            arrow_volumes=arrow_volumes,
            is_exogenous=is_exogenous,
        )

        power_arrow = Arrow(
            node=self._power_node,
            is_ingoing=True,
            conversion=Conversion(value=1),
        )
        flow.add_arrow(power_arrow)

        fuel_arrow = Arrow(
            node=self._fuel_node,
            is_ingoing=False,
            efficiency=self._efficiency,
        )
        flow.add_arrow(fuel_arrow)
        arrow_volumes[fuel_arrow] = self._fuel_demand

        if self._emission_node is not None:
            if self._emission_demand is None:
                self._emission_demand = AvgFlowVolume()
            emission_arrow = Arrow(
                node=self._emission_node,
                is_ingoing=False,
                conversion=self._emission_coefficient,
                efficiency=self._efficiency,
            )
            flow.add_arrow(emission_arrow)
            arrow_volumes[emission_arrow] = self._emission_demand

        if self._voc:
            flow.add_cost_term("VOC", self._voc)

        return flow
