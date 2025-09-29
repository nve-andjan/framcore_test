from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from numpy.typing import NDArray

from framcore import Base
from framcore.fingerprints import Fingerprint
from framcore.timeindexes import TimeIndex
from framcore.timevectors import ReferencePeriod

if TYPE_CHECKING:
    from framcore.loaders import TimeVectorLoader


# TODO: Floating point precision
class TimeVector(Base, ABC):
    """TimeVector interface class."""

    def __init__(self) -> None:
        """Initialize the TimeVector class."""
        super().__init__()

    @abstractmethod
    def __eq__(self, other) -> bool:  # noqa: ANN001
        """Check if two TimeVectors are equal."""
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Compute hash value."""
        pass

    @abstractmethod
    def get_vector(self, is_float32: bool) -> NDArray:
        """Get the values of the TimeVector."""
        pass

    @abstractmethod
    def get_timeindex(self) -> TimeIndex | None:
        """Get the TimeIndex of the TimeVector."""
        pass

    @abstractmethod
    def is_constant(self) -> bool:
        """Check if the TimeVector is constant."""
        pass

    @abstractmethod
    def is_max_level(self) -> bool | None:
        """
        Check if TimeVector is a level representing max Volume/Capacity.

        Returns:
            True - vector is a level representing max Volume/Capacity.
            False - vector is a level representing average Volume/Capacity over a given reference period.
            None - vector is not a level.

        """
        pass

    @abstractmethod
    def is_zero_one_profile(self) -> bool | None:
        """
        Check if TimeVector is a profile with values between zero and one.

        Returns:
            True - vector is a profile with values between zero and one.
            False - vector is a profile where the mean value is 1 given a reference period.
            None - vector is not a profile.

        """
        pass

    @abstractmethod
    def get_unit(self) -> str | None:
        """Get the unit of the TimeVector."""
        pass

    @abstractmethod
    def get_fingerprint(self) -> Fingerprint:
        """Get the fingerprint of the TimeVector."""
        pass

    @abstractmethod
    def get_reference_period(self) -> ReferencePeriod | None:
        """Get the reference period of the TimeVector."""
        pass

    @abstractmethod
    def get_loader(self) -> TimeVectorLoader | None:
        """Get the TimeVectorLoader of the TimeVector if self has one."""
        pass
