from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy

from framcore.Base import Base
from framcore.components import Component
from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.metadata import Member
from framcore.Model import Model
from framcore.timevectors import TimeVector


class Aggregator(Base, ABC):
    """
    Aggregator interface class.

    Public API is the aggregate and disaggregate methods.

    These methods come with the folloing calling rules:
    1. Not allowed to call aggregate twice. Must call disaggregate before aggregate can be called again.
    2. Disaggragate can only be called after aggregate has been called.

    Implementations should implement _aggregate and _disaggregate.
    - The general approach for aggregation is to group components, aggregated components in the same group, delete the detailed components,
    and add the mapping to self._aggregation_map.
    - The general approach for disaggregation is to restore the detailed components, move results from aggregated components to detailed components,
    and delete the aggregated components.
    """

    def __init__(self) -> None:
        """Initialize the Aggregator with default state for aggregation tracking and data storage."""
        self._is_last_call_aggregate = None
        self._original_data: dict[str, Component | TimeVector | Curve | Expr] | None = None
        self._aggregation_map: dict[str, set[str]] | None = None

    def aggregate(self, model: Model) -> None:
        """Aggregate model. Keep original data in case disaggregate is called."""
        self._check_type(model, Model)

        if self._is_last_call_aggregate is True:
            message = f"Will overwrite existing aggregation."
            self.send_warning_event(message)
        
        self._original_data = deepcopy(model.get_data())
        self._aggregate(model)
        self._is_last_call_aggregate = True
        if self in model._aggregators:  # noqa: SLF001
            message = f"{model} has already been aggregated with {self}. Cannot perform the same Aggregation more than once on a Model object."
            raise ValueError(message)

        # transfer_unambigous_memberships to aggregated components to support further aggregation
        mapping = self.get_aggregation_map()
        reversed_mapping = defaultdict(set)
        new_data = model.get_data()
        for member_id, group_ids in mapping.items():
            self._check_type(group_ids, set)
            for group_id in group_ids:
                self._check_type(group_id, str)
                member_component = self._original_data[member_id]
                group_component = new_data[group_id]
                reversed_mapping[group_component].add(member_component)
        for group_component, member_components in reversed_mapping.items():
            transfer_unambigous_memberships(group_component, member_components)

        model._aggregators.append(deepcopy(self))  # noqa: SLF001

    def disaggregate(self, model: Model) -> None:
        """Disaggregate model back to pre-aggregate form. Move results into the disaggregated objects."""
        self._check_type(model, Model)
        self._check_is_aggregated()
        self._disaggregate(model, self._original_data)
        self._is_last_call_aggregate = False
        self._original_data = None
        self._aggregation_map = None

    def get_aggregation_map(self) -> dict[str, None | str | set[str]]:
        """
        Return dictionary mapping from disaggregated to aggregated Component IDs.

        The mapping should tell you which of the original Components were aggregated into which new Components.
        Components which are left as is should not be in the mapping.
        Components which are deleted without being aggregated are mapped to None.
        """
        if self._aggregation_map is None:
            message = f"{self} has not yet performed an aggregation or the aggregation map was not created during aggregation."
            raise ValueError(message)
        return self._aggregation_map

    @abstractmethod
    def _aggregate(self, model: Model) -> None:
        """Modify model inplace. Replace components with aggregated components according to some method."""
        pass

    @abstractmethod
    def _disaggregate(
        self,
        model: Model,
        original_data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> None:
        """
        Modify model inplace. Restore from aggregated to original components.

        Transfer any results from aggregated components to restored (disaggregated) components.

        Implementers should document and handle changes in model instance between aggregation and disaggregation.
        E.g. what to do if an aggregated component has been deleted prior to disaggregate call.
        """
        pass

    def _check_is_aggregated(self) -> None:
        if self._is_last_call_aggregate in [False, None]:
            message = "Not aggregated. Must call aggregate and disaggregate in pairs."
            raise RuntimeError(message)

def transfer_unambigous_memberships(group_component: Component, member_components: Iterable[Component]) -> None:
    """
    Transfer unambiguous membership metadata from member components to a group component.

    Parameters
    ----------
    group_component : Component
        The component to which unambiguous membership metadata will be transferred.
    member_components : Iterable[Component]
        The components from which membership metadata is collected.

    Notes
    -----
    Only metadata keys with a single unique Member value among all member components are transferred.
    Existing metadata on the group component is not overwritten.

    """
    d = defaultdict(set)
    for member in member_components:
        for key in member.get_meta_keys():
            value = member.get_meta(key)
            if not isinstance(value, Member):
                continue
            d[key].add(value)
    for key, value_set in d.items():
        test_value = group_component.get_meta(key)
        if test_value is not None:
            # don't overwrite if already set
            continue
        if len(value_set) != 1:
            # ambigous membership
            continue
        value = next(iter(value_set))
        group_component.add_meta(key, value)
