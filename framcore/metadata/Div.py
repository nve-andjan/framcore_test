from __future__ import annotations

from framcore.fingerprints import Fingerprint
from framcore.fingerprints.fingerprint import _custom_hash  # TODO: is this needed?
from framcore.metadata.Meta import Meta  # NB! full import path needed for inheritance to work


class Div(Meta):
    """
    Div class is made for loss-less aggregation of metadata. Subclass of Meta.

    It's combine method is made to keep all unique metadata,
    so that nothing is thrown away in connection with aggregation.
    """

    def __init__(self, value: Meta | set[Meta] | None = None) -> None:
        """Create Div metadata."""
        self._check_type_meta(value, with_none=True)

        self._value: set[Meta] = set()

        if isinstance(value, set):
            self._value.update(value)

        elif isinstance(value, Meta):
            self._value.add(value)

    def _check_type_meta(self, value: Meta | set[Meta], with_none: bool) -> None:
        if with_none:
            self._check_type(value, (Meta, set, type(None)))
        else:
            self._check_type(value, (Meta, set))
        if isinstance(value, set):
            for x in value:
                self._check_type(x, Meta)

    def get_value(self) -> set[Meta]:
        """Return str value."""
        return self._value

    def set_value(self, value: Meta | set[Meta]) -> None:
        """Set str value. TypeError if not str."""
        self._check_type_meta(value, with_none=False)
        if isinstance(value, set):
            self._value.update(value)

        elif isinstance(value, Meta):
            self._value.add(value)

    def combine(self, other: Meta | set[Meta]) -> Div:
        """Just consume other and return self."""
        self._check_type_meta(other, with_none=True)
        if isinstance(other, Div):
            for x in other.get_value():
                self.combine(x)
        else:
            self.set_value(other)
        return self

    def get_fingerprint(self) -> Fingerprint:
        """
        Generate and return a Fingerprint representing the current set of Meta values.

        Returns
        -------
        Fingerprint
            A fingerprint object based on the hashes of the contained Meta values.

        """
        fingerprint = Fingerprint()
        hash_list = [value.get_fingerprint().get_hash() for value in self._value]
        fingerprint.add("_value", _custom_hash(hash_list))
        return fingerprint
