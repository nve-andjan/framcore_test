import numpy as np
from numpy.typing import NDArray

from framcore.fingerprints import Fingerprint
from framcore.loaders import TimeVectorLoader
from framcore.timeindexes import TimeIndex
from framcore.timevectors import ReferencePeriod
from framcore.timevectors.TimeVector import TimeVector  # NB! full import path needed for inheritance to work


class LoadedTimeVector(TimeVector):
    """TimeVector which gets its data from a data source via a TimeVectorLoader. Subclass of TimeVector."""

    def __init__(self, vector_id: str, loader: TimeVectorLoader) -> None:
        """
        Store vector id and loader in instance variables, get unit from loader.

        Args:
            vector_id (str): Unique name of this vector.
            loader (TimeVectorLoader): Object connected to a data source where vector_id is associated with a time
                                       vector. The Loader object must also implement the TimeVectorLoader API.

        Raises:
            ValueError: When metadata in the TimeVectorLoader for both is_max_level and is_zero_one_profile for the
                        given vector_id is not None. This would mean the TimeVector represents both a level and a
                        profile, which is not allowed.

        """
        self._vector_id = vector_id
        self._loader = loader
        self._check_type(self._vector_id, str)
        self._check_type(self._loader, TimeVectorLoader)

        self._is_max_level = self._loader.is_max_level(self._vector_id)
        self._is_zero_one_profile = self._loader.is_zero_one_profile(self._vector_id)
        self._unit = self._loader.get_unit(self._vector_id)
        self._reference_period = self._loader.get_reference_period(self._vector_id)

        if (self._is_max_level is not None and self._is_zero_one_profile is not None) or (self._is_max_level is None and self._is_zero_one_profile is None):
            message = (
                f"Values for {self._loader} is_max_level ({self._is_max_level}) and is_zero_one_profile"
                f" ({self._is_zero_one_profile}) with time vector {self} Must have exactly one 'non-None' value."
                " A TimeVector is either a level or a profile."
            )
            raise ValueError(message)

    def __repr__(self) -> str:
        """Overwrite string representation of LoadedTimeVector objects."""
        return f"{type(self).__name__}(vector_id={self._vector_id},loader={self._loader},unit={self._unit})"

    def __eq__(self, other: object) -> bool:
        """Check equality between two LoadedTimeVector objects."""
        if not isinstance(other, LoadedTimeVector):
            return NotImplemented
        return (self._vector_id == other._vector_id) and (self._loader == other._loader)

    def __hash__(self) -> int:
        """Return hash of LoadedTimeVector object."""
        return hash((self._vector_id, self._loader))

    def get_vector(self, is_float32: bool) -> NDArray:
        """Get the vector of the TimeVector as a numpy array."""
        vector = self._loader.get_values(self._vector_id)
        if is_float32:
            return vector.astype(np.float32)
        return vector

    def get_timeindex(self) -> TimeIndex:
        """
        Get this time vectors index.

        Returns:
            TimeIndex: Object describing the index.

        """
        return self._loader.get_index(self._vector_id)

    def is_constant(self) -> bool:
        """Signify if this TimeVector is constant."""
        return False

    def get_unit(self) -> str:
        """Get the unit of this TimeVector."""
        return self._unit

    def get_loader(self) -> TimeVectorLoader:
        """Get the Loader this TimeVector retrieves its data from."""
        return self._loader

    def get_reference_period(self) -> ReferencePeriod | None:
        """Get the reference period which the data of this TimeVector is from."""
        return self._reference_period

    def is_max_level(self) -> bool | None:
        """Check if TimeVector is a level representing maximum Volume/Capacity."""
        return self._loader.is_max_level(self._vector_id)

    def is_zero_one_profile(self) -> bool | None:
        """Check if TimeVector is a profile with values between zero and one."""
        return self._loader.is_zero_one_profile(self._vector_id)

    def get_fingerprint(self) -> Fingerprint:
        """Get the Fingerprint of this TimeVector."""
        return self._loader.get_fingerprint(self._vector_id)
