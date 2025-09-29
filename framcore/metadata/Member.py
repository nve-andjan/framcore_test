from __future__ import annotations

from framcore.fingerprints import Fingerprint
from framcore.metadata import Div
from framcore.metadata.Meta import Meta  # NB! full import path needed for inheritance to work


class Member(Meta):
    """
    Member represent membership to a catergory with a str. Subclass of Meta.

    Should not have missing values.

    When used, all components must have a membership.
    """

    def __init__(self, value: str | float | int) -> None:  # TODO: only str
        """Create new member with str value."""
        self._value = value  # set before checking, otherwise __repr__ can fail because self._value is not set.
        self._check_type(value, (str, float, int))

    def __repr__(self) -> str:
        """Overwrite __repr__ for better string representation."""
        return f"{type(self).__name__}(value={self._value})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on value."""
        if not isinstance(other, Member):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Overwrite __hash__ since its added to sets."""
        return hash(self.__repr__())

    def get_value(self) -> str | float | int:
        """Return str value."""
        return self._value

    def set_value(self, value: str | float | int) -> None:
        """Set str value. TypeError if not str."""
        self._check_type(value, (str, float, int))
        self._value = value

    def combine(self, other: Meta) -> Member | Div:
        """Return self if other == self else return Div containing both."""
        if self == other:
            return self
        d = Div(self)
        d.set_value(other)
        return d

    def get_fingerprint(self) -> Fingerprint:
        """Get the fingerprint of the Member."""
        return self.get_fingerprint_default()
