# from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, tzinfo

from numpy.typing import NDArray

from framcore import Base
from framcore.fingerprints.fingerprint import Fingerprint
from framcore.timeindexes import FixedFrequencyTimeIndex


class TimeIndex(Base, ABC):
    """TimeIndex interface for TimeVectors."""

    @abstractmethod
    def __eq__(self, other) -> bool:  # noqa: ANN001
        """Check if two TimeIndexes are equal."""
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Compute hash value.."""
        pass

    @abstractmethod
    def get_fingerprint(self) -> Fingerprint:
        """Get the fingerprint of the TimeIndex."""
        pass

    @abstractmethod
    def get_timezone(self) -> tzinfo | None:
        """Get the timezone of the TimeIndex."""
        pass

    @abstractmethod
    def get_num_periods(self) -> bool:
        """Get the number of periods in the TimeIndex."""
        pass

    @abstractmethod
    def is_52_week_years(self) -> bool:
        """Check if the TimeIndex is based on 52-week years."""
        pass

    @abstractmethod
    def is_one_year(self) -> bool:
        """
        Check if the TimeIndex represents a single year.

        Must be False if
        extrapolate_first_point and or extrapolate_last_point is True.

        When True, can be repeted in profiles.
        """
        pass

    @abstractmethod
    def is_whole_years(self) -> bool:
        pass

    @abstractmethod
    def extrapolate_first_point(self) -> bool:
        """Check if the TimeIndex should extrapolate the first point. Must be False if is_one_year is True."""
        pass

    @abstractmethod
    def extrapolate_last_point(self) -> bool:
        """Check if the TimeIndex should extrapolate the last point. Must be False if is_one_year is True."""
        pass

    @abstractmethod
    def get_period_average(self, vector: NDArray, start_time: datetime, duration: timedelta, is_52_week_years: bool) -> float:
        """Get the average over the period from the vector."""
        pass

    @abstractmethod
    def write_into_fixed_frequency(
        self,
        target_vector: NDArray,
        target_timeindex: FixedFrequencyTimeIndex,
        input_vector: NDArray,
    ) -> None:
        """Write the input vector into the target vector based on the target FixedFrequencyTimeIndex."""
        pass

    @abstractmethod
    def is_constant(self) -> bool:
        """Check if the TimeIndex is constant."""
        pass
