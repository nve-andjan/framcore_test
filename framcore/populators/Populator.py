"""Populator API, for creating a system of Components, TimeVectors and Curves (and Expr) for a Model object."""

from abc import ABC, abstractmethod

from framcore import Base, Model
from framcore.components import Component
from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.timevectors import TimeVector


class Populator(Base, ABC):
    """Populate a model with data from a data source."""

    def __init__(self) -> None:
        """
        Set up ID and reference registration containers.

        These are used to check if IDs and references actually exist in the system.
        """
        super().__init__()

        self._registered_ids: dict[str, list[object]] = {}
        self._registered_refs: dict[str, set[str]] = {}

    def populate(self, model: Model) -> None:
        """
        Add data objects from a database to an input Model.

        These data objects shall be of class Component, TimeVector, and Curve.
        The method _populate should be overwritten in a subclass of Populator.
        In this way, it is used to create objects from any database.

        Args:
            model (Model): Model which will have the objects added to it.

        """
        self._check_type(model, Model)
        new_data = self._populate()

        # check that the new_data dict complies with the type hints of _populate?
        for existing_id in model.get_data():
            self._register_id(existing_id, model)
        errors = list(self._check_duplicate_ids())
        model.get_data().update(new_data)
        errors += list(self._check_references(model.get_data()))
        self._report_errors(errors)

    @abstractmethod
    def _populate(self) -> dict[str, Component | TimeVector | Curve | Expr]:
        """Create and return Components, TimeVectors and Curves. Possibly also Exprs."""
        pass

    def _check_duplicate_ids(self) -> dict[str, list[object]]:
        """
        Retrieve dictionary with ids of duplicated objects and their corresponding source.

        Returns:
            dict[str, list[object]]: keys are ids and values are lists of sources.

        """
        return {f"Duplicate ID found: '{duplicate_id}' in sources {sources}" for duplicate_id, sources in self._registered_ids.items() if len(sources) > 1}

    def _check_references(self, data: dict[str, Component | TimeVector | Curve | Expr]) -> set:
        errors = set()
        for ref, referencers in self._registered_refs.items():
            if ref not in data:
                msg = f"References to an invalid ID found. ID '{ref}' is not connected to any data."
                try:
                    sources = {source_id: data[source_id] for source_id in referencers}
                except KeyError:
                    errors.add(
                        msg + f" Sub Components referencing the faulty ID: {referencers}",
                    )
                else:
                    errors.add(
                        msg + f" Components referencing the faulty ID: {sources}",
                    )
        return errors

    def _report_errors(self, errors: list[str]) -> None:
        if errors:
            n = len(errors)
            s = "s" if n > 1 else ""
            error_str = "\n".join(errors)
            message = f"Found {n} error{s}:\n{error_str}"
            raise RuntimeError(message)

    def _register_id(self, new_id: str, source: object) -> None:
        """
        Register an id and its source.

        Args:
            new_id (str): New id to be registered.
            source (object): Source of the new id.

        """
        if new_id in self._registered_ids:
            self._registered_ids[new_id].append(source)
        else:
            self._registered_ids[new_id] = [source]

    def _register_references(self, component_id: str, references: set) -> None:
        for ref in references:
            if ref in self._registered_refs:
                self._registered_refs[ref].add(component_id)
            else:
                self._registered_refs[ref] = {component_id}
