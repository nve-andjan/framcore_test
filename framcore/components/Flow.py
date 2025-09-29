from __future__ import annotations

from typing import TYPE_CHECKING

from framcore.attributes import Arrow, AvgFlowVolume, FlowVolume, ObjectiveCoefficient, StartUpCost
from framcore.components import Component
from framcore.fingerprints import Fingerprint
from framcore.loaders import Loader

if TYPE_CHECKING:
    from framcore.loaders import Loader


class Flow(Component):
    """Represents a commodity flow in or out of one or more nodes."""

    def __init__(
        self,
        main_node: str,
        max_capacity: FlowVolume | None = None,
        min_capacity: FlowVolume | None = None,
        startupcost: StartUpCost | None = None,
        volume: AvgFlowVolume | None = None,
        arrow_volumes: dict[Arrow, AvgFlowVolume] | None = None,
        is_exogenous: bool = False,
    ) -> None:
        """Initialize Flow with main node, capacity, and startup cost."""
        super().__init__()
        self._check_type(main_node, str)
        self._check_type(max_capacity, (FlowVolume, type(None)))
        self._check_type(min_capacity, (FlowVolume, type(None)))
        self._check_type(startupcost, (StartUpCost, type(None)))
        self._check_type(volume, (FlowVolume, type(None)))
        self._check_type(arrow_volumes, (dict, type(None)))
        self._main_node: str = main_node
        self._max_capacity = max_capacity
        self._min_capacity = min_capacity
        self._startupcost = startupcost
        self._arrows: set[Arrow] = set()
        self._cost_terms: dict[str, ObjectiveCoefficient] = dict()
        self._is_exogenous: bool = is_exogenous

        if not volume:
            volume = AvgFlowVolume()
        self._volume: AvgFlowVolume = volume

        if arrow_volumes is None:
            arrow_volumes = dict()
        self._arrow_volumes: dict[Arrow, AvgFlowVolume] = arrow_volumes

    def is_exogenous(self) -> bool:
        """Return True if Flow is exogenous."""
        return self._is_exogenous

    def set_exogenous(self) -> None:
        """
        Treat flow as rhs term.

        Use volume if it exists.
        If no volume, then try to use
        min_capacity and max_capacity, which must
        be equal. Error if this fails.
        """
        self._is_exogenous = True

    def set_endogenous(self) -> None:
        """
        Treat flow as decision variable.

        Volume should be updated with results after a solve.
        """
        self._is_exogenous = False

    def get_main_node(self) -> str:
        """Get the main node of the flow."""
        return self._main_node

    def get_volume(self) -> AvgFlowVolume:
        """Get the volume of the flow."""
        return self._volume

    def get_arrow_volumes(self) -> dict[Arrow, AvgFlowVolume]:
        """Get dict of volume converted to volume at node pointed to by Arrow."""
        return self._arrow_volumes

    def get_max_capacity(self) -> FlowVolume | None:
        """Get the maximum capacity of the flow."""
        return self._max_capacity

    def set_max_capacity(self, capacity: FlowVolume | None) -> None:
        """Set the maximum capacity of the flow."""
        self._check_type(capacity, (FlowVolume, type(None)))
        self._max_capacity = capacity

    def get_min_capacity(self) -> FlowVolume | None:
        """Get the minimum capacity of the flow."""
        return self._min_capacity

    def set_min_capacity(self, capacity: FlowVolume | None) -> None:
        """Set the minimum capacity of the flow."""
        self._check_type(capacity, (FlowVolume, type(None)))
        self._min_capacity = capacity

    def get_startupcost(self) -> StartUpCost | None:
        """Get the startup cost of the flow."""
        self._check_type(self._startupcost, (StartUpCost, type(None)))
        return self._startupcost

    def set_startupcost(self, startupcost: StartUpCost | None) -> None:
        """Set the startup cost of the flow."""
        self._check_type(startupcost, (StartUpCost, type(None)))
        self._startupcost = startupcost

    def get_arrows(self) -> set[Arrow]:
        """Get the arrows of the flow."""
        return self._arrows

    def add_arrow(self, arrow: Arrow) -> None:
        """Add an arrow to the flow."""
        self._check_type(arrow, Arrow)
        self._arrows.add(arrow)

    def add_cost_term(self, key: str, cost_term: ObjectiveCoefficient) -> None:
        """Add a cost term to the flow."""
        self._check_type(key, str)
        self._check_type(cost_term, ObjectiveCoefficient)
        self._cost_terms[key] = cost_term

    def get_cost_terms(self) -> dict[str, ObjectiveCoefficient]:
        """Get the cost terms of the flow."""
        return self._cost_terms

    def add_loaders(self, loaders: set[Loader]) -> None:
        """Add loaders stored in attributes to loaders."""
        from framcore.utils import add_loaders_if  # noqa: PLC0415

        add_loaders_if(loaders, self.get_volume())
        add_loaders_if(loaders, self.get_max_capacity())
        add_loaders_if(loaders, self.get_min_capacity())

        for cost in self.get_cost_terms().values():
            add_loaders_if(loaders, cost)

        for arrow in self.get_arrows():
            add_loaders_if(loaders, arrow)

        for volume in self.get_arrow_volumes().values():
            add_loaders_if(loaders, volume)

    def _replace_node(self, old: str, new: str) -> None:
        # Component.replace_node does input type check
        if old == self._main_node:
            self._main_node = new
        for a in self._arrows:
            a: Arrow
            if a.get_node() == old:
                a.set_node(new)
                return

    def _get_simpler_components(self, _: str) -> dict[str, Component]:
        return dict()

    def _get_fingerprint(self) -> Fingerprint:
        refs = {}
        refs["_main_node"] = self._main_node

        return self.get_fingerprint_default()
