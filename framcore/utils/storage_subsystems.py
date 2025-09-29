from __future__ import annotations  # NB! added for type hint to work

from collections import defaultdict

from framcore import Model
from framcore.components import Component, Flow, Node
from framcore.utils import get_supported_components


# TODO: Finish implementation, test and demo
def get_storage_subsystems(domain_components: dict[str, Component] | Model) -> dict[str, set[str]]:
    if isinstance(domain_components, Model):
        domain_components = {k: v for k, v in domain_components.get_data() if isinstance(v, Component)}

    # translate domain_components to graph consisting of just Flow and Node components
    graph: dict[str, Flow | Node] = get_supported_components(
        components=domain_components,
        supported_types=(Node, Flow),
    )

    abstract_subsystems, __ = get_one_commodity_storage_subsystems(graph, include_boundaries=True)

    # TODO: Use Component.get_top_level to lift abstract_subsystems back to domain_components
    domain_subsystems = abstract_subsystems

    return domain_subsystems


def get_one_commodity_storage_subsystems(
    graph: dict[str, Node | Flow],
    include_boundaries: bool,
) -> dict[str, tuple[str, set[str], set[str]]]:
    """
    Group all storage subsystems belonging to same commodity.

    Returns dict[subsystem_id, (domain_commodity, member_component_ids, boundary_domain_commodities)]

    The boundary_domain_commodities of the output is a set of boundary commodities.
    Some algorithms can only handle one boundary commodity, so this output is useful
    to verify that those conditions apply, and to derive conversion factor unit,
    which need both storage_commodity unit and boundray_commodity unit.

    If include_boundaries is False only nodes with same commodity as storage_node will
    be included in the subsystem.
    """
    if not all(isinstance(c, Flow | Node) for c in graph.values()):
        invalid = {k: v for k, v in graph.items() if not isinstance(v, Flow | Node)}
        message = f"All values in graph must be Flow or Node objects. Found invalid objects: {invalid}"
        raise ValueError(message)

    flows: dict[str, Flow] = {k: v for k, v in graph.items() if isinstance(v, Flow)}
    nodes: dict[str, Node] = {k: v for k, v in graph.items() if isinstance(v, Node)}

    storage_nodes: dict[str, Node] = {k: v for k, v in nodes.items() if v.get_storage()}

    node_to_flows: dict[str, set[str]] = defaultdict(set)
    flow_to_nodes: dict[str, set[str]] = defaultdict(set)
    for flow_id, flow in flows.items():
        for arrow in flow.get_arrows():
            node_id = arrow.get_node()
            node_to_flows[node_id].add(flow_id)
            flow_to_nodes[flow_id].add(node_id)

    out = dict()
    allocated: set[str] = set()
    for storage_node_id, storage_node in storage_nodes.items():
        if storage_node_id in allocated:
            continue

        subsystem_id = storage_node_id
        storage_commodity = storage_node.get_commodity()

        member_component_ids: set[str] = set()
        boundary_commodities: set[str] = set()

        visited: set[str] = set()
        remaining: set[str] = set()

        remaining.add(storage_node_id)

        while remaining:
            component_id = remaining.pop()
            if component_id in visited:
                continue

            visited.add(component_id)

            if component_id in nodes:
                node: Node = nodes[component_id]
                node_commodity = node.get_commodity()

                if node_commodity == storage_commodity:
                    allocated.add(component_id)
                    remaining.update(node_to_flows.get(component_id, set()))
                else:
                    boundary_commodities.add(node_commodity)

                if include_boundaries or node_commodity == storage_commodity:
                    member_component_ids.add(component_id)

            else:
                remaining.update(flow_to_nodes.get(component_id, set()))
                member_component_ids.add(component_id)

        out[subsystem_id] = (storage_commodity, member_component_ids, boundary_commodities)

    return out
