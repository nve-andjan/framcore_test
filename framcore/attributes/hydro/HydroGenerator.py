from framcore import Base
from framcore.attributes import AvgFlowVolume, Conversion
from framcore.curves import Curve
from framcore.expressions import Expr, ensure_expr
from framcore.fingerprints import Fingerprint
from framcore.timevectors import TimeVector


class HydroGenerator(Base):
    """Generator class representing a hydro generator component."""

    def __init__(
        self,
        power_node: str,
        energy_eq: Conversion,  # energy equivalent
        pq_curve: Expr | str | Curve | None = None,
        nominal_head: Expr | str | TimeVector | None = None,
        tailwater_elevation: Expr | str | TimeVector | None = None,
        production: AvgFlowVolume | None = None,
    ) -> None:
        """Initialize a hydro generator with power node, energy equivalent, and optional parameters."""
        super().__init__()

        self._check_type(power_node, str)
        self._check_type(energy_eq, Conversion)
        self._check_type(pq_curve, (Expr, str, Curve, type(None)))
        self._check_type(nominal_head, (Expr, str, TimeVector, type(None)))
        self._check_type(tailwater_elevation, (Expr, str, TimeVector, type(None)))

        self._power_node = power_node
        self._energy_eq = energy_eq
        self._pq_curve = ensure_expr(pq_curve)
        self._nominal_head = ensure_expr(nominal_head, is_level=True)
        self._tailwater_elevation = ensure_expr(tailwater_elevation, is_level=True)

        if production is None:
            production = AvgFlowVolume()
        self._production: AvgFlowVolume = production

    def get_power_node(self) -> str:
        """Get the power node of the hydro generator."""
        return self._power_node

    def set_power_node(self, power_node: str) -> None:
        """Set the power node of the pump unit."""
        self._check_type(power_node, str)
        self._power_node = power_node

    # TODO: change from eq to equivalent
    def get_energy_eq(self) -> Conversion:
        """Get the energy equivalent of the hydro generator."""
        return self._energy_eq

    def get_pq_curve(self) -> Expr | None:
        """Get the PQ curve of the hydro generator."""
        return self._pq_curve

    def get_nominal_head(self) -> Expr | None:
        """Get the nominal head of the hydro generator."""
        return self._nominal_head

    def get_tailwater_elevation(self) -> Expr | None:
        """Get the tailwater elevation of the hydro generator."""
        return self._tailwater_elevation

    def get_production(self) -> AvgFlowVolume:
        """Get the generation of the hydro generator."""
        return self._production

    def _get_fingerprint(self) -> Fingerprint:
        raise self.get_fingerprint_default(refs={"power_node": self._power_node})
