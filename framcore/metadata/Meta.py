from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from framcore import Base
from framcore.fingerprints import Fingerprint


class Meta(Base, ABC):
    """
    Metadata-interface class for components.

    The interface is there to support validation and aggregation.
    - Some types of metadata should not have any missing values
    - Different types of metadata should be aggregated differently (e.g. ignore, sum, mean, keep all in list, etc.)
    """

    @abstractmethod
    def get_value(self) -> Any:  # noqa: ANN401
        """Return metadata value."""
        pass

    @abstractmethod
    def set_value(self, value: Any) -> None:  # noqa: ANN401
        """
        Set metadata value.

        Error if incorrect type or value.

        Some Meta types may be immutable and thus error if
        set_value is called with any value.
        """
        pass

    @abstractmethod
    def combine(self, other: Meta) -> Meta | None:
        """How should this metadata type be aggregated?."""
        pass

    @abstractmethod
    def get_fingerprint(self) -> Fingerprint:
        """Return fingerprint."""
        pass
