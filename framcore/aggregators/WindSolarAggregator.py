from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from framcore.aggregators._utils import (
    _aggregate_costs,
    _aggregate_result_volumes,
    _aggregate_weighted_expressions,
    _all_detailed_exprs_in_sum_expr,
)
from framcore.aggregators.Aggregator import Aggregator  # full import path so inheritance works
from framcore.attributes import AvgFlowVolume, Cost
from framcore.components import Component, Solar, Wind
from framcore.curves import Curve
from framcore.expressions import Expr, get_level_value
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex
from framcore.timevectors import ConstantTimeVector, TimeVector

if TYPE_CHECKING:
    from framcore import Model


class _WindSolarAggregator(Aggregator):
    """
    Aggregate components into groups based on their power nodes.

    Aggregation steps (self._aggregate):
    1. Group components based on their power nodes (self._group_by_power_node):
    2. Aggregate grouped components into a single aggregated component for each group (self._aggregate_groups):
        - Max_capacity is calculated as the sum of the maximum capacity levels with weighted profiles.
        - Variable operational costs (voc) are aggregated using weighted averages based on the weighting method (now only max_capacity supported).
        - TODO: Add support for additional weighting methods (e.g. production instead of capacity).
        - Production is aggregated as the sum of production levels with weighted profiles. TODO: Add possibility to skip results aggregation.
    2a. Make new hydro module and delete original components from model data.
    3. Add mapping from detailed to aggregated components to self._aggregation_map.

    Disaggregation steps (self._disaggregate):
    1. Restore original components from self._original_data.
    2. Distribute production from aggregated components back to the original components:
        - Results are weighted based on the weighting method (now only max_capacity supported).
    3. Delete aggregated components from the model.

    Comments:
        - It is recommended to only use the same aggregator type once on the same components of a model. If you want to go from one aggregation level to
        another, it is better to use model.disaggregate first and then aggregate again. This is to keep the logic simple and avoid complex expressions.
        We have also logic that recognises if result expressions come from aggregations or disaggregations. When aggregating or disaggregating these,
        we can go back to the original results rather than setting up complex expressions that for examples aggregates the disaggregated results.
        - Levels and profiles are aggregated separately, and then combined into attributes.
        - We have chosen to eagerly evaluate weights for aggregation and disaggregation of levels and profiles. This is a balance between eagerly evaluating
        everything, and setting up complex expressions. Eagerly evaluating everything would require setting up new timevectors after eager evaluation, which
        is not ideal. While setting up complex expressions gives expressions that are harder to work with and slower to query from.

    Attributes:
        _data_dim (SinglePeriodTimeIndex | None): Data dimension for eager evaluation.
        _scen_dim (FixedFrequencyTimeIndex | None): Scenario dimension for eager evaluation.
        _grouped_components (dict[str, set[str]]): Mapping of aggregated components to their detailed components.  agg to detailed

    Parent Attributes (see framcore.aggregators.Aggregator):
        _is_last_call_aggregate (bool | None): Tracks whether the last operation was an aggregation.
        _original_data (dict[str, Component | TimeVector | Curve | Expr] | None): Original detailed data before aggregation.
        _aggregation_map (dict[str, set[str]] | None): Maps aggregated components to their detailed components. detailed to agg

    """

    def __init__(
        self,
        data_dim: SinglePeriodTimeIndex | None = None,
        scen_dim: FixedFrequencyTimeIndex | None = None,
    ) -> None:
        """
        Initialize Aggregator.

        Args:
            data_dim (SinglePeriodTimeIndex): Data dimension for eager evalutation.
            scen_dim (FixedFrequencyTimeIndex): Scenario dimension for eager evalutation.

        """
        super().__init__()
        self._data_dim = data_dim
        self._scen_dim = scen_dim
        self._grouped_components: dict[str, set[str]] = defaultdict(set)

    def _aggregate(self, model: Model) -> None:
        data = model.get_data()

        # Group components by power node and remove groups of size 1
        self._group_by_power_node(data)

        # Aggregate the grouped components
        self._aggregate_groups(model)

        # Remove the original components from the model
        for group_id in self._grouped_components:
            for component_id in self._grouped_components[group_id]:
                del data[component_id]

        # Add mapping to self._aggregation_map
        self._aggregation_map = {member_id: {group_id} for group_id, member_ids in self._grouped_components.items() for member_id in member_ids}

    def _group_by_power_node(self, data: dict[str, Component | TimeVector | Curve | Expr]) -> None:
        """Group components by their power node and remove groups with only one member."""
        self._grouped_components.clear()
        for name, obj in data.items():
            if isinstance(obj, self._component_type):
                power_node = obj.get_power_node()
                if power_node is None:
                    message = f"Component {name} has no power node defined. Cannot group by power node."
                    raise ValueError(message)
                group_id = f"Aggregated{self._component_type.__name__}{power_node}"
                self._grouped_components[group_id].add(name)

        for group_id in list(self._grouped_components.keys()):
            if len(self._grouped_components[group_id]) == 1:
                del self._grouped_components[group_id]

    def _aggregate_groups(self, model: Model) -> None:
        """Aggregate each group of components into a single component."""
        for group_id, member_ids in self._grouped_components.items():
            self._aggregate_group(model, group_id, member_ids)

    def _aggregate_group(self, model: Model, group_id: str, member_ids: list[str]) -> None:
        """Aggregate a group of components into a single component."""
        self.send_info_event(f"{group_id} from {len(member_ids)} components.")
        data = model.get_data()
        members = [data[member_id] for member_id in member_ids]

        # Weights
        capacity_levels = [member.get_max_capacity().get_level() for member in members]
        capacity_profiles = [member.get_max_capacity().get_profile() for member in members]
        vocs = [member.get_voc() for member in members]
        if any(capacity_profiles) or any(vocs):  # only calc capacity weights if needed
            capacity_level_values = [get_level_value(cl, model, "MW", self._data_dim, self._scen_dim, True) for cl in capacity_levels]
            if sum(capacity_level_values) == 0.0:
                message = "All grouped components do not contribute to weights (capacity = 0). Simplified aggregation."
                self.send_warning_event(message)

        # Production capacity
        capacity_levels = [member.get_max_capacity().get_level() for member in members]
        capacity_level = sum(capacity_levels)

        capacity_profile = None
        if any(capacity_profiles) and (sum(capacity_level_values) != 0.0):
            one_profile = Expr(src=ConstantTimeVector(1.0, is_zero_one_profile=False), is_profile=True)
            capacity_profiles = [profile if profile else one_profile for profile in capacity_profiles]
            capacity_profile = _aggregate_weighted_expressions(capacity_profiles, capacity_level_values)

        sum_capacity = AvgFlowVolume(capacity_level, capacity_profile)

        # Power node
        power_node = members[0].get_power_node()

        # Production
        productions = [member.get_production() for member in members]
        production = _aggregate_result_volumes(model, productions, "MW", self._data_dim, self._scen_dim, group_id, member_ids)

        # Variable operational cost
        voc = None
        if any(vocs) and (sum(capacity_level_values) != 0.0):
            voc_level, voc_profile, voc_intercept = _aggregate_costs(model, vocs, outside_weights=capacity_level_values, weight_unit="EUR/MWh")
            voc = Cost(voc_level, voc_profile, voc_intercept)

        new_wind = Wind(
            power_node=power_node,
            max_capacity=sum_capacity,
            voc=voc,
            production=production,
        )

        data[group_id] = new_wind

    def _disaggregate(
        self,
        model: Model,
        original_data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> None:
        new_data = model.get_data()

        deleted_group_names = self._get_deleted_group_components(new_data)
        agg_components = {key: new_data.pop(key) for key in self._grouped_components if key not in deleted_group_names}  # isolate agg modules out of new_data

        # Reinstate original detailed components that are not fully deleted
        for detailed_key, agg_keys in self._aggregation_map.items():
            if agg_keys and all(key in deleted_group_names for key in agg_keys):
                continue
            new_data[detailed_key] = original_data[detailed_key]

        # Set production results in detailed modules
        for agg_key, detailed_keys in self._grouped_components.items():
            if agg_key in deleted_group_names:
                continue

            agg_production_level = agg_components[agg_key].get_production().get_level()
            if agg_production_level is None:  # keep original production if agg has no production defined
                continue
            if len(detailed_keys) == 1:  # only one detailed module, set production directly
                new_data[detailed_key].get_production().set_level(agg_production_level)
                continue
            detailed_production_levels = [new_data[detailed_key].get_production().get_level() for detailed_key in detailed_keys]
            if any(detailed_production_levels) and not all(
                detailed_production_levels,
            ):  # if some but not all detailed components have production defined, skip setting production
                missing = [detailed_key for detailed_key, level in zip(detailed_keys, detailed_production_levels, strict=False) if not level]
                message = f"Some but not all grouped components have production defined. Production not disaggregated for {agg_key}, missing for {missing}."
                self.send_warning_event(message)
                continue
            if _all_detailed_exprs_in_sum_expr(agg_production_level, detailed_production_levels):  # if agg production is sum of detailed levels,  keep original
                continue
            capacity_levels = [new_data[detailed_key].get_max_capacity().get_level() for detailed_key in detailed_keys]
            capacity_level_values = [get_level_value(cl, model, "MW", self._data_dim, self._scen_dim, True) for cl in capacity_levels]
            capacity_level_value_weights = [cl / sum(capacity_level_values) for cl in capacity_level_values]
            production_weights = {detailed_key: weight for detailed_key, weight in zip(detailed_keys, capacity_level_value_weights, strict=False)}
            for detailed_key in detailed_keys:
                self._set_weighted_production(new_data[detailed_key], agg_components[agg_key], production_weights[detailed_key])  # default

    def _get_deleted_group_components(self, new_data: dict[str, Component | TimeVector | Curve | Expr]) -> set[str]:
        """Identify which aggregated components have been deleted from the model."""
        deleted_group_names: set[str] = set()

        for group_name in self._grouped_components:
            if group_name not in new_data:
                deleted_group_names.add(group_name)
                continue

        return deleted_group_names

    def _set_weighted_production(self, detailed_component: Component, agg_component: Component, production_weight: float) -> None:
        """Set production level and profile for detailed components based on aggregated component."""
        agg_production_level = agg_component.get_production().get_level()
        agg_production_profile = agg_component.get_production().get_profile()
        production_level = production_weight * agg_production_level
        detailed_component.get_production().set_level(production_level)
        detailed_component.get_production().set_profile(agg_production_profile)


class WindAggregator(_WindSolarAggregator):
    """
    Aggregate components into groups based on their power nodes.

    Aggregation steps (self._aggregate):
    1. Group components based on their power nodes (self._group_by_power_node):
    2. Aggregate grouped components into a single aggregated component for each group (self._aggregate_groups):
        - Max_capacity is calculated as the sum of the maximum capacity levels with weighted profiles.
        - Variable operation costs (voc) are aggregated using weighted averages based on the weighting method (now ony max_capacity supported).
        - TODO: Add support for additional weighting methods (e.g. production instead of capacity).
        - Production is aggregated as the sum of production levels with weighted profiles.
    2a. Make new hydro module and delete original components from model data.
    3. Add mapping from detailed to aggregated components to self._aggregation_map.

    Disaggregation steps (self._disaggregate):
    1. Restore original components from self._original_data.
    2. Distribute production from aggregated components back to the original components:
        - Results are weighted based on the weighting method (now ony max_capacity supported).
    3. Delete aggregated components from the model.

    Comments:
        - It is recommended to only use the same aggregator type once on the same components of a model. If you want to go from one aggregation level to
        another, it is better to use model.disaggregate first and then aggregate again. This is to keep the logic simple and avoid complex expressions.
        We have also logic that recognises if result expressions come from aggregations or disaggregations. When aggregating or disaggregating these,
        we can go back to the original results rather than setting up complex expressions that for examples aggregates the disaggregated results.
        - Levels and profiles are aggregated separately, and then combined into attributes.
        - We have chosen to eagerly evaluate weights for aggregation of levels and profiles, and disaggregation. This is a balance between eagerly evaluating
        everything, and setting up complex expressions. Eagerly evaluating everything would require setting up new timevectors after eager evaluation, which
        is not ideal. While setting up complex expressions gives expressions that are harder to work with and slower to query from.

    Attributes:
        _data_dim (SinglePeriodTimeIndex | None): Data dimension for eager evaluation.
        _scen_dim (FixedFrequencyTimeIndex | None): Scenario dimension for eager evaluation.
        _grouped_components (dict[str, set[str]]): Mapping of aggregated components to their detailed components.  agg to detailed

    Parent Attributes (see framcore.aggregators.Aggregator):
        _is_last_call_aggregate (bool | None): Tracks whether the last operation was an aggregation.
        _original_data (dict[str, Component | TimeVector | Curve | Expr] | None): Original detailed data before aggregation.
        _aggregation_map (dict[str, set[str]] | None): Maps aggregated components to their detailed components. detailed to agg

    """

    _component_type = Wind


class SolarAggregator(_WindSolarAggregator):
    """
    Aggregate components into groups based on their power nodes.

    Aggregation steps (self._aggregate):
    1. Group components based on their power nodes (self._group_by_power_node):
    2. Aggregate grouped components into a single aggregated component for each group (self._aggregate_groups):
        - Max_capacity is calculated as the sum of the maximum capacity levels with weighted profiles.
        - Variable operation costs (voc) are aggregated using weighted averages based on the weighting method (now ony max_capacity supported).
        - TODO: Add support for additional weighting methods (e.g. production instead of capacity).
        - Production is aggregated as the sum of production levels with weighted profiles.
    2a. Make new hydro module and delete original components from model data.
    3. Add mapping from detailed to aggregated components to self._aggregation_map.

    Disaggregation steps (self._disaggregate):
    1. Restore original components from self._original_data.
    2. Distribute production from aggregated components back to the original components:
        - Results are weighted based on the weighting method (now ony max_capacity supported).
    3. Delete aggregated components from the model.

    Comments:
        - It is recommended to only use the same aggregator type once on the same components of a model. If you want to go from one aggregation level to
        another, it is better to use model.disaggregate first and then aggregate again. This is to keep the logic simple and avoid complex expressions.
        We have also logic that recognises if result expressions come from aggregations or disaggregations. When aggregating or disaggregating these,
        we can go back to the original results rather than setting up complex expressions that for examples aggregates the disaggregated results.
        - Levels and profiles are aggregated separately, and then combined into attributes.
        - We have chosen to eagerly evaluate weights for aggregation of levels and profiles, and disaggregation. This is a balance between eagerly evaluating
        everything, and setting up complex expressions. Eagerly evaluating everything would require setting up new timevectors after eager evaluation, which
        is not ideal. While setting up complex expressions gives expressions that are harder to work with and slower to query from.

    Attributes:
        _data_dim (SinglePeriodTimeIndex | None): Data dimension for eager evaluation.
        _scen_dim (FixedFrequencyTimeIndex | None): Scenario dimension for eager evaluation.
        _grouped_components (dict[str, set[str]]): Mapping of aggregated components to their detailed components.  agg to detailed

    Parent Attributes (see framcore.aggregators.Aggregator):
        _is_last_call_aggregate (bool | None): Tracks whether the last operation was an aggregation.
        _original_data (dict[str, Component | TimeVector | Curve | Expr] | None): Original detailed data before aggregation.
        _aggregation_map (dict[str, set[str]] | None): Maps aggregated components to their detailed components. detailed to agg

    """

    _component_type = Solar
