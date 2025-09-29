from framcore import Model
from framcore.querydbs import QueryDB


class CacheDB(QueryDB):
    """Stores models and precomputed values."""

    def __init__(self, model: Model, *models: tuple[Model]) -> None:
        """
        Initialize CacheDB with one or more Model instances.

        Args:
            model (Model): The primary Model instance.
            *models (tuple[Model]): Additional Model instances.

        """
        self._models: tuple[Model] = (model, *models)
        self._cache = dict()
        self._min_elapsed_seconds = 0.01

    def set_min_elapsed_seconds(self, value: float) -> None:
        """Values that takes below this threshold to compute, does not get cached."""
        self._check_type(value, float)
        self._check_float(lower_bound=0.0)
        self._min_elapsed_seconds = value

    def get_min_elapsed_seconds(self) -> float:
        """Values that takes below this threshold to compute, does not get cached."""
        return self._min_elapsed_seconds

    def _get(self, key: object) -> object:
        if key in self._cache:
            return self._cache[key]
        for m in self._models:
            data = m.get_data()
            if key in data:
                return data[key]
        message = f"Key '{key}' not found."
        raise KeyError(message)

    def _has_key(self, key: object) -> bool:
        return key in self._cache or any(key in m.get_data() for m in self._models)

    def _put(self, key: object, value: object, elapsed_seconds: float) -> None:
        if elapsed_seconds < self._min_elapsed_seconds:
            return
        self._cache[key] = value

    def _get_data(self) -> dict:
        return self._models[0].get_data()
