"""Contain class describing transmission of Power commodity between nodes."""

from framcore.attributes import Arrow, AvgFlowVolume, Conversion, Cost, FlowVolume, Loss, Proportion
from framcore.components import Component, Flow


class Transmission(Component):
    """
    Transmission component representing a transmission line. Subclass of Component.

    An object of this class represents one transmission line where power flows one direction (the other direction is
    represented by another Transmission object). However, the actual measured power being sent can be higher than the
    amount being recieved because of loss. One Transmission object therefore represents the viewpoints of both the
    sender and the reciever of power on this specific line.

    """

    def __init__(
        self,
        from_node: str,
        to_node: str,
        max_capacity: FlowVolume = None,
        min_capacity: FlowVolume | None = None,
        loss: Loss | None = None,
        tariff: Cost | None = None,
        ramp_up: Proportion | None = None,
        ramp_down: Proportion | None = None,
        ingoing_volume: AvgFlowVolume | None = None,
        outgoing_volume: AvgFlowVolume | None = None,
    ) -> None:
        """Initialize object of the Transmission class. Perform type checks and convert arguments to expressions."""
        super().__init__()

        self._check_type(from_node, str)
        self._check_type(to_node, str)
        self._check_type(max_capacity, FlowVolume)
        self._check_type(min_capacity, (FlowVolume, type(None)))
        self._check_type(loss, (Loss, type(None)))
        self._check_type(tariff, (Cost, type(None)))
        self._check_type(ramp_up, (Proportion, type(None)))
        self._check_type(ramp_down, (Proportion, type(None)))
        self._check_type(ingoing_volume, (AvgFlowVolume, type(None)))
        self._check_type(outgoing_volume, (AvgFlowVolume, type(None)))

        self._from_node = from_node
        self._to_node = to_node
        self._max_capacity = max_capacity
        self._min_capacity = min_capacity
        self._loss = loss
        self._tariff = tariff
        self._ramp_up = ramp_up
        self._ramp_down = ramp_down

        if outgoing_volume is None:
            outgoing_volume = AvgFlowVolume()

        if ingoing_volume is None:
            ingoing_volume = AvgFlowVolume()

        self._outgoing_volume: AvgFlowVolume = outgoing_volume
        self._ingoing_volume: AvgFlowVolume = ingoing_volume

    def get_from_node(self) -> str:
        """Get the from node of the transmission line."""
        return self._from_node

    def set_from_node(self, node: str) -> None:
        """Set the from node of the transmission line."""
        self._check_type(node, str)
        self._from_node = node

    def get_to_node(self) -> str:
        """Get the to node of the transmission line."""
        return self._to_node

    def set_to_node(self, node: str) -> None:
        """Set the to node of the transmission line."""
        self._check_type(node, str)
        self._to_node = node

    def get_max_capacity(self) -> FlowVolume:
        """Get the maximum capacity (before losses) of the transmission line."""
        return self._max_capacity

    def get_min_capacity(self) -> FlowVolume:
        """Get the minimum capacity (before losses) of the transmission line."""
        return self._min_capacity

    def set_min_capacity(self, value: FlowVolume | None) -> None:
        """Set the minimum capacity (before losses) of the transmission line."""
        self._check_type(value, (FlowVolume, type(None)))
        self._min_capacity = value

    def get_outgoing_volume(self) -> AvgFlowVolume:
        """Get the outgoing (before losses) flow volume of the transmission line."""
        return self._outgoing_volume

    def get_ingoing_volume(self) -> AvgFlowVolume:
        """Get the ingoing (after losses) flow volume of the transmission line."""
        return self._ingoing_volume

    def get_loss(self) -> Loss | None:
        """Get the loss of the transmission line."""
        return self._loss

    def set_loss(self, loss: Loss | None) -> None:
        """Set the loss of the transmission line."""
        self._check_type(loss, (Loss, type(None)))
        self._loss = loss

    def get_tariff(self) -> Cost | None:
        """Get the tariff of the transmission line."""
        return self._tariff

    def set_tariff(self, tariff: Cost | None) -> None:
        """Set the tariff of the transmission line."""
        self._check_type(tariff, (Cost, type(None)))
        self._tariff = tariff

    def get_ramp_up(self) -> Proportion | None:
        """Get the ramp up profile level of the transmission line."""
        return self._ramp_up

    def set_ramp_up(self, value: Proportion | None) -> None:
        """Set the ramp up of the transmission line."""
        self._check_type(value, (Proportion, type(None)))
        self._ramp_up = value

    def get_ramp_down(self) -> Proportion | None:
        """Get the ramp down of the transmission line."""
        return self._ramp_down

    def set_ramp_down(self, value: Proportion | None) -> None:
        """Set the ramp down of the transmission line."""
        self._check_type(value, (Proportion, type(None)))
        self._ramp_down = value

    """Implementation of Component interface"""

    def _get_simpler_components(self, base_name: str) -> dict[str, Component]:
        return {base_name + "_Flow": self._create_flow()}

    def _replace_node(self, old: str, new: str) -> None:
        if old == self._from_node:
            self._from_node = new
        if old == self._to_node:
            self._to_node = new

    def _create_flow(self) -> Flow:
        arrow_volumes: dict[Arrow, FlowVolume] = dict()

        flow = Flow(
            main_node=self._from_node,
            max_capacity=self._max_capacity,
            volume=self._outgoing_volume,
            arrow_volumes=arrow_volumes,
            # ramp_up=self._ramp_up,    # TODO
            # ramp_down=self._ramp_up,  # TODO
        )

        outgoing_arrow = Arrow(
            node=self._from_node,
            is_ingoing=False,
            conversion=Conversion(value=1),
        )
        flow.add_arrow(outgoing_arrow)
        arrow_volumes[outgoing_arrow] = self._outgoing_volume

        # TODO: Extend Loss to support more fetures, such as quadratic losses? Needs loss param in Arrow to do this

        ingoing_arrow = Arrow(
            node=self._to_node,
            is_ingoing=True,
            conversion=Conversion(value=1),
            loss=self._loss,
        )
        flow.add_arrow(ingoing_arrow)
        arrow_volumes[ingoing_arrow] = self._ingoing_volume

        if self._tariff is not None:
            flow.add_cost_term("tariff", self._tariff)

        return flow
