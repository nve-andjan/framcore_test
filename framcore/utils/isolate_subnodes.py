"""Demo to show how we can use the core to write some functions we need."""

from collections import defaultdict
from copy import copy
from time import time

from framcore import Model
from framcore.components import Component, Flow, Node
from framcore.events import send_debug_event
from framcore.utils import get_node_to_commodity, get_supported_components, is_transport_by_commodity


def _is_boundary_flow(flow: Flow, nodes: set[str]) -> bool:
    arrows = flow.get_arrows()
    x, y = tuple(arrows)  # has len 2
    return int(x.get_node() in nodes) + int(y.get_node() in nodes) == 1


def _is_member(node: Node, meta_key: str, members: set[str]) -> bool:
    meta = node.get_meta(meta_key)
    value = meta.get_value()
    return value in members


def isolate_subnodes(model: Model, commodity: str, meta_key: str, members: list[str]) -> None:
    """
    Delete nodes of commodity named using meta_key except members and boundary nodes and flows.

    Boudary nodes are set exogenous and all flows pointing to them except boundary flows into or out from member nodes.
    """
    t = time()

    data = model.get_data()
    counts_before = model.get_content_counts()

    has_not_converged = True
    num_iterations = 0

    while has_not_converged:
        num_iterations += 1

        n_data_before = len(data)

        # We need copy of components to set _parent None so component becomes top_parent in upcoming code
        components: dict[str, Component] = {k: copy(v) for k, v in data.items() if isinstance(v, Component)}
        for c in components.values():
            c: Component
            c._parent = None  # noqa: SLF001

        node_to_commodity = get_node_to_commodity(components)

        parent_keys: dict[Component, str] = {v: k for k, v in components.items()}

        graph: dict[str, Node | Flow] = get_supported_components(components, (Node, Flow), tuple())

        parent_to_components = defaultdict(set)
        for c in graph.values():
            parent_to_components[c.get_top_parent()].add(c)

        nodes: dict[str, Node] = {k: v for k, v in graph.items() if isinstance(v, Node)}
        flows: dict[str, Flow] = {k: v for k, v in graph.items() if isinstance(v, Flow)}

        commodity_nodes: dict[str, Node] = {k: v for k, v in nodes.items() if commodity == v.get_commodity()}
        for k, v in commodity_nodes.items():
            assert v.get_meta(meta_key), f"missing meta_key {meta_key} node_id {k}"

        inside_nodes: dict[str, Node] = {k: v for k, v in commodity_nodes.items() if _is_member(v, meta_key, members)}

        transports: dict[str, Flow] = {k: v for k, v in flows.items() if is_transport_by_commodity(v, node_to_commodity, commodity)}

        boundary_flows: dict[str, Flow] = {k: v for k, v in transports.items() if _is_boundary_flow(v, inside_nodes.keys())}

        boundary_nodes: dict[str, Node] = dict()
        for flow_id, flow in boundary_flows.items():
            for a in flow.get_arrows():
                node_id = a.get_node()
                if node_id not in inside_nodes:
                    boundary_nodes[node_id] = nodes[node_id]

        outside_nodes: dict[str, Node] = {k: v for k, v in commodity_nodes.items() if not (k in inside_nodes or k in boundary_nodes)}

        deletes: set[str] = set()

        deletes.update(outside_nodes.keys())
        deletes.update(boundary_nodes.keys())  # will be kept in delete step below
        deletes.update(boundary_flows.keys())  # will be kept in delete step below

        # delete flows delivering to deleted node
        for k, flow in flows.items():
            for a in flow.get_arrows():
                if a.get_node() in deletes:
                    deletes.add(k)
                    break  # goto next k, flow

        # needed for next two steps
        node_to_flows: dict[str, set[str]] = defaultdict(set)
        flow_to_nodes: dict[str, set[str]] = defaultdict(set)
        for flow_id, flow in flows.items():
            for arrow in flow.get_arrows():
                node_id = arrow.get_node()
                node_to_flows[node_id].add(flow_id)
                flow_to_nodes[flow_id].add(node_id)

        # delete disconnected subgraphs
        remaining = set(n for n in nodes if n not in commodity_nodes)
        while remaining:
            is_disconnected_subgraph = True
            subgraph = set()
            possible_members = set()
            possible_members.add(remaining.pop())
            while possible_members:
                member = possible_members.pop()
                if member in subgraph:  # avoid cycle
                    continue
                if member in flows:
                    subgraph.add(member)
                    for node in flow_to_nodes[member]:
                        if node not in outside_nodes or node not in boundary_nodes:
                            possible_members.add(node)
                            if node in inside_nodes:
                                is_disconnected_subgraph = False
                else:
                    subgraph.add(member)
                    for flow in node_to_flows[member]:
                        possible_members.add(flow)
            if is_disconnected_subgraph:
                deletes.update(subgraph)

        for key in deletes:
            if (key in boundary_flows) or (key in boundary_nodes):
                continue

            if key not in graph:
                continue

            parent_key = parent_keys[graph[key].get_top_parent()]

            if parent_key in data:
                del data[parent_key]

        n_data_after = len(data)

        if n_data_after == n_data_before:
            has_not_converged = False

    counts_after = model.get_content_counts()

    added_components = counts_after["components"] - counts_before["components"]
    if added_components.total() > 0:
        message = f"Expected only deleted components. Got additions {added_components}"
        raise RuntimeError(message)

    deleted_components = counts_before["components"] - counts_after["components"]

    for node_id in boundary_nodes:
        if node_id in data:
            node: Node = data[node_id]
            node.set_exogenous()
            if not node.get_price().has_level():
                message = f"{node_id} set to be exogenous, but no price is available."
                raise RuntimeError(message)

    send_debug_event(isolate_subnodes, f"Used {num_iterations} iterations and {round(time() - t, 2)} seconds and deleted {deleted_components}")
