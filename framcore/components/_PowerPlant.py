from framcore.attributes import AvgFlowVolume, Cost, FlowVolume
from framcore.components import Component


class _PowerPlant(Component):
    """
    PowerPlant parent class component representing a power plant. Subclass of Component.

    This class models a powerplant with various attributes such as power node,
    capacity, VOC levels and profile, and production.

    Functions that are dependent on commodity nodes other than power are defined in the spesific power plant components.
    """

    def __init__(
        self,
        power_node: str,
        max_capacity: FlowVolume,
        min_capacity: FlowVolume | None,
        voc: Cost | None = None,
        production: AvgFlowVolume | None = None,
    ) -> None:
        """Initialize the  class."""
        super().__init__()

        self._check_type(power_node, str)
        self._check_type(max_capacity, FlowVolume)
        self._check_type(min_capacity, (FlowVolume, type(None)))
        self._check_type(voc, (Cost, type(None)))
        self._check_type(production, (AvgFlowVolume, type(None)))

        self._power_node = power_node
        self._max_capacity = max_capacity
        self._min_capacity = min_capacity
        self._voc = voc

        if not production:
            production = AvgFlowVolume()

        self._production = production

    def get_max_capacity(self) -> FlowVolume:
        """Get the capacity of the power unit."""
        return self._max_capacity

    def get_production(self) -> AvgFlowVolume:
        """Get the production volume of the power unit."""
        return self._production

    def get_min_capacity(self) -> FlowVolume | None:
        """Get the minimum capacity of the power unit."""
        return self._min_capacity

    def set_min_capacity(self, value: FlowVolume | None) -> None:
        """Set the minimum capacity of the power unit."""
        self._check_type(value, (FlowVolume, type(None)))
        self._min_capacity = value

    def get_power_node(self) -> str:
        """Get the power node of the power unit."""
        return self._power_node

    def set_power_node(self, power_node: str) -> None:
        """Set the power node of the power unit."""
        self._check_type(power_node, str)
        self._power_node = power_node

    def get_voc(self) -> Cost | None:
        """Get the variable operating cost (VOC) level of the power unit."""
        return self._voc

    def set_voc(self, voc: Cost | None) -> None:
        """Set the variable operating cost (VOC) level of the power unit."""
        self._check_type(voc, (Cost, type(None)))
        self._voc = voc

    """Implementation of Component interface"""

    def _replace_node(self, old: str, new: str) -> None:
        if old == self._power_node:
            self._power_node = new
