from __future__ import annotations

import contextlib
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from framcore.attributes import FlowVolume
from framcore.components import Component, Flow, Node
from framcore.expressions import get_unit_conversion_factor
from framcore.expressions._utils import _load_model_and_create_model_db
from framcore.metadata import Member
from framcore.querydbs import QueryDB
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex
from framcore.utils import FlowInfo, get_flow_infos, get_node_to_commodity, get_supported_components

if TYPE_CHECKING:
    from framcore import Model


class RegionalVolumes:
    """
    Container for regional energy volumes.

    Stores production, consumption, import, and export vectors for each node and category.
    Provides methods to access these aggregated results.
    """

    def __init__(self) -> None:
        """Initialize the RegionalVolumes instance with empty dictionaries for production, consumption, import, and export."""
        self._production: dict[str, dict[str, NDArray]] = dict()
        self._consumption: dict[str, dict[str, NDArray]] = dict()
        self._export: dict[str, dict[str, NDArray]] = dict()
        self._import: dict[str, dict[str, NDArray]] = dict()

    def get_production(self) -> dict[str, dict[str, NDArray]]:
        """Return dict with production vector by category for each node."""
        return self._production

    def get_consumption(self) -> dict[str, dict[str, NDArray]]:
        """Return dict with consumption vector by category for each node."""
        return self._consumption

    def get_export(self) -> dict[str, dict[str, NDArray]]:
        """Return nested dict with export vector for each trade partner to an exporting node."""
        return self._export

    def get_import(self) -> dict[str, dict[str, NDArray]]:
        """Return nested dict with import vector for each trade partner to an importing node."""
        return self._import


def _get_meta_value(key: str, v: Node | Flow, category_level: str) -> str:
    """Get member meta value from component."""
    meta = v.get_meta(category_level)
    if not isinstance(meta, Member):
        message = f"Expected for key {key} metadata of type Member, got {meta}"
        raise ValueError(message)
    return meta.get_value()


def _get_vector(
    flow: Flow,
    is_ingoing: bool,
    commodity: str,
    node_to_commodity: dict[str, str],
    db: QueryDB,
    data_period: SinglePeriodTimeIndex,
    scenario_period: FixedFrequencyTimeIndex,
    unit: str,
    is_float32: bool,
) -> FlowVolume:
    arrows = flow.get_arrows()
    if len(arrows) == 1:
        volume = flow.get_volume()
        return volume.get_scenario_vector(
            db=db,
            scenario_horizon=scenario_period,
            level_period=data_period,
            unit=unit,
            is_float32=is_float32,
        )

    arrows = [a for a in flow.get_arrows() if a.is_ingoing() == is_ingoing and node_to_commodity[a.get_node()] == commodity]
    if len(arrows) != 1:
        message = f"Expected one arrow, got {arrows}"
        raise ValueError(message)
    arrow = arrows[0]

    arrow_volumes = flow.get_arrow_volumes()

    if arrow in arrow_volumes:
        volume = arrow_volumes[arrow]
        return volume.get_scenario_vector(
            db=db,
            scenario_horizon=scenario_period,
            level_period=data_period,
            unit=unit,
            is_float32=is_float32,
        )

    # we have to calculate using volume and conversion
    volume = flow.get_volume()

    main_node = flow.get_main_node()
    main_arrows = [a for a in flow.get_arrows() if a.get_node() == main_node]
    if len(main_arrows) != 1:
        message = f"Expected exactly one arrow connected to main node of flow. Got {main_arrows}"
        raise ValueError(message)
    main_arrow = main_arrows[0]

    if arrow == main_arrow:
        return volume.get_scenario_vector(
            db=db,
            scenario_horizon=scenario_period,
            level_period=data_period,
            unit=unit,
            is_float32=is_float32,
        )

    main_units = main_arrow.get_conversion_unit_set(db)
    if not main_units:
        return volume.get_scenario_vector(
            db=db,
            scenario_horizon=scenario_period,
            level_period=data_period,
            unit=unit,
            is_float32=is_float32,
        )

    # we must convert to correct unit
    arrow_units = arrow.get_conversion_unit_set(db)

    a_main_unit = next(iter(main_units))
    a_arrow_unit = next(iter(arrow_units))

    unit_conversion_factor = get_unit_conversion_factor(
        from_unit=f"(({a_arrow_unit}) / ({a_main_unit}))",
        to_unit=unit,
    )

    vector = volume.get_scenario_vector(
        db=db,
        scenario_horizon=scenario_period,
        level_period=data_period,
        unit=a_main_unit,
        is_float32=is_float32,
    )

    if arrow.has_profile():
        conversion_vector = arrow.get_scenario_vector(
            db=db,
            scenario_horizon=scenario_period,
            level_period=data_period,
            unit=a_arrow_unit,
            is_float32=is_float32,
        )
        np.multiply(vector, conversion_vector, out=vector)
        np.multiply(vector, unit_conversion_factor, out=vector)
        return vector

    conversion_value = arrow.get_data_value(
        db=db,
        scenario_horizon=scenario_period,
        level_period=data_period,
        unit=a_arrow_unit,
    )
    np.multiply(vector, conversion_value * unit_conversion_factor, out=vector)

    return vector


# TODO: More options: node_category, consumption_category, production_category, with_trade_partners


def _check_category(category, flow_id, flow_info) -> None:
    pass


def get_regional_volumes(
    db: Model | QueryDB,
    commodity: str,
    node_category: str,
    production_category: str,
    consumption_category: str,
    data_period: SinglePeriodTimeIndex,
    scenario_period: FixedFrequencyTimeIndex,
    unit: str,
    is_float32: bool = True,
) -> RegionalVolumes:
    """Calculate aggregated production, consumption, import and export."""
    db = _load_model_and_create_model_db(db)

    if not isinstance(is_float32, bool):
        message = f"Expected bool for is_float32, got {is_float32}"
        raise ValueError(message)

    domain_components = {k: v for k, v in db.get_data().items() if isinstance(v, Component)}

    graph: dict[str, Node | Flow] = get_supported_components(
        components=domain_components,
        supported_types=(Node, Flow),
        forbidden_types=tuple(),
    )

    flows: dict[str, Flow] = {k: v for k, v in graph.items() if isinstance(v, Flow)}
    nodes: dict[str, Node] = {k: v for k, v in graph.items() if isinstance(v, Node)}

    node_to_commodity = get_node_to_commodity(graph)

    # only nodes of prefered commodity
    nodes_of_commodity: dict[str, Node] = {k: v for k, v in nodes.items() if v.get_commodity() == commodity}

    # Mapping of node to category of prefered node level
    node_to_category: dict[str, str] = {k: _get_meta_value(k, v, node_category) for k, v in nodes_of_commodity.items()}

    category_to_nodes: dict[str, set[str]] = defaultdict(set)
    visited = set()
    for node_id, category in node_to_category.items():
        assert node_id not in visited, f"{node_id} is duplicated"
        category_to_nodes[category].add(node_id)
        visited.add(node_id)

    direct_production: dict[str, dict[str, list[Flow]]] = dict()
    direct_consumption: dict[str, dict[str, list[Flow]]] = dict()
    converted_production: dict[str, dict[str, list[Flow]]] = dict()
    converted_consumption: dict[str, dict[str, list[Flow]]] = dict()
    import_: dict[str, dict[str, list[Flow]]] = dict()
    export: dict[str, dict[str, list[Flow]]] = dict()

    for flow_id, flow in flows.items():
        flow_infos = get_flow_infos(flow, node_to_commodity)

        prod_category = None
        cons_category = None
        with contextlib.suppress(Exception):
            prod_category = _get_meta_value(flow_id, flow, production_category)
        with contextlib.suppress(Exception):
            cons_category = _get_meta_value(flow_id, flow, consumption_category)

        for flow_info in flow_infos:
            flow_info: FlowInfo
            if flow_info.category == "direct_in" and flow_info.commodity_in == commodity:
                _check_category(prod_category, flow_id, flow_info)
                node_category = node_to_category[flow_info.node_in]
                if node_category not in direct_production:
                    direct_production[node_category] = defaultdict(list)
                direct_production[node_category][prod_category].append(flow)

            elif flow_info.category == "conversion" and flow_info.commodity_in == commodity:
                _check_category(prod_category, flow_id, flow_info)
                node_category = node_to_category[flow_info.node_in]
                if node_category not in converted_production:
                    converted_production[node_category] = defaultdict(list)
                converted_production[node_category][prod_category].append(flow)

            elif flow_info.category == "direct_out" and flow_info.commodity_out == commodity:
                _check_category(cons_category, flow_id, flow_info)
                node_category = node_to_category[flow_info.node_out]
                if node_category not in direct_consumption:
                    direct_consumption[node_category] = defaultdict(list)
                direct_consumption[node_category][cons_category].append(flow)

            elif flow_info.category == "conversion" and flow_info.commodity_out == commodity:
                _check_category(cons_category, flow_id, flow_info)
                node_category = node_to_category[flow_info.node_out]
                if node_category not in converted_consumption:
                    converted_consumption[node_category] = defaultdict(list)
                converted_consumption[node_category][cons_category].append(flow)

            elif flow_info.category == "transport":
                if node_to_commodity[flow_info.node_in] != commodity:
                    continue
                category_in = node_to_category[flow_info.node_in]
                category_out = node_to_category[flow_info.node_out]
                if category_in == category_out:
                    continue

                if category_in not in import_:
                    import_[category_in] = defaultdict(list)
                import_[category_in][category_out].append(flow)

                if category_out not in export:
                    export[category_out] = defaultdict(list)
                export[category_out][category_in].append(flow)

    num_periods = scenario_period.get_num_periods()
    dtype = np.float32 if is_float32 else np.float64

    out = RegionalVolumes()

    # direct
    for flow_dict, out_dict, is_ingoing in [(direct_production, out.get_production(), True), (direct_consumption, out.get_consumption(), False)]:
        for node_category, flow_categories in flow_dict.items():
            if node_category not in out_dict:
                out_dict[node_category] = dict()
            for flow_category, flows in flow_categories.items():
                x = np.zeros(num_periods, dtype=dtype)
                for flow in flows:
                    with contextlib.suppress(Exception):
                        vector = _get_vector(
                            flow=flow,
                            is_ingoing=is_ingoing,
                            commodity=commodity,
                            node_to_commodity=node_to_commodity,
                            db=db,
                            scenario_period=scenario_period,
                            data_period=data_period,
                            unit=unit,
                            is_float32=is_float32,
                        )
                        np.add(x, vector, out=x)
                out_dict[node_category][flow_category] = x

    # converted
    for flow_dict, out_dict, is_ingoing in [(converted_production, out.get_production(), True), (converted_consumption, out.get_consumption(), False)]:
        for node_category, flow_categories in flow_dict.items():
            if node_category not in out_dict:
                out_dict[node_category] = dict()
            for flow_category, flows in flow_categories.items():
                x = out_dict[node_category][flow_category] if flow_category in out_dict[node_category] else np.zeros(num_periods, dtype=dtype)
                for flow in flows:
                    with contextlib.suppress(Exception):
                        vector = _get_vector(
                            flow=flow,
                            is_ingoing=is_ingoing,
                            commodity=commodity,
                            node_to_commodity=node_to_commodity,
                            db=db,
                            scenario_period=scenario_period,
                            data_period=data_period,
                            unit=unit,
                            is_float32=is_float32,
                        )
                        np.add(x, vector, out=x)
                out_dict[node_category][flow_category] = x

    # trade
    for flow_dict, out_dict, is_ingoing in [(import_, out.get_import(), True), (export, out.get_export(), False)]:
        for category, trade_partners in flow_dict.items():
            out_dict[category] = dict()
            for trade_partner, flows in trade_partners.items():
                x = np.zeros(num_periods, dtype=dtype)
                for flow in flows:
                    with contextlib.suppress(Exception):
                        vector = _get_vector(
                            flow=flow,
                            is_ingoing=is_ingoing,
                            commodity=commodity,
                            node_to_commodity=node_to_commodity,
                            db=db,
                            scenario_period=scenario_period,
                            data_period=data_period,
                            unit=unit,
                            is_float32=is_float32,
                        )
                        np.add(x, vector, out=x)
                out_dict[category][trade_partner] = x

    return out
