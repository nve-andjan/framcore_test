from framcore.attributes import Arrow, AvgFlowVolume, Conversion, Cost, FlowVolume
from framcore.components import Flow
from framcore.components._PowerPlant import _PowerPlant


class _WindSolar(_PowerPlant):
    """
    Wind and Solar class component representing a wind and solar power plant. Subclass of PowerPlant.

    This class models a wind or solarpower plant with various attributes inherited from the parent class PowerPlant.

    Capacity can be provided directly or as parts (level or profile). Max and min capacity profiles are set
    to be equal as the capacity_profile for these technologytypes since it does not have a max or min.

    The functions _get_fingerprints, _get_nodes og _get_flow are defines in this
    subclass since other subclases are dependent on fuel and emission nodes.
    """

    def __init__(
        self,
        power_node: str,
        max_capacity: FlowVolume,
        voc: Cost | None = None,
        production: AvgFlowVolume | None = None,
    ) -> None:
        """Initialize the Wind and Solar class."""
        super().__init__(
            power_node=power_node,
            max_capacity=max_capacity,
            min_capacity=None,
            voc=voc,
            production=production,
        )

    """Implementation of Component interface"""

    def _get_simpler_components(self, base_name: str) -> dict[str, Flow]:
        return {base_name + "_Flow": self._create_flow()}

    def _create_flow(self) -> Flow:
        flow = Flow(
            main_node=self._power_node,
            max_capacity=self._max_capacity,
            volume=self._production,
        )

        flow.add_arrow(Arrow(node=self._power_node, is_ingoing=True, conversion=Conversion(value=1)))

        if self._voc:
            flow.add_cost_term("VOC", self._voc)
        else:
            flow.set_min_capacity(self._max_capacity)
            flow.set_exogenous()

        return flow


class Wind(_WindSolar):
    """Wind power component."""

    pass


class Solar(_WindSolar):
    """Solar power component."""

    pass
