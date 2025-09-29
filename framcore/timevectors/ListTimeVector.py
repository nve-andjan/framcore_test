import numpy as np
from numpy.typing import NDArray

from framcore.fingerprints import Fingerprint
from framcore.timeindexes import TimeIndex
from framcore.timevectors import ReferencePeriod
from framcore.timevectors.TimeVector import TimeVector  # NB! full import path needed for inheritance to work


class ListTimeVector(TimeVector):
    """ListTimeVector class for TimeVectors with a numpy array of values. Subclass of TimeVector."""

    def __init__(
        self,
        timeindex: TimeIndex,
        vector: NDArray,
        unit: str | None,
        is_max_level: bool | None,
        is_zero_one_profile: bool | None,
        reference_period: ReferencePeriod | None = None,
    ) -> None:
        """
        Initialize the ListTimeVector class.

        Args:
            timeindex (TimeIndex): Index of timestamps for the vector.
            vector (NDArray): Array of vector values.
            unit (str | None): Unit of the values in the vector.
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
        if (is_max_level is not None and is_zero_one_profile is not None) or (is_max_level is None and is_zero_one_profile is None):
            message = (
                f"Input arguments for {self}: Must have exactly one 'non-None'"
                "value for is_max_level and is_zero_one_profile. "
                "A TimeVector is either a level or a profile."
            )
            raise ValueError(message)
        self._timeindex = timeindex
        self._vector = vector
        self._unit = unit
        self._reference_period = reference_period
        self._is_max_level = is_max_level
        self._is_zero_one_profile = is_zero_one_profile

    def __eq__(self, other):
        """Check equality between two ListTimeVector objects."""
        if not isinstance(other, ListTimeVector):
            return NotImplemented
        return (self._timeindex == other._timeindex) and np.array_equal(self._vector, other._vector) and (self._unit == other._unit) and (self._is_max_level == other._is_max_level) and (self._is_zero_one_profile == other._is_zero_one_profile) and (self._reference_period == other._reference_period)
    
    def __hash__(self) -> int:
        """Return hash of ListTimeVector object."""
        return hash((self._timeindex, self._vector.tobytes(), self._unit, self._is_max_level, self._is_zero_one_profile, self._reference_period))
    
    def __repr__(self) -> str:  # TODO: Also timeindex and reference_period
        """Return the string representation of the ListTimeVector."""
        return f"ListTimeVector(timeindex={self._timeindex}, vector={self._vector}, unit={self._unit})"

    def get_vector(self, is_float32: bool) -> NDArray:
        """Get the vector of the TimeVector as a numpy array."""
        if is_float32:
            return self._vector.astype(dtype=np.float32)
        return self._vector

    def get_timeindex(self) -> TimeIndex:
        """Get the TimeIndex of the TimeVector."""
        return self._timeindex

    def is_constant(self) -> bool:
        """Check if the TimeVector is constant."""
        return False

    def is_max_level(self) -> bool:
        """Check if TimeVector is a level representing maximum Volume/Capacity."""
        return self._is_max_level

    def is_zero_one_profile(self) -> bool:
        """Check if TimeVector is a profile with vector between zero and one."""
        return self._is_zero_one_profile

    def get_unit(self) -> str | None:
        """Get the unit of the TimeVector."""
        return self._unit

    def get_reference_period(self) -> ReferencePeriod | None:
        """Get the reference period of the TimeVector."""
        return self._reference_period

    def get_fingerprint(self) -> Fingerprint:
        """
        Get the fingerprint of the ListTimeVector.

        Returns:
            Fingerprint: The fingerprint of the ListTimeVector, excluding the reference period.

        """
        excludes = {"_reference_period"}
        return self.get_fingerprint_default(excludes=excludes)

    def get_loader(self) -> None:
        """Interface method Not applicable for this type. Return None."""
        return
