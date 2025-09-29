from __future__ import annotations  # NB! added for type hint to work

from collections import defaultdict
from typing import TYPE_CHECKING

from framcore import Base
from framcore.components import Component, Flow, Node
from framcore.utils import get_supported_components

if TYPE_CHECKING:
    from framcore import Model


class FlowInfo(Base):
    """Holds info about one or two related Arrows of a Flow."""

    def __init__(
        self,
        category: str,
        node_out: str | None = None,
        commodity_out: str | None = None,
        node_in: str | None = None,
        commodity_in: str | None = None,
    ) -> None:
        """
        Based on its arrows, we derive properties about a Flow.

        We use this class to store such info.
        """
        self.category = category
        self.node_out = node_out
        self.commodity_out = commodity_out
        self.node_in = node_in
        self.commodity_in = commodity_in


def _check_type(value: object, expected) -> None:  # noqa: ANN001
    assert isinstance(value, expected), f"Expected {expected}. Got {type(value.__name__)}."


def get_node_to_commodity(data: dict[str, object]) -> dict[str, str]:
    """Return dict with commodity (str) for each node id (str) in data."""
    _check_type(data, dict)

    components = {k: v for k, v in data.items() if isinstance(v, Component)}
    for k in components:
        assert isinstance(k, str), f"Got invalid key {k}"

    g = get_supported_components(components, (Node, Flow), tuple())

    out = dict()
    for k, v in g.items():
        if isinstance(v, Node):
            _check_type(k, str)
            out[k] = v.get_commodity()
    return out


def get_flow_infos(flow: Flow, node_to_commodity: dict[str, str]) -> list[FlowInfo]:
    """Get flow infos from analysis of all its arrows."""
    _check_type(flow, Flow)
    _check_type(node_to_commodity, dict)

    arrows = flow.get_arrows()

    if len(arrows) == 1:
        arrow = next(iter(arrows))
        node_id = arrow.get_node()

        if node_id not in node_to_commodity:
            message = f"node_id {node_id} missing from node_to_commodity for flow\n{flow}"
            raise RuntimeError(message)

        commodity = node_to_commodity[node_id]
        if arrow.is_ingoing():
            info = FlowInfo(
                "direct_in",
                node_in=node_id,
                commodity_in=commodity,
            )
        else:
            info = FlowInfo(
                "direct_out",
                node_out=node_id,
                commodity_out=commodity,
            )
        return [info]

    seen: set[tuple[str, str]] = set()
    infos: list[FlowInfo] = []
    for x in arrows:
        for y in arrows:
            if x is y:
                continue

            if x.is_ingoing() != y.is_ingoing():
                arrow_in = x if x.is_ingoing() else y
                arrow_out = x if y.is_ingoing() else y

                node_in = arrow_in.get_node()
                node_out = arrow_out.get_node()

                if node_in not in node_to_commodity:
                    message = f"node_in {node_in} missing from node_to_commodity for flow\n{flow}"
                    raise RuntimeError(message)

                if node_out not in node_to_commodity:
                    message = f"node_out {node_out} missing from node_to_commodity for flow\n{flow}"
                    raise RuntimeError(message)

                commodity_in = node_to_commodity[node_in]
                commodity_out = node_to_commodity[node_out]

                info = FlowInfo(
                    category="transport" if commodity_in == commodity_out else "conversion",
                    node_in=node_in,
                    commodity_in=commodity_in,
                    node_out=node_out,
                    commodity_out=commodity_out,
                )
                key = (node_in, node_out)
                if key in seen:
                    continue

                infos.append(info)
                seen.add(key)

    for arrow in arrows:
        node = arrow.get_node()
        if any(node in [info.node_in, info.node_out] for info in infos):
            continue
        node_id = arrow.get_node()
        commodity = node_to_commodity[node_id]
        if arrow.is_ingoing():
            info = FlowInfo(
                "direct_in",
                node_in=node_id,
                commodity_in=commodity,
            )
        else:
            info = FlowInfo(
                "direct_out",
                node_out=node_id,
                commodity_out=commodity,
            )
        infos.append(info)

    return infos


def get_component_to_nodes(data: Model | dict[str, object]) -> dict[str, set[str]]:
    """For each str key in data where value is a Comonent find all Node id str in data directly connected to the Component."""
    from framcore import Model  # noqa: PLC0415

    _check_type(data, Model | dict)

    if isinstance(data, Model):
        data = data.get_data()

    components = {k: v for k, v in data.items() if isinstance(v, Component)}
    for k in components:
        assert isinstance(k, str), f"Got invalid key {k}"

    g = get_supported_components(components, (Node, Flow), tuple())

    nodes = {k: v for k, v in g.items() if isinstance(v, Node)}
    flows = {k: v for k, v in g.items() if isinstance(v, Flow)}

    domain_nodes = {k: v for k, v in nodes.items() if (k in components) and isinstance(v, Node)}
    assert all(isinstance(v, Node) for v in domain_nodes.values())

    parent_keys = {v: k for k, v in components.items()}

    out = defaultdict(set)
    for flow in flows.values():
        parent_key = parent_keys[flow.get_top_parent()]
        for a in flow.get_arrows():
            node_id = a.get_node()
            if node_id in domain_nodes:
                out[parent_key].add(node_id)

    return out


def get_transports_by_commodity(data: Model | dict[str, object], commodity: str) -> dict[str, tuple[str, str]]:
    """Return dict with key component_id and value (from_node_id, to_node_id) where both nodes belong to given commodity."""
    from framcore import Model  # noqa: PLC0415

    _check_type(data, Model | dict)
    _check_type(commodity, str)

    if isinstance(data, Model):
        data = data.get_data()

    components = {k: v for k, v in data.items() if isinstance(v, Component)}
    for k in components:
        assert isinstance(k, str), f"Got invalid key {k}"

    node_to_commodity = get_node_to_commodity(components)

    g = get_supported_components(components, (Node, Flow), tuple())

    flows = {k: v for k, v in g.items() if isinstance(v, Flow)}

    parent_keys = {v: k for k, v in components.items()}

    out = dict()
    for flow in flows.values():
        parent_key = parent_keys[flow.get_top_parent()]
        infos = get_flow_infos(flow, node_to_commodity)
        if len(infos) != 1:
            continue
        info = infos[0]
        if info.category != "transport":
            continue
        if info.commodity_in != commodity:
            continue
        out[parent_key] = (info.node_out, info.node_in)

    return out


def is_transport_by_commodity(flow: Flow, node_to_commodity: dict[str, str], commodity: str) -> bool:
    """Return True if flow is a transport of the given commodity."""
    _check_type(flow, Flow)
    _check_type(node_to_commodity, dict)
    arrows = flow.get_arrows()
    try:
        x, y = tuple(arrows)
        opposite_directions = x.is_ingoing() != y.is_ingoing()
        x_commodity = node_to_commodity[x.get_node()]
        y_commodity = node_to_commodity[y.get_node()]
        correct_commodity = x_commodity == y_commodity == commodity
        return opposite_directions and correct_commodity
    except Exception:
        return False
