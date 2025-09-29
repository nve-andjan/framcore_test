import numpy as np
from numpy.typing import NDArray

from framcore.fingerprints import Fingerprint
from framcore.loaders import TimeVectorLoader
from framcore.timeindexes import ConstantTimeIndex
from framcore.timevectors import ReferencePeriod
from framcore.timevectors.TimeVector import TimeVector  # NB! full import path needed for inheritance to work


class LinearTransformTimeVector(TimeVector):
    """LinearTransformTimeVector(TimeVector). Immutable."""

    def __init__(
        self,
        timevector: TimeVector,
        scale: float,
        shift: float,
        unit: str | None,
        is_max_level: bool | None = None,
        is_zero_one_profile: bool | None = None,
        reference_period: ReferencePeriod | None = None,
    ) -> None:
        """
        Transform timevector into scale * timevector + shift.

        May also override unit, is_max_level,  is_zero_one_profile and reference_period.
        """
        self._check_type(timevector, TimeVector)
        self._check_type(scale, float)
        self._check_type(shift, float)
        self._check_type(unit, (str, type(None)))
        self._check_type(is_max_level, (bool, type(None)))
        self._check_type(is_zero_one_profile, (bool, type(None)))
        self._check_type(reference_period, (ReferencePeriod, type(None)))
        self._timevector = timevector
        self._scale = scale
        self._shift = shift
        self._unit = unit
        self._is_max_level = is_max_level
        self._is_zero_one_profile = is_zero_one_profile
        self._reference_period = reference_period

    def get_vector(self, is_float32: bool) -> NDArray:
        """Get the values of the TimeVector."""
        vector = self._timevector.get_vector(is_float32)
        if self._scale == 1.0 and self._shift == 0.0:
            return vector
        out = vector.copy()
        if self._scale != 1.0:
            np.multiply(out, self._scale, out=out)
        if self._shift != 0.0:
            np.add(out, self._shift, out=out)
        return out

    def get_fingerprint(self) -> Fingerprint:
        """Get the Fingerprint of the TimeVector."""
        return self.get_fingerprint_default()

    def get_timeindex(self) -> ConstantTimeIndex:
        """Get the TimeIndex of the TimeVector."""
        return self._timevector.get_timeindex()

    def is_constant(self) -> bool:
        """Check if the TimeVector is constant."""
        return self._timevector.is_constant()

    def is_max_level(self) -> bool | None:
        """Check if TimeVector is a level representing maximum Volume/Capacity."""
        return self._is_max_level

    def is_zero_one_profile(self) -> bool | None:
        """Check if TimeVector is a profile with values between zero and one."""
        return self._is_zero_one_profile

    def get_unit(self) -> str | None:
        """Get the unit of the TimeVector."""
        return self._unit

    def get_reference_period(self) -> ReferencePeriod | None:
        """Get the reference period of the TimeVector."""
        return self._reference_period

    def get_loader(self) -> TimeVectorLoader | None:
        """Call get_loader on underlying time vector."""
        return self._timevector.get_loader()

    def __eq__(self, other) -> bool:  # noqa: ANN001
        """Check if self and other are equal."""
        if not isinstance(other, type(self)):
            return False
        return (
            self._timevector == other._timevector
            and self._scale == other._scale
            and self._shift == other._shift
            and self._unit == other._unit
            and self._is_max_level == other._is_max_level
            and self._is_zero_one_profile == other._is_zero_one_profile
            and self._reference_period == other._reference_period
        )

    def __hash__(self) -> int:
        """Compute the hash of the LinearTransformTimeVector."""
        return hash(
            (
                self._timevector,
                self._scale,
                self._shift,
                self._unit,
                self._is_max_level,
                self._is_zero_one_profile,
                self._reference_period,
            ),
        )
