from abc import ABC, abstractmethod

from framcore import Base


class QueryDB(Base, ABC):
    """
    Abstract base class for database queries.

    Provides an interface for getting, putting, and checking keys in a database.
    Subclasses must implement the _get, _put, and _has_key methods.

    """

    def get(self, key: object) -> object:
        """Get value behind key from db."""
        return self._get(key)

    def put(self, key: object, value: object, elapsed_seconds: float) -> None:
        """Put value in db behind key (maybe, depending on implementation)."""
        self._put(key, value, elapsed_seconds)

    def has_key(self, key: str) -> bool:
        """Return True if db has value behind key."""
        return self._has_key(key)

    def get_data(self) -> dict:
        """Return output of get_data called on first underlying model."""
        return self._get_data()

    @abstractmethod
    def _get(self, key: object) -> object:
        pass

    @abstractmethod
    def _put(self, key: object, value: object, elapsed_seconds: float) -> None:
        pass

    @abstractmethod
    def _has_key(self, key: object) -> bool:
        pass

    @abstractmethod
    def _get_data(self) -> dict:
        pass
