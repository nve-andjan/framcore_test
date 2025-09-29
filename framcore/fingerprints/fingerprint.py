from __future__ import annotations

import hashlib
import json
import pickle
from enum import Enum


class FingerprintRef:
    """Refers to another fingerprint."""

    def __init__(self, key: str) -> None:
        """
        Initialize a FingerprintRef with the given key.

        Args:
            key (str): The key referencing another fingerprint.

        """
        self._key = key

    def get_key(self) -> str:
        """
        Return the key referencing another fingerprint.

        Returns:
            str: The key referencing another fingerprint.

        """
        return self._key


class FingerprintDiffType(Enum):
    """Type of difference between two fingerprints."""

    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"


class FingerprintDiff:
    """Differences between two fingerprints."""

    def __init__(self) -> None:
        """Initialize an empty FingerprintDiff."""
        self._diffs: dict[str, tuple] = {}

    def add_diff(
        self,
        key: str,
        diff_type: FingerprintDiffType,
        obj: object,
    ) -> None:
        """
        Add a difference entry for a fingerprint.

        Args:
            key (str): The key identifying the fingerprint part.
            diff_type (FingerprintDiffType): The type of difference (NEW, MODIFIED, DELETED).
            obj: The object associated with the difference.

        """
        from framcore.components.Component import Component
        from framcore.curves.Curve import Curve
        from framcore.timevectors.TimeVector import TimeVector

        # Trenger vi denne sjekken, siden vi filtrerer ut alt som ikke er Fingerprint før vi kjører add_diff()?
        if isinstance(obj, TimeVector | Curve | Component):
            if key in self._diffs:
                message = f"duplicate entry: {key} ({obj})"
                print(message)

            self._diffs[key] = (obj, diff_type)

    def get_diffs(self) -> dict[str, tuple]:
        """
        Return the dictionary of differences.

        Returns:
            dict[str, tuple]: The differences stored in the FingerprintDiff.

        """
        return self._diffs

    def is_changed(self) -> bool:
        """Return True if there are any differences."""
        return bool(self._diffs)

    def update(self, other: FingerprintDiff) -> None:
        """
        Update this FingerprintDiff with differences from another FingerprintDiff.

        Args:
            other (FingerprintDiff): Another FingerprintDiff whose differences will be added.

        """
        self._diffs.update(other.get_diffs())


class Fingerprint:
    """Fingerprint of various data structures."""

    def __init__(self, source: object = None) -> None:
        """
        Initialize a Fingerprint instance.

        Args:
            source (object, optional): The source object to fingerprint. Defaults to None.

        """
        self._nested = {}
        self._hash = None
        self._source = source

    def add(self, key: str, value: object) -> None:
        """
        Add a value to the fingerprint under the specified key.

        Args:
            key (str): The key to associate with the value.
            value: The value to add, which can be a Fingerprint, FingerprintRef, or other supported types.

        Returns:
            None

        """
        assert key not in self._nested

        if isinstance(value, Fingerprint | FingerprintRef):
            self._nested[key] = value
        elif hasattr(value, "get_fingerprint"):
            self.add(key, value.get_fingerprint())
        elif isinstance(value, list | tuple | set):
            self.add(key, self._fingerprint_from_list(value))
        elif isinstance(value, dict):
            self.add(key, self._fingerprint_from_dict(value))
        else:
            self._nested[key] = _custom_hash(value)

        self._hash = None

    def _fingerprint_from_list(self, items: list | tuple | set) -> Fingerprint:
        fingerprint = Fingerprint()
        for index, value in enumerate(items):
            fingerprint.add(f"{index}", value)
        return fingerprint

    def _fingerprint_from_dict(self, a_dict: dict) -> Fingerprint:
        fingerprint = Fingerprint()
        for key, value in a_dict.items():
            fingerprint.add(f"{key}", value)
        return fingerprint

    def add_ref(self, prop: str, ref_key: str) -> None:
        """
        Add a FingerprintRef to the fingerprint under the specified property key.

        Args:
            prop (str): The property key to associate with the reference.
            ref_key (str): The key referencing another fingerprint.

        Returns:
            None

        """
        self.add(prop, FingerprintRef(ref_key))

    def get_parts(self) -> dict:
        """
        Return the dictionary of parts contained in the fingerprint.

        Returns:
            dict: A dictionary mapping keys to their associated fingerprint parts.

        """
        return {k: v for k, v in self._nested.items()}

    def update_ref(self, ref_key: str, fingerprint: Fingerprint) -> None:
        """
        Update the reference at the given key with a new Fingerprint.

        Args:
            ref_key (str): The key referencing the FingerprintRef to update.
            fingerprint (Fingerprint): The new Fingerprint to set at the reference.

        Returns:
            None

        """
        assert ref_key in self._nested
        assert isinstance(self._nested[ref_key], FingerprintRef)

        self._nested[ref_key] = fingerprint
        self._hash = None

    def get_hash(self) -> str:
        """
        Return the hash value of the fingerprint.

        Returns:
            str: The computed hash value representing the fingerprint.

        """
        self._resolve_total_hash()
        return self._hash

    def _contains_refs(self) -> bool:
        return any(isinstance(v, FingerprintRef) for v in self._nested.values())

    def _contains_key(self, key: str) -> bool:
        return key in self._nested

    def _resolve_total_hash(self) -> None:
        parts = []
        for k, v in self._nested.items():
            if isinstance(v, Fingerprint):
                parts.append((k, v.get_hash()))
            elif isinstance(v, FingerprintRef):
                parts.append((k, f"#ref:{v.get_key()}"))
            else:
                parts.append((k, v))

        self._hash = _custom_hash(sorted(parts))

    def diff(self, other: Fingerprint | None) -> FingerprintDiff:
        """Return differences between this and other fingerprint."""
        diff = FingerprintDiff()

        if other is None:
            for parent_key, parent_value in self.get_parts().items():
                if isinstance(parent_value, Fingerprint):
                    diff.add_diff(parent_key, FingerprintDiffType.NEW, parent_value._source)  # noqa: SLF001
                    diff.update(parent_value.diff(None))
            return diff

        if self.get_hash() == other.get_hash():
            return diff

        self_parts: dict[str, Fingerprint] = {
            key: value for key, value in self.get_parts().items() if isinstance(value, Fingerprint)
        }
        other_parts: dict[str, Fingerprint] = {
            key: value for key, value in other.get_parts().items() if isinstance(value, Fingerprint)
        }

        # Check for new or modified keys
        for key, value in self_parts.items():
            if key not in other_parts:
                diff.add_diff(key, FingerprintDiffType.NEW, value._source)  # noqa: SLF001
                diff.update(value.diff(None))
            elif value.get_hash() != other_parts[key].get_hash():
                diff.add_diff(key, FingerprintDiffType.MODIFIED, value._source)  # noqa: SLF001
                diff.update(value.diff(other_parts[key]))

        # Check for deleted keys
        for key in other_parts.keys() - self_parts.keys():
            other_value = other_parts[key]
            diff.add_diff(key, FingerprintDiffType.DELETED, other_value._source)  # noqa: SLF001
            source = self  # TODO: Is this correct?
            diff.update(Fingerprint(source).diff(other_value))

        return diff

    def __eq__(self, other: Fingerprint) -> bool:
        """
        Determine if two Fingerprint instances are equal based on their hash values.

        Args:
            other (Fingerprint): The other Fingerprint instance to compare.

        Returns:
            bool: True if the hash values are equal, False otherwise.

        """
        return self.get_hash() == other.get_hash()


def _custom_hash(value: object) -> str:
    """Return hash of value represented as str."""
    if isinstance(value, int | bool | float | None):
        return str(value)

    if isinstance(value, str):
        return hashlib.sha1(value.encode()).hexdigest()

    if isinstance(value, list | tuple | set):
        return _custom_hash(str(sorted([_custom_hash(x) for x in value])))

    if isinstance(value, dict):
        return _custom_hash([(_custom_hash(k), (_custom_hash(v))) for k, v in value.items()])

    sha1_hash = hashlib.sha1(pickle.dumps(value))
    return sha1_hash.hexdigest()
