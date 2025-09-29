from __future__ import annotations

from collections import defaultdict
from time import time
from typing import TYPE_CHECKING

from framcore.aggregators import Aggregator
from framcore.aggregators._utils import _aggregate_costs
from framcore.attributes import MaxFlowVolume, Price
from framcore.components import Component, Demand, Node, Transmission
from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.metadata import Member, Meta
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex
from framcore.timevectors import TimeVector
from framcore.utils import get_component_to_nodes, get_transports_by_commodity

# TODO: Support internal loss demand
# TODO: Document method appropriate place (which docstring? module? class? __init__? _aggregate?)
# TODO: transfer member metadata to internal loss Demand

if TYPE_CHECKING:
    from framcore import Model


class NodeAggregator(Aggregator):
    """Aggregate groups of nodes for a commodity. Subclass of Aggregator."""

    def __init__(
        self,
        commodity: str,
        meta_key: str,
        data_dim: SinglePeriodTimeIndex,
        scen_dim: FixedFrequencyTimeIndex,
        utilization_rate: float = 0.5,
    ) -> None:
        """
        Aggregate groups of nodes (defined by metadata key) for a commodity.

        Args:
            commodity (str): Commodity of the Nodes to be aggregated.
            meta_key (str): _description_
            data_dim (SinglePeriodTimeIndex): Data dimension for eager evalutation of prices.
            scen_dim (FixedFrequencyTimeIndex): Scenario dimension for eager evalutation of prices.
            utilization_rate (float, optional): Assumed utilization rate on internal transports. Used to calculate new Demands after aggregation
                                                          if the transport does not have a volume.
                                                          Defaults to 0.5 (i.e. 50 percent utilization in each direction).

        """
        super().__init__()
        self._commodity = commodity
        self._meta_key = meta_key
        self._data_dim = data_dim
        self._scen_dim = scen_dim
        self._utilization_rate = utilization_rate

        # To remember all modifications in _aggregate so we can undo them in _disaggregate
        # Will be cleared in __init of _aggregate, so that same memory can be re-used.
        self._grouped_nodes: dict[str, set[str]] = defaultdict(set)
        self._replaced_references: dict[str, set[tuple[str, str]]] = defaultdict(set)  # dict with controll of all nodes which have been replaced
        self._internal_transports: set[str] = set()
        self._internal_demands: set[str] = set()

        # To record error messages in _aggregate and _disaggregate
        # Will be cleared in _init_aggregate and _init_disaggregate,
        # so that same memory can be re-used.
        self._errors: set[str] = set()

    def _aggregate(self, model: Model) -> None:
        """Modify model, components and data."""
        t0 = time()
        # Will be modified by upcoming code by adding group_nodes
        # and deleting member_nodes and redundant transports.
        data = model.get_data()

        # Helper-dict to give simpler access to components in upcoming loops
        # The components are the same instances as in data, and upcoming code
        # will use this to modify components inplace, in self._replace_node.
        components: dict[str, Component] = {key: c for key, c in data.items() if isinstance(c, Component)}

        # This is just a helper-dict to give fast access
        component_to_nodes: dict[str, set[str]] = get_component_to_nodes(components)

        self._init_aggregate(components, data)
        self.send_debug_event(f"init time {round(time() - t0, 3)} seconds")

        # main logic
        t = time()
        for group_name, member_node_names in self._grouped_nodes.items():
            member_node_names: set[str]
            group_node = Node(commodity=self._commodity)
            self._set_group_price(model, group_node, member_node_names, "EUR/MWh")
            self._delete_members(data, member_node_names)
            model.add(group_name, group_node)
            self._replace_node(group_name, member_node_names, components, component_to_nodes)
            components[group_name] = group_node
        self.send_debug_event(f"main logic time {round(time() - t, 3)} seconds")

        t = time()
        transports = get_transports_by_commodity(components, self._commodity)
        self._update_internal_transports(transports)
        self._delete_transports(data)
        self._add_internal_demands(model, components, transports)
        self.send_debug_event(f"handle internal transport losses time {round(time() - t, 3)} seconds")

        self.send_debug_event(f"total time {round(time() - t0, 3)} seconds")

    def _update_internal_transports(
        self,
        transports: dict[str, tuple[str, str]],
    ) -> None:
        for name, (from_node, to_node) in transports.items():
            if from_node == to_node:
                # if not, then invalid transport from before
                assert to_node in self._grouped_nodes

                # earlier to_node was added here, but it should be the transport name, right?
                self._internal_transports.add(name)

    def _add_internal_demands(
        self,
        model: Model,
        components: dict[str, Component],
        transports: dict[str, tuple[str, str]],
    ) -> None:
        # TODO: Document that we rely on Transmission and Demand API to get loss
        for key in self._internal_transports:
            transport = components[key]
            from_node, to_node = transports[key]
            assert from_node == to_node, f"{from_node}, {to_node}"
            node = from_node

            transport: Transmission

            if transport.get_loss():
                profile = None
                loss = transport.get_loss()
                if loss.get_level() is None:
                    continue
                if transport.get_outgoing_volume().get_level():
                    level = transport.get_outgoing_volume().get_level() * loss.get_level()
                    profile = (
                        transport.get_outgoing_volume().get_profile()
                    )  # could multiply by loss profile here, but profile*profile is not yet supported so we wait.
                # elif exploitation factor at individual level. How to best access this?
                else:
                    level = transport.get_max_capacity().get_level() * self._utilization_rate * loss.get_level()
                    profile = loss.get_profile()
                internl_demand = Demand(
                    node=node,
                    capacity=MaxFlowVolume(
                        level=level,
                        profile=profile,
                    ),
                )
                demand_key = key + "_Internal_Demand_" + node
                self._internal_demands.add(demand_key)
                model.add(demand_key, internl_demand)

    def _delete_transports(
        self,
        data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> None:
        for key in self._internal_transports:
            self._aggregation_map[key] = set()
            del data[key]

    def _delete_members(
        self,
        data: dict[str, Component | TimeVector | Curve | Expr],
        member_node_names: set[str],
    ) -> None:
        for member in member_node_names:
            del data[member]

    def _set_group_price(
        self,
        model: Model,
        group_node: Node,
        member_node_names: set[str],
        weight_unit: str,
    ) -> None:
        data = model.get_data()
        weights = [1.0 / len(member_node_names)] * len(member_node_names)
        prices = [data[key].get_price() for key in member_node_names]
        if all(prices):
            level, profile, intercept = _aggregate_costs(
                model=model,
                costs=prices,
                weights=weights,
                weight_unit=weight_unit,
                data_dim=self._data_dim,
                scen_dim=self._scen_dim,
            )
            group_node.get_price().set_level(level)
            group_node.get_price().set_profile(profile)
            group_node.get_price().set_intercept(intercept)
        elif any(prices):
            missing = [key for key in member_node_names if data[key].get_price() is None]
            self.send_warning_event(f"Only some member nodes of group {group_node} have a Price, skip aggregate prices. Missing: {missing}")

    def _replace_node(
        self,
        group_name: str,
        member_node_names: set[str],
        components: dict[str, Component],
        component_to_nodes: dict[str, set[str]],
    ) -> None:
        for name, component in components.items():
            replace_keys = component_to_nodes[name]
            for key in member_node_names:
                if key in replace_keys:
                    component.replace_node(key, group_name)
                    self._replaced_references[name].add((key, group_name))

    def _init_aggregate( # noqa C901
        self,
        components: dict[str, Component],
        data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> None:
        self._grouped_nodes.clear()
        self._internal_transports.clear()
        self._internal_demands.clear()
        self._errors.clear()

        self._aggregation_map = defaultdict(set)

        exogenous_groups = set()

        meta_key = self._meta_key

        for key, component in components.items():
            if not isinstance(component, Node):
                self._aggregation_map[key].add(key)
                continue

            node: Node = component

            commodity = node.get_commodity()

            if self._commodity != commodity:
                self._aggregation_map[key].add(key)
                continue

            meta: Meta | None = node.get_meta(meta_key)

            if meta is None:
                self._errors.add(f"Node {key} had no metadata behind key {meta_key}.")
                continue

            meta: Meta

            if not isinstance(meta, Member):
                got = type(meta).__name__
                message = f"Node {key} has metadata behind key {meta_key} with wrong type. Expected Member, got {got}."
                self._errors.add(message)
                continue

            meta: Member

            group_name: str = meta.get_value()

            if node.is_exogenous():
                # register groups with exogenous Nodes to validate later.
                exogenous_groups.add(group_name)

            if not self._errors:
                self._aggregation_map[key].add(group_name)
                self._grouped_nodes[group_name].add(key)

        grouped_nodes = self._grouped_nodes.copy()

        for group_name in exogenous_groups:  # Check exogenous groups.
            node_keys = grouped_nodes[group_name]
            if len(node_keys) != 1:  # allow unchanged or renamed exogenous Nodes.
                self._errors.add(
                    f"Group {group_name} contains an exogenous Node and must therefore contain only one Node."
                    " Exogenous Nodes cannot be grouped together with other Nodes.",
                )
                # For if we want to allow pure exogenous groups.
                # for node_key in node_keys:
                #     node: Node = components[node_key]
                #     if not node.is_exogenous():
                #         self._errors.add(f"Group {group_name} contains both exogenous and endogenous Nodes. This is not allowed.")
                #         break

        # remove single groups with unchanged names and check for duplicated names
        for group_name, node_keys in grouped_nodes.items():
            if len(node_keys) == 1 and group_name == next(iter(node_keys)):
                del self._grouped_nodes[group_name]
            try:  # If group name already exists for a node and the existing node is not aggregated to a new one.
                meta = data[group_name].get_meta(meta_key)
                if meta is None or meta.get_value() is None:
                    self._errors.add(
                        f"Metadata name for aggregated node ({group_name}) already exists in the model: {data[group_name]}",
                    )
            except KeyError:
                pass

        self._check_uniqueness()
        self._report_errors(self._errors)

    def _report_errors(self, errors: set[str]) -> None:
        if errors:
            n = len(errors)
            s = "s" if n > 1 else ""
            error_str = "\n".join(errors)
            message = f"Found {n} error{s}:\n{error_str}"
            raise RuntimeError(message)

    def _check_uniqueness(self) -> None:
        flipped = defaultdict(set)
        for group, members in self._grouped_nodes.items():
            for member in members:
                flipped[member].add(group)
        for k, v in flipped.items():
            if len(v) > 1:
                self._errors.add(f"Node {k} belong to more than one group {v}")

    def _disaggregate(
        self,
        model: Model,
        original_data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> None:
        new_data = model.get_data()

        deleted_group_names: set[str] = self._init_disaggregate(new_data)

        self._validate_restore_nodes(new_data, deleted_group_names)
        self._restore_nodes(new_data, original_data, deleted_group_names)
        self._restore_references(new_data)

        restorable_transports = self._validate_restore_transports(new_data, original_data, deleted_group_names)
        self._restore_transports(new_data, original_data, restorable_transports)

        self._delete_internal_demands(new_data)

    def _init_disaggregate(
        self,
        new_data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> set[str]:
        self._errors.clear()
        deleted_group_names: set[str] = set()

        for group_name in self._grouped_nodes:
            if group_name not in new_data:
                deleted_group_names.add(group_name)
                continue

            group_node = new_data[group_name]

            if not isinstance(group_node, Node):
                deleted_group_names.add(group_name)

        return deleted_group_names

    def _validate_restore_nodes(
        self,
        new_data: dict[str, Component | TimeVector | Curve | Expr],
        deleted_group_names: set[str],
    ) -> None:
        for group_name, member_node_names in self._grouped_nodes.items():
            if group_name in deleted_group_names:
                continue
            for key in member_node_names:
                if key in new_data:
                    obj = new_data[key]
                    if not isinstance(obj, Node) and obj.get_commodity() == self._commodity:
                        typ = type(obj).__name__
                        message = f"Restoring node {key} from group node {group_name} failed because model already stores object of {typ} with that name."
                        self._errors.add(message)
        self._report_errors(self._errors)

    def _restore_nodes(
        self,
        new_data: dict[str, Component | TimeVector | Curve | Expr],
        original_data: dict[str, Component | TimeVector | Curve | Expr],
        deleted_group_names: set[str],
    ) -> None:
        for group_name, member_node_names in self._grouped_nodes.items():
            if group_name in deleted_group_names:
                continue

            group_node: Node = new_data.pop(group_name)

            group_price: Price | None = group_node.get_price()

            for key in member_node_names:
                original_node: Node = original_data[key]
                if group_price is not None:
                    original_price = original_node.get_price()
                    original_price.copy_from(group_price)
                new_data[key] = original_node

    def _validate_restore_transports(
        self,
        new_data: dict[str, Component | TimeVector | Curve | Expr],
        original_data: dict[str, Component | TimeVector | Curve | Expr],
        deleted_group_names: set[str],
    ) -> set[str]:
        nodes_not_added_back: set[str] = set()
        restorable_transports: set[str] = set()

        components = {k: v for k, v in original_data.items() if isinstance(v, Component)}
        transports = get_transports_by_commodity(components, self._commodity)

        for group_name, member_node_names in self._grouped_nodes.items():
            if group_name in deleted_group_names:
                nodes_not_added_back.update(member_node_names)
                continue

        for key in self._internal_transports:
            from_node, to_node = transports[key]

            if (from_node in nodes_not_added_back) and (to_node in nodes_not_added_back):
                continue

            restorable_transports.add(key)
            if key in new_data:
                obj = new_data[key]
                typ = type(obj).__name__
                message = f"Restoring deleted transport {key} from group node {group_name} failed becausemodel already stores object of {typ} with that name."
                self._errors.add(message)

        self._report_errors(self._errors)

        return restorable_transports

    def _restore_transports(
        self,
        new_data: dict[str, Component | TimeVector | Curve | Expr],
        original_data: dict[str, Component | TimeVector | Curve | Expr],
        restorable_transports: set[str],
    ) -> None:
        for key in self._internal_transports:
            if key not in restorable_transports:
                continue
            transport = original_data[key]
            new_data[key] = transport

    def _delete_internal_demands(self, new_data: dict[str, Component | TimeVector | Curve | Expr]) -> None:
        for key in self._internal_demands:
            new_data.pop(key, None)

    def _restore_references(self, new_data: dict[str, Component | TimeVector | Curve | Expr]) -> None:
        for component_name, replacements in self._replaced_references.items():
            # internal transports are handled by themselves.
            if component_name in new_data and component_name not in self._internal_transports and isinstance(new_data[component_name], Component):
                for replacement in replacements:
                    disaggregated, group_name = replacement
                    new_data[component_name].replace_node(old=group_name, new=disaggregated)  # set the disaggregated node back in the component.
