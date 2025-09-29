from framcore import Base
from framcore.attributes import AvgFlowVolume, FlowVolume
from framcore.fingerprints import Fingerprint


class HydroBypass(Base):
    """Bypass class representing a hydro bypass attribute."""

    def __init__(
        self,
        to_module: str | None,
        capacity: FlowVolume | None = None,
    ) -> None:
        """Initialize Bypass."""
        super().__init__()

        self._check_type(to_module, (str, type(None)))
        self._check_type(capacity, (FlowVolume, type(None)))

        self._to_module = to_module
        self._capacity = capacity
        self._volume = AvgFlowVolume()

    def get_to_module(self) -> str | None:
        """Get the name of the module to which the bypass leads."""
        return self._to_module

    def set_to_module(self, to_module: str) -> None:
        """Set the name of the module to which the bypass leads."""
        self._check_type(to_module, str)
        self._to_module = to_module

    def get_capacity(self) -> FlowVolume | None:
        """Get the capacity of the bypass."""
        return self._capacity

    def get_volume(self) -> AvgFlowVolume:
        """Get the volume of the bypass."""
        return self._volume

    def _get_fingerprint(self) -> Fingerprint:
        return self.get_fingerprint_default(refs={"to_module": self._to_module})
