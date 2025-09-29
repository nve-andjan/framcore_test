from framcore.attributes import Arrow, AvgFlowVolume, Conversion, FlowVolume, HydroBypass, HydroGenerator, HydroPump, HydroReservoir, WaterValue
from framcore.components import Component, Flow, Node


class HydroModule(Component):
    """HydroModule class representing a hydro module component."""

    # We add this to module name to get corresponding node name
    _NODE_NAME_POSTFIX = "_node"

    def __init__(
        self,
        release_to: str | None = None,  # Must be reference to another HydroModule
        release_capacity: FlowVolume | None = None,
        generator: HydroGenerator | None = None,  # attribute
        pump: HydroPump | None = None,
        inflow: AvgFlowVolume | None = None,
        reservoir: HydroReservoir | None = None,  # attribute
        hydraulic_coupling: int = 0,
        bypass: HydroBypass | None = None,  # attribute
        spill_to: str | None = None,  # Must be reference to another HydroModule
        commodity: str = "Hydro",
        water_value: WaterValue | None = None,
        release_volume: AvgFlowVolume | None = None,
        spill_volume: AvgFlowVolume | None = None,
    ) -> None:
        """Initialize the HydroModule with its parameters."""
        super().__init__()
        self._check_type(release_to, (str, type(None)))
        self._check_type(release_capacity, (FlowVolume, type(None)))
        self._check_type(generator, (HydroGenerator, type(None)))
        self._check_type(pump, (HydroPump, type(None)))
        self._check_type(inflow, (AvgFlowVolume, type(None)))
        self._check_type(reservoir, (HydroReservoir, type(None)))
        self._check_type(hydraulic_coupling, int)
        self._check_type(bypass, (HydroBypass, type(None)))
        self._check_type(spill_to, (str, type(None)))
        self._check_type(water_value, (WaterValue, type(None)))
        self._check_type(release_volume, (AvgFlowVolume, type(None)))
        self._check_type(spill_volume, (AvgFlowVolume, type(None)))

        self._release_to = release_to
        self._release_capacity = release_capacity
        self._generator = generator
        self._pump = pump
        self._inflow = inflow
        self._reservoir = reservoir
        self._hydraulic_coupling = hydraulic_coupling
        self._bypass = bypass
        self._spill_to = spill_to
        self._commodity = commodity

        if not water_value:
            water_value = WaterValue()

        if not release_volume:
            release_volume = AvgFlowVolume()

        if not spill_volume:
            spill_volume = AvgFlowVolume()

        self._water_value: WaterValue = water_value
        self._release_volume: AvgFlowVolume = release_volume
        self._spill_volume: AvgFlowVolume = spill_volume

    def get_release_capacity(self) -> FlowVolume | None:
        """Get the capacity of the thermal unit."""
        return self._release_capacity

    def get_hydraulic_coupling(self) -> int:
        """Get the Modules hydraulic code."""
        return self._hydraulic_coupling

    def get_reservoir(self) -> HydroReservoir | None:
        """Get the reservoir of the hydro module."""
        return self._reservoir

    def set_reservoir(self, reservoir: HydroReservoir | None) -> None:
        """Set the reservoir of the hydro module."""
        self._check_type(reservoir, (HydroReservoir, type(None)))
        self._reservoir = reservoir

    def get_pump(self) -> HydroPump | None:
        """Get the pump of the hydro module."""
        return self._pump

    def set_pump(self, pump: HydroPump | None) -> None:
        """Set the pump of the hydro module."""
        self._check_type(pump, (HydroPump, type(None)))
        self._pump = pump

    def get_generator(self) -> HydroGenerator | None:
        """Get the generator of the hydro module."""
        return self._generator

    def set_generator(self, generator: HydroGenerator | None) -> None:
        """Set the generator of the hydro module."""
        self._check_type(generator, (HydroGenerator, type(None)))
        self._generator = generator

    def get_bypass(self) -> HydroBypass | None:
        """Get the bypass of the hydro module."""
        return self._bypass

    def set_bypass(self, bypass: HydroBypass | None) -> None:
        """Set the bypass of the hydro module."""
        self._check_type(bypass, (HydroBypass, type(None)))
        self._bypass = bypass

    def get_inflow(self) -> AvgFlowVolume | None:
        """Get the inflow of the hydro module."""
        return self._inflow

    def set_inflow(self, inflow: AvgFlowVolume | None) -> None:
        """Set the inflow of the hydro module."""
        self._check_type(inflow, (AvgFlowVolume, type(None)))
        self._inflow = inflow

    def get_release_to(self) -> str | None:
        """Get the release_to module of the hydro module."""
        return self._release_to

    def set_release_to(self, release_to: str | None) -> None:
        """Set the release_to module of the hydro module."""
        self._check_type(release_to, (str, type(None)))
        self._release_to = release_to

    def get_spill_to_module(self) -> str | None:
        """Get the spill_to module of the hydro module."""
        return self._spill_to

    def get_water_value(self) -> WaterValue:
        """Get water value at the hydro node."""
        return self._water_value

    def get_release_volume(self) -> FlowVolume:
        """Get the release_volume volume of the thermal unit."""
        return self._release_volume

    def get_spill_volume(self) -> FlowVolume:
        """Get the spill_volume volume of the thermal unit."""
        return self._spill_volume

    """Implementation of Component interface"""

    def _replace_node(self, old: str, new: str) -> None:
        if self._pump and old == self._pump.get_power_node():
            self._pump.set_power_node(new)
        if self._generator and old == self._generator.get_power_node():
            self._generator.set_power_node(new)

    def _get_simpler_components(self, module_name: str) -> dict[str, Component]:
        out: dict[str, Component] = {}

        node_name = module_name + self._NODE_NAME_POSTFIX

        out[node_name] = self._create_hydro_node()
        out[module_name + "_release_flow"] = self._create_release_flow(node_name)
        out[module_name + "_spill_flow"] = self._create_spill_flow(node_name)

        if self._inflow is not None:
            out[module_name + "_inflow_flow"] = self._create_inflow_flow(node_name)

        if self._bypass is not None:
            out[module_name + "_bypass_flow"] = self._create_bypass_flow(node_name)

        if self._pump is not None:
            out[module_name + "_pump_flow"] = self._create_pump_flow(node_name)

        return out

    def _create_hydro_node(self) -> Node:
        return Node(
            commodity=self._commodity,
            price=self._water_value,
            storage=self._reservoir,
        )

    def _create_release_flow(self, node_name: str) -> Flow:
        # TODO: pq_curve, nominal_head, tailwater_elevation
        flow = Flow(
            main_node=node_name,
            max_capacity=self._release_capacity,
            volume=self._release_volume,
            startupcost=None,
            arrow_volumes=None,
            is_exogenous=False,
        )
        arrow_volumes = flow.get_arrow_volumes()

        outgoing_arrow = Arrow(
            node=node_name,
            is_ingoing=False,
            conversion=Conversion(value=1),
        )
        flow.add_arrow(outgoing_arrow)

        if self._release_to:
            flow.add_arrow(
                Arrow(
                    node=self._release_to + self._NODE_NAME_POSTFIX,
                    is_ingoing=True,
                    conversion=Conversion(value=1),
                ),
            )

        if self._generator:
            production_arrow = Arrow(
                node=self._generator.get_power_node(),
                is_ingoing=True,
                conversion=self._generator.get_energy_eq(),
            )
            flow.add_arrow(production_arrow)
            arrow_volumes[production_arrow] = self._generator.get_production()

        return flow

    def _create_spill_flow(self, node_name: str) -> Flow:
        flow = Flow(
            main_node=node_name,
            max_capacity=None,
            volume=self._spill_volume,
        )

        flow.add_arrow(
            Arrow(
                node=node_name,
                is_ingoing=False,
                conversion=Conversion(value=1),
            ),
        )

        if self._spill_to is not None:
            flow.add_arrow(
                Arrow(
                    node=self._spill_to + self._NODE_NAME_POSTFIX,
                    is_ingoing=True,
                    conversion=Conversion(value=1),
                ),
            )

        return flow

    def _create_bypass_flow(self, node_name: str) -> Flow:
        flow = Flow(
            main_node=node_name,
            max_capacity=self._bypass.get_capacity(),
            volume=self._bypass.get_volume(),
            is_exogenous=False,
        )

        flow.add_arrow(
            Arrow(
                node=node_name,
                is_ingoing=False,
                conversion=Conversion(value=1),
            ),
        )

        if self._bypass.get_to_module() is not None:
            flow.add_arrow(
                Arrow(
                    node=self._bypass.get_to_module() + self._NODE_NAME_POSTFIX,
                    is_ingoing=True,
                    conversion=Conversion(value=1),
                ),
            )

        return flow

    def _create_inflow_flow(self, node_name: str) -> Flow:
        flow = Flow(
            main_node=node_name,
            max_capacity=None,
            volume=self._inflow,
            is_exogenous=True,
        )

        flow.add_arrow(
            Arrow(
                node=node_name,
                is_ingoing=True,
                conversion=Conversion(value=1),
            ),
        )

        return flow

    def _create_pump_flow(self, node_name: str) -> Flow:
        # TODO: add rest of attributes

        arrow_volumes: dict[Arrow, FlowVolume] = dict()

        flow = Flow(
            main_node=node_name,
            max_capacity=self._pump.get_water_capacity(),
            volume=self._pump.get_water_consumption(),
            arrow_volumes=arrow_volumes,
            is_exogenous=False,
        )

        flow.add_arrow(
            Arrow(
                node=self._pump.get_to_module() + self._NODE_NAME_POSTFIX,
                is_ingoing=True,
                conversion=Conversion(value=1),
            ),
        )

        flow.add_arrow(
            Arrow(
                node=self._pump.get_from_module() + self._NODE_NAME_POSTFIX,
                is_ingoing=False,
                conversion=Conversion(value=1),
            ),
        )

        pump_arrow = Arrow(
            node=self._pump.get_power_node(),
            is_ingoing=False,
            conversion=self._pump.get_energy_eq(),
        )
        flow.add_arrow(pump_arrow)
        arrow_volumes[pump_arrow] = self._pump.get_power_consumption()

        return flow
