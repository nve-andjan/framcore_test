from framcore.attributes import ReservoirCurve, StockVolume
from framcore.attributes.Storage import Storage


class HydroReservoir(Storage):
    """Reservoir class representing a hydro reservoir attribute."""

    def __init__(
        self,
        capacity: StockVolume,
        reservoir_curve: ReservoirCurve = None,
        volume: StockVolume | None = None,
    ) -> None:
        """
        Initialize a HydroReservoir instance.

        Args:
            capacity (StockVolume): The total storage capacity of the reservoir.
            reservoir_curve (ReservoirCurve, optional): The curve describing reservoir characteristics.
            volume (StockVolume, optional): The current volume of water in the reservoir.

        """
        super().__init__(
            capacity=capacity,
            reservoir_curve=reservoir_curve,
            volume=volume,
        )
