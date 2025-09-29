import numpy as np
from numpy.typing import NDArray

from framcore.fingerprints import Fingerprint
from framcore.timeindexes import ConstantTimeIndex
from framcore.timevectors import ReferencePeriod
from framcore.timevectors.TimeVector import TimeVector  # NB! full import path needed for inheritance to work


class ConstantTimeVector(TimeVector):
    """ConstantTimeVector class for TimeVectors that are constant over time. Subclass of TimeVector."""

    def __init__(
        self,
        scalar: float,
        unit: str | None = None,
        is_max_level: bool | None = None,
        is_zero_one_profile: bool | None = None,
        reference_period: ReferencePeriod | None = None,
    ) -> None:
        """
        Initialize the ListTimeVector class.

        Args:
            scalar (float): Constant float value of the timevector.
            unit (str | None): Unit of the value in the vector.
            is_max_level (bool | None): Whether the vector represents the maximum level, average level given a
                                        reference period, or not a level at all.
            is_zero_one_profile (bool | None): Whether the vector represents aprofile with values between 0 and 1, a
                                               profile with values averaging to 1 over a given reference period, or is
                                               not a profile.
            reference_period (ReferencePeriod | None, optional): Given reference period if the vector represents average
                                                                 level or mean one profile. Defaults to None.

        Raises:
            ValueError: When both is_max_level and is_zero_one_profile is not None. This would mean the TimeVector
                        represents both a level and a profile, which is not allowed.

        """
        self._scalar = float(scalar)
        self._unit = unit

        if (is_max_level is not None and is_zero_one_profile is not None) or (is_max_level is None and is_zero_one_profile is None):
            message = (
                f"Input arguments for {self}: Must have exactly one 'non-None'"
                "value for is_max_level and is_zero_one_profile. "
                "A TimeVector is either a level or a profile."
            )
            raise ValueError(message)
        self._is_max_level = is_max_level
        self._is_zero_one_profile = is_zero_one_profile
        self._reference_period = reference_period

        self._check_type(scalar, (float, np.float32))  # TODO: Accept np.float32 elsewhere aswell
        self._check_type(unit, (str, type(None)))
        self._check_type(is_max_level, (bool, type(None)))
        self._check_type(is_zero_one_profile, (bool, type(None)))
        self._check_type(reference_period, (ReferencePeriod, type(None)))

    def __repr__(self) -> str:
        """Return the string representation of the ConstantTimeVector."""
        ref_period = None
        if self._reference_period is not None:
            start_year = self._reference_period.get_start_year()
            num_years = self._reference_period.get_num_years()
            assert num_years > 0
            ref_period = f"{start_year}-{start_year + num_years - 1}"
        unit = f", unit={self._unit}" if self._unit is not None else ""
        ref_period = f", reference_period={ref_period}" if ref_period is not None else ""
        is_max_level = f", is_max_level={self._is_max_level}"
        return f"ConstantTimeVector({self._scalar}{unit}{ref_period}{is_max_level})"

    def __eq__(self, other: object) -> bool:
        """Check equality between two ConstantTimeVector objects."""
        if not isinstance(other, ConstantTimeVector):
            return NotImplemented
        return (
            self._scalar == other._scalar
            and self._unit == other._unit
            and self._is_max_level == other._is_max_level
            and self._is_zero_one_profile == other._is_zero_one_profile
            and self._reference_period == other._reference_period
        )

    def __hash__(self) -> int:
        """Compute the hash of the ConstantTimeVector."""
        return hash((self._scalar, self._unit, self._is_max_level, self._is_zero_one_profile, self._reference_period))

    def get_expr_str(self) -> str:
        """Simpler representation of self to show in Expr."""
        return f"{self._scalar} {self._unit if self._unit else ''}"

    def get_vector(self, is_float32: bool) -> NDArray:
        """Get the values of the TimeVector."""
        dtype = np.float32 if is_float32 else np.float64
        out = np.zeros(1, dtype=dtype)
        out[0] = self._scalar
        return out

    def get_timeindex(self) -> ConstantTimeIndex:
        """Get the TimeIndex of the TimeVector."""
        return ConstantTimeIndex()

    def is_constant(self) -> bool:
        """Check if the TimeVector is constant."""
        return True

    def is_max_level(self) -> bool:
        """Check if TimeVector is a level representing maximum Volume/Capacity."""
        return self._is_max_level

    def is_zero_one_profile(self) -> bool:
        """Check if TimeVector is a profile with values between zero and one."""
        return self._is_zero_one_profile

    def get_unit(self) -> str | None:
        """Get the unit of the TimeVector."""
        return self._unit

    def get_reference_period(self) -> ReferencePeriod | None:
        """Get the reference period of the TimeVector."""
        if self._reference_period is not None:
            return self._reference_period
        if self.is_zero_one_profile() is False:
            timeindex = self.get_timeindex()
            return timeindex.get_reference_period()
        return None

    def get_fingerprint(self) -> Fingerprint:
        """Get the Fingerprint of the TimeVector."""
        return self.get_fingerprint_default()

    def get_loader(self) -> None:
        """Interface method Not applicable for this type. Return None."""
        return
