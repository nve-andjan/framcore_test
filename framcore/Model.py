from collections import Counter
from copy import deepcopy
from typing import TYPE_CHECKING

from framcore import Base
from framcore.components import Component
from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.loaders import Loader
from framcore.timevectors import TimeVector
from framcore.utils import get_supported_components

if TYPE_CHECKING:
    from framcore.aggregators import Aggregator


class Model(Base):
    """Definition of the Model class."""

    def __init__(self) -> None:
        """Create a new model instance."""
        self._data: dict[str, Component | TimeVector | Curve | Expr] = dict()
        self._aggregators: list[Aggregator] = []

    def add(self, key: str, x: Component | TimeVector | Curve | Expr, overwrite: bool = False) -> None:
        """
        Store deepcopy of x behind key.

        Raises KeyError is key already exist unless overwrite is True (default False).
        """
        self._check_type(key, str)
        self._check_type(x, (Component, TimeVector, Curve, Expr))
        assert key != "", "Invalid key name"
        if not overwrite and key in self._data:
            obj = self._data[key]
            message = f"Key {key} is already used to store object {obj}."
            raise KeyError(message)
        self._data[key] = deepcopy(x)

    def get(self, key: str) -> Component | TimeVector | Curve | Expr:
        """Get deepcopy of object stored behind key. KeyError if missing."""
        self._check_type(key, str)
        return deepcopy(self._data[key])

    def delete(self, key: str) -> None:
        """Delete object behind key. KeyError if missing."""
        self._check_type(key, str)
        del self._data[key]

    def disaggregate(self) -> None:
        """Undo all aggregations in LIFO order."""
        while self._aggregators:
            aggregator = self._aggregators.pop(-1)  # last item
            aggregator: Aggregator
            aggregator.disaggregate(self)

    def get_data(self) -> dict[str, Component | TimeVector | Curve | Expr]:
        """Get internal data. Modify this with care."""
        return self._data

    def get_content_counts(self) -> dict[str, Counter]:
        """Return number of objects stored in model organized into concepts and types."""
        data_values = self.get_data().values()
        counts = {
            "components": Counter(),
            "timevectors": Counter(),
            "curves": Counter(),
            "expressions": Counter(),
        }
        for obj in data_values:
            if isinstance(obj, Component):
                key = "components"
            elif isinstance(obj, TimeVector):
                key = "timevectors"
            elif isinstance(obj, Curve):
                key = "curves"
            elif isinstance(obj, Expr):
                key = "expressions"
            else:
                key = "unexpected"
                if key not in counts:
                    counts[key] = Counter()
            counts[key][type(obj).__name__] += 1

        assert len(data_values) == sum(c.total() for c in counts.values())

        counts["aggregators"] = Counter()
        for a in self._aggregators:
            counts["aggregators"][type(a).__name__] += 1

        return counts

    def get_loaders(self) -> set[Loader]:
        """Get all loaders stored in Model."""
        from framcore.components import Flow, Node

        out = set()
        data = self.get_data()
        components = dict()
        for key, value in data.items():
            if isinstance(value, Expr):
                value.add_loaders(out)
                # out.update(value.get_loaders())
            elif isinstance(value, TimeVector | Curve):
                loader = value.get_loader()
                if loader is not None:
                    out.add(loader)
            elif isinstance(value, Component):
                components[key] = value
        graph = get_supported_components(components, (Flow, Node), tuple())
        for c in graph.values():
            c: Flow | Node
            c.add_loaders(out)
            # out.update(c.get_loaders())
        return out

    def clear_caches(self) -> None:
        """
        Clear cached data from objects which use it in Model.

        Currently only loaders use cache.

        """
        for loader in self.get_loaders():
            loader.clear_cache()
