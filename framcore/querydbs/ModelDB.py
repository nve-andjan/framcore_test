from framcore import Model
from framcore.querydbs import QueryDB


class ModelDB(QueryDB):
    """A database-like interface for querying multiple Model instances."""

    def __init__(self, model: Model, *models: tuple[Model]) -> None:
        """
        Initialize ModelDB with one or more Model instances.

        Args:
            model (Model): The primary Model instance.
            *models (tuple[Model]): Additional Model instances.

        """
        self._models: tuple[Model] = (model, *models)

    def _get(self, key: object) -> object:
        for m in self._models:
            data = m.get_data()
            if key in data:
                return data[key]
        message = f"Key '{key}' not found."
        raise KeyError(message)

    def _has_key(self, key: object) -> bool:
        return any(key in m.get_data() for m in self._models)

    def _put(self, key: object, value: object, elapsed_seconds: float) -> None:
        return None

    def _get_data(self) -> dict:
        return self._models[0].get_data()
