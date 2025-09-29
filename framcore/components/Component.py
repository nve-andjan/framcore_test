from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from framcore import Base
from framcore.metadata import Meta


class Component(Base, ABC):
    """Component interface class."""

    def __init__(self) -> None:
        """Set mandatory private variables."""
        self._parent: Component | None = None
        self._meta: dict[str, Meta] = dict()

    def add_meta(self, key: str, value: Meta) -> None:
        """Add metadata to component. Overwrite if already exist."""
        self._check_type(key, str)
        self._check_type(value, Meta)
        self._meta[key] = value

    def get_meta(self, key: str) -> Meta | None:
        """Get metadata from component or return None if not exist."""
        self._check_type(key, str)
        return self._meta.get(key, None)

    def get_meta_keys(self) -> Iterable[str]:
        """Get iterable with all metakeys in component."""
        return self._meta.keys()

    def get_simpler_components(
        self,
        base_name: str,
    ) -> dict[str, Component]:
        """
        Return representation of self as dict of named simpler components.

        The base_name should be unique within a model instance, and should
        be used to prefix name of all simpler components.

        Insert self as parent in each child.

        Transfer metadata to each child.
        """
        self._check_type(base_name, str)
        components = self._get_simpler_components(base_name)
        assert base_name not in components, f"base_name: {base_name}\ncomponent: {self}"
        components: dict[str, Component]
        self._check_type(components, dict)
        for name, c in components.items():
            self._check_type(name, str)
            self._check_type(c, Component)
            self._check_component_not_self(c)
            c: Component
            c._parent = self  # noqa: SLF001
        for key in self.get_meta_keys():
            value = self.get_meta(key)
            for c in components.values():
                c.add_meta(key, value)
        return components

    def get_parent(self) -> Component | None:
        """Return parent if any, else None."""
        self._check_type(self._parent, (Component, type(None)))
        self._check_component_not_self(self._parent)
        return self._parent

    def get_parents(self) -> list[Component]:
        """Return list of all parents, including self."""
        child = self
        parent = child.get_parent()
        parents = [child]
        while parent is not None:
            child = parent
            parent = child.get_parent()
            parents.append(child)
        self._check_unique_parents(parents)
        return parents

    def get_top_parent(self) -> Component:
        """Return topmost parent. (May be object self)."""
        parents = self.get_parents()
        return parents[-1]

    def replace_node(self, old: str, new: str) -> None:
        """Replace old node with new. Not error if no match."""
        self._check_type(old, str)
        self._check_type(new, str)
        self._replace_node(old, new)

    def _check_component_not_self(self, other: Component | None) -> None:
        if not isinstance(other, Component):
            return
        if self != other:
            return
        message = f"Expected other component than {self}."
        raise TypeError(message)

    def _check_unique_parents(self, parents: list[Component]) -> None:
        if len(parents) > len(set(parents)):
            message = f"Parents for {self} are not unique."
            raise TypeError(message)

    @abstractmethod
    def _replace_node(self, old: str, new: str) -> None:
        pass

    @abstractmethod
    def _get_simpler_components(self, base_name: str) -> dict[str, Component]:
        pass
