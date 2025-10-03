from __future__ import annotations

from collections import defaultdict
from time import time
from typing import TYPE_CHECKING

from framcore.aggregators import Aggregator
from framcore.aggregators._utils import (
    _aggregate_result_volumes,
    _aggregate_weighted_expressions,
    _all_detailed_exprs_in_sum_expr,
    _get_level_profile_weights_from_disagg_levelprofiles,
)
from framcore.attributes import AvgFlowVolume, Conversion, HydroGenerator, HydroReservoir, MaxFlowVolume, StockVolume
from framcore.components import Component, HydroModule
from framcore.curves import Curve
from framcore.expressions import Expr, get_level_value
from framcore.metadata import LevelExprMeta
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex
from framcore.timevectors import ConstantTimeVector, TimeVector
from framcore.utils import get_hydro_downstream_energy_equivalent

if TYPE_CHECKING:
    from framcore import Model


class HydroAggregator(Aggregator):
    """
    Aggregate hydro modules into two equivalent modules based on the regulation factor, into one regulated and one unregulated module per area.

    Aggregation steps (self._aggregate):
    1. Group modules based on their power nodes (self._group_modules_by_power_node)
        - Modules with generators are grouped based on their power nodes.
        - Reservoirs are assigned to the power node which has the highest cumulative energy equivalent downstream of the reservoir. This is because JulES
        currently only support one-to-one mapping of detailed and aggregated reservoirs.
        - Reservoirs without generators downstream are ignored in the aggregation.
        - TODO: Add possibility to only aggregate HydroModules in certain areas, so that different areas can have different aggregation levels.
    2. Group area modules into regulated and unregulated based on regulation factor (self._group_modules_by_regulation_factor)
        - Regulation factor = upstream reservoir capacity / yearly upstream inflow. Modules with generators that have regulation factor <= self._ror_threshold
        are grouped into unregulated run-of-river modules, the other modules with generators are grouped into regulated reservoir modules.
        - All reservoirs are assigned to the regulated group.
        - Generators without upstream inflows are ignored in the aggregation.
    3. Make aggregated hydro module for each group (self._aggregate_groups)
        - The resulting HydroModule has a generator with energy equivalent of 1 kWh/m3. The inflow, discharge capacity and reservoir capacity
        is calculated based on energy and transformed back to water using this energy equivalent.
        - Generation capacity (release_cap*energy_equivalent/agg_energy_equivalent, capacity of hydraulic couplings not double counted)
        - Energy reservoir capacity (res_cap*energy_equivalent_downstream/agg_energy_equivalent)
        - Gross energy inflow (inflow_up*energy_equivalent/agg_energy_equivalent) - TODO: Add possibility to adjust inflow to closer represent net inflow
        - Inflow profiles weighted based on gross energy inflow (inflow_up_per_profile*energy_equivalent) - calc from core model using self._map_topology()
        - TODO: Other details like pumps and environmental constraints are currently ignored in the aggregation.
    3a. Aggregate results if all modules in group have results.
        - Production is the sum of production levels with weighted profiles
        - Reservoir filling is the sum of energy reservoir filling levels (filling*energy_equivalent_downstream/agg_energy_equivalent) with weighted profiles
        - TODO: Spill, bypass and pumping results are currently ignored in the aggregation.
        - TODO: Add possibility to skip results aggregation.
    3b. Make new hydro module and delete original modules from model data.
    4. Add mapping from detailed to aggregated modules to self._aggregation_map.

    Disaggregation steps (self._disaggregate):
    1. Restore original modules from self._original_data.
    2. Move production and filling results from aggregated modules to detailed modules, weighted based on production capacity and reservoir capacity.
        - TODO: Spill and bypass results are currently ignored in the disaggregation.
    3. Delete aggregated modules.

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
        _metakey_energy_eq_downstream (str): Metadata key for energy equivalent downstream.
        _data_dim (SinglePeriodTimeIndex): Data dimension for eager evalutation.
        _scen_dim (FixedFrequencyTimeIndex): Scenario dimension for eager evalutation.
        _grouped_modules (dict[str, set[str]]): Mapping of aggregated modules to detailed modules. agg to detailed
        _grouped_reservoirs (dict[str, set[str]]): Mapping of aggregated reservoirs to detailed reservoirs. agg to detailed
        _ror_threshold (float): Regulation factor (upstream reservoir capacity / yearly upstream inflow) threshold for run-of-river classification.
            Default is 0.5.

    Parent Attributes (see framcore.aggregators.Aggregator):
        _is_last_call_aggregate (bool | None): Tracks whether the last operation was an aggregation.
        _original_data (dict[str, Component | TimeVector | Curve | Expr] | None): Original detailed data before aggregation.
        _aggregation_map (dict[str, set[str]] | None): Maps aggregated components to their detailed components. detailed to agg

    """

    def __init__(
        self,
        metakey_energy_eq_downstream: str,
        data_dim: SinglePeriodTimeIndex,
        scen_dim: FixedFrequencyTimeIndex,
        ror_threshold: float = 0.5,
    ) -> None:
        """
        Initialize HydroAggregator.

        Args:
            metakey_energy_eq_downstream (str): Metadata key for energy equivalent downstream.
                Can be calculated with framcore.utils.set_global_energy_equivalent
            data_dim (SinglePeriodTimeIndex): Data dimension for eager evalutation.
            scen_dim (FixedFrequencyTimeIndex): Scenario dimension for eager evalutation.
            ror_threshold (float): Regulation factor (upstream reservoir capacity / yearly upstream inflow) threshold for run-of-river classification.
                Default is 0.5.

        """
        super().__init__()
        self._check_type(metakey_energy_eq_downstream, str)
        self._check_type(ror_threshold, float)
        assert ror_threshold >= 0, ValueError(f"ror_threshold must be non-negative, got {ror_threshold}.")
        self._check_type(data_dim, SinglePeriodTimeIndex)
        self._check_type(scen_dim, FixedFrequencyTimeIndex)

        self._metakey_energy_eq_downstream = metakey_energy_eq_downstream
        self._ror_threshold = ror_threshold

        self._data_dim = data_dim
        self._scen_dim = scen_dim

        self._grouped_modules: dict[str, set[str]] = defaultdict(list)  # agg to detailed
        self._grouped_reservoirs: dict[str, set[str]] = defaultdict(list)  # agg to detailed

    def _aggregate(self, model: Model) -> None:
        t0 = time()
        data = model.get_data()

        t = time()
        upstream_topology = self._map_upstream_topology(data)
        self.send_debug_event(f"_map_upstream_topology time: {round(time() - t, 3)} seconds")

        t = time()
        generator_module_groups, reservoir_module_groups = self._group_modules_by_power_node(model, upstream_topology)
        self.send_debug_event(f"_group_modules_by_power_node time: {round(time() - t, 3)} seconds")

        t = time()
        self._group_modules_by_regulation_factor(model, generator_module_groups, reservoir_module_groups, upstream_topology)
        self.send_debug_event(f"_group_modules_by_regulation_factor time: {round(time() - t, 3)} seconds")

        t = time()
        ignore_production_capacity_modules = self._ignore_production_capacity_modules(model)
        self.send_debug_event(f"_ignore_production_capacity_modules time: {round(time() - t, 3)} seconds")

        t = time()
        self._aggregate_groups(model, upstream_topology, ignore_production_capacity_modules)
        self.send_debug_event(f"_aggregate_groups time: {round(time() - t, 3)} seconds")

        # Add reservoir modules to aggregation map
        t = time()
        self._aggregation_map = {dd: set([a]) for a, d in self._grouped_reservoirs.items() for dd in d}
        self.send_debug_event(f"add reservoir modules to _aggregation_map time: {round(time() - t, 3)} seconds")

        # Add generator modules to aggregation map
        t = time()
        for a, d in self._grouped_modules.items():
            for dd in d:
                if dd not in self._aggregation_map:
                    self._aggregation_map[dd] = set([a])
                elif not data[dd].get_reservoir():  # if reservoir module already in map, skip as reservoir mapping is main mapping
                    self._aggregation_map[dd].add(a)
        self.send_debug_event(f"add generator modules to _aggregation_map time: {round(time() - t, 3)} seconds")

        # Delete detailed modules and add remaining modules to aggregation map
        t = time()
        hydromodules = [key for key, component in data.items() if isinstance(component, HydroModule)]
        for m_key in hydromodules:
            if m_key not in self._grouped_modules:
                if not (m_key in self._aggregation_map or m_key in self._grouped_reservoirs):
                    self._aggregation_map[m_key] = set()
                del model.get_data()[m_key]
        self.send_debug_event(f"delete detailed modules time: {round(time() - t, 3)} seconds")

        self.send_debug_event(f"total _aggregate: {round(time() - t0, 3)} seconds")

    def _map_upstream_topology(
        self,
        data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> dict[str, list[str]]:
        """Map HydroModules topology. Return dict[module, List[upstream modules + itself]]."""
        module_names = [key for key, component in data.items() if isinstance(component, HydroModule)]

        # Direct upstream mapping (including transport pumps)
        direct_upstream = {module_name: [] for module_name in module_names}
        for module_name in module_names:
            release_to = data[module_name].get_release_to()
            pump = data[module_name].get_pump()
            if data[module_name].get_pump() and pump.get_from_module() == module_name:  # transport pump
                pump = data[module_name].get_pump()
                pump_to = pump.get_to_module()
                direct_upstream[pump_to].append(module_name)
            elif release_to:  # other
                try:
                    direct_upstream[release_to].append(module_name)
                except KeyError as e:
                    message = f"Reference to {release_to} does not exist in Model. Referenced by {module_name} Module."
                    raise KeyError(message) from e

        # Recursive upstream function
        def find_all_upstream(
            module_name: str,
            visited: set,
            data: dict[str, Component | TimeVector | Curve | Expr],
        ) -> list[str]:
            if module_name in visited:
                return []  # Avoid circular dependencies
            visited.add(module_name)
            upstream_names = direct_upstream[module_name]
            all_upstream = set(upstream_names)
            for upstream in upstream_names:
                all_upstream.update(find_all_upstream(upstream, visited, data))
            all_upstream.add(module_name)  # include itself
            return visited

        # Full upstream topology
        topology = {}
        for module_name in module_names:
            topology[module_name] = list(find_all_upstream(module_name, set(), data))

        return topology

    def _build_upstream_reservoir_and_inflow_exprs(
        self,
        data: dict[str, Component | TimeVector | Curve | Expr],
        upstream_topology: dict[str, list[str]],
    ) -> tuple[dict[str, Expr], dict[str, Expr]]:
        """Build upstream inflow and reservoir expressions for each generator module."""
        upstream_inflow_exprs = dict[str, Expr]()
        upstream_reservoir_exprs = dict[str, Expr]()
        generator_modules = [key for key, module in data.items() if isinstance(module, HydroModule) and module.get_generator()]
        for m in generator_modules:
            inflow_expr = 0
            reservoir_expr = 0
            for mm in upstream_topology[m]:
                inflow = data[mm].get_inflow()
                if inflow:
                    inflow_expr += inflow.get_level()
                reservoir = data[mm].get_reservoir()
                if reservoir:
                    reservoir_expr += reservoir.get_capacity().get_level()

            upstream_inflow_exprs[m] = inflow_expr
            upstream_reservoir_exprs[m] = reservoir_expr

        return upstream_inflow_exprs, upstream_reservoir_exprs

    def _group_modules_by_power_node(self, model: Model, upstream_topology: dict[str, list[str]]) -> dict[str, list[str]]:
        """Group modules by power node. Return generator_module_groups, reservoir_module_groups."""
        data = model.get_data()
        generator_module_groups = defaultdict(list)  # power_node -> generator_modules
        reservoir_mapping = defaultdict(set)  # reservoir -> power_node(s)
        for key, component in data.items():
            if isinstance(component, HydroModule) and component.get_generator():
                power_node = component.get_generator().get_power_node()
                generator_module_groups[power_node].append(key)

                for m in upstream_topology[key]:
                    if data[m].get_reservoir():
                        reservoir_mapping[m].add(power_node)

        # Group reservoirs to the power node with the highest cumulative energy equivalent downstream from the reservoir
        reservoir_module_groups: dict[str, list[str]] = defaultdict(list)
        for res_name in reservoir_mapping:
            power_nodes = reservoir_mapping[res_name]
            if len(power_nodes) > 1:
                highest_power_node = max(
                    power_nodes,
                    key=lambda pn: get_level_value(
                        get_hydro_downstream_energy_equivalent(data, res_name, pn),
                        db=model,
                        unit="kWh/m3",
                        data_dim=self._data_dim,
                        scen_dim=self._scen_dim,
                        is_max=False,
                    ),
                )
                reservoir_module_groups[highest_power_node].append(res_name)
            else:
                reservoir_module_groups[next(iter(power_nodes))].append(res_name)

        return generator_module_groups, reservoir_module_groups

    def _group_modules_by_regulation_factor(
        self,
        model: Model,
        generator_module_groups: dict[str, list[str]],
        reservoir_module_groups: dict[str, list[str]],
        upstream_topology: dict[str, list[str]],
    ) -> None:
        """
        Group modules into regulated and unregulated based on regulation factor and self._ror_threshold.

        Regulation factor = upstream reservoir capacity / yearly upstream inflow.
        Run-of-river = regulation factor <= self._ror_threshold.
        Regulated = regulation factor > self._ror_threshold.
        """
        data = model.get_data()
        upstream_inflow_exprs, upstream_reservoir_exprs = self._build_upstream_reservoir_and_inflow_exprs(data, upstream_topology)

        for area, member_modules in generator_module_groups.items():
            ror_name = area + "_hydro_RoR"
            reg_name = area + "_hydro_reservoir"

            ror_modules = []
            reservoir_modules = []

            for m_key in member_modules:
                if upstream_inflow_exprs[m_key] != 0:
                    upstream_inflow = get_level_value(
                        upstream_inflow_exprs[m_key],
                        db=model,
                        unit="Mm3/year",
                        data_dim=self._data_dim,
                        scen_dim=self._scen_dim,
                        is_max=False,
                    )
                else:
                    continue  # Skip generator modules with no upstream inflow
                if upstream_reservoir_exprs[m_key] != 0:
                    upstream_reservoir = get_level_value(
                        upstream_reservoir_exprs[m_key],
                        db=model,
                        unit="Mm3",
                        data_dim=self._data_dim,
                        scen_dim=self._scen_dim,
                        is_max=False,
                    )
                else:
                    upstream_reservoir = 0
                regulation_factor = upstream_reservoir / upstream_inflow if upstream_inflow > 0 else 0

                if regulation_factor <= self._ror_threshold:
                    ror_modules.append(m_key)
                else:
                    reservoir_modules.append(m_key)

            if len(ror_modules) > 0:  # only make run-of-river group if there are any modules
                self._grouped_modules[ror_name] = ror_modules

            if len(reservoir_modules) > 0:  # only make reservoir group if there are any modules
                self._grouped_modules[reg_name] = reservoir_modules

            if len(reservoir_module_groups[area]) > 0 and len(reservoir_modules) > 0:  # add reservoirs to reg group
                self._grouped_reservoirs[reg_name] = reservoir_module_groups[area]
            elif len(reservoir_module_groups[area]) > 0:  # add reservoirs to ror group if no reg group
                self._grouped_reservoirs[ror_name] = reservoir_module_groups[area]
                message = f"{area} has no modules over ror_threshold ({self._ror_threshold}), so all reservoirs are put in RoR module."
                self.send_warning_event(message)

    def _ignore_production_capacity_modules(
        self,
        model: Model,
    ) -> list[str]:
        """
        Return list of module names to ignore production capacity for in aggregation, because of hydraulic coupled reservoirs.

        Ignore the lowest production capacity of modules that are under the same hydraulic coupled reservoirs.
        """
        ignore_production_capacity_modules = []
        data = model.get_data()
        module_names = [key for key, component in data.items() if isinstance(component, HydroModule)]

        for m in module_names:
            if data[m].get_hydraulic_coupling() != 0:
                under_hydraulic = [
                    (
                        mm,
                        get_level_value(
                            data[mm].get_generator().get_energy_eq().get_level() * data[mm].get_release_capacity().get_level(),
                            model,
                            "MW",
                            self._data_dim,
                            self._scen_dim,
                            is_max=False,
                        ),
                    )
                    for mm in module_names
                    if data[mm].get_release_to() == m
                ]
                assert len(under_hydraulic) > 1
                ignore_production_capacity_modules.append(min(under_hydraulic, key=lambda x: x[1])[0])

        return ignore_production_capacity_modules

    def _aggregate_groups(  # noqa: C901
        self,
        model: Model,
        upstream_topology: dict[str, list[str]],
        ignore_capacity: list[str],
    ) -> None:
        """Aggregate each group of modules into one HydroModule."""
        data = model.get_data()
        for new_id, module_names in self._grouped_modules.items():
            num_reservoirs = 0
            if new_id in self._grouped_reservoirs:
                num_reservoirs = len(self._grouped_reservoirs[new_id])
            self.send_info_event(f"{new_id} from {len(module_names)} generator modules and {num_reservoirs} reservoirs.")

            # Generator and production
            generator_module_names = [m for m in module_names if data[m].get_generator()]
            productions = [data[m].get_generator().get_production() for m in generator_module_names]
            sum_production = _aggregate_result_volumes(model, productions, "MW", self._data_dim, self._scen_dim, new_id, generator_module_names)

            generator = HydroGenerator(
                power_node=data[generator_module_names[0]].get_generator().get_power_node(),
                energy_eq=Conversion(level=ConstantTimeVector(1.0, "kWh/m3", is_max_level=True)),
                production=sum_production,
            )
            energy_eq = generator.get_energy_eq().get_level()

            # Release capacity
            release_capacity_levels = [
                data[gm].get_release_capacity().get_level() * data[gm].get_generator().get_energy_eq().get_level()
                for gm in generator_module_names
                if gm not in ignore_capacity
            ]
            release_capacity = MaxFlowVolume(level=sum(release_capacity_levels) / energy_eq)

            # Inflow level
            upstream_inflow_levels = defaultdict(list)
            for m in generator_module_names:
                for mm in upstream_topology[m]:
                    inflow = data[mm].get_inflow()
                    if inflow:
                        upstream_inflow_levels[m].append(inflow.get_level())
            inflow_level_energy = sum(
                sum(upstream_inflow_levels[m]) * data[m].get_generator().get_energy_eq().get_level()
                for m in generator_module_names
                if len(upstream_inflow_levels[m]) > 0
            )
            inflow_level = inflow_level_energy / energy_eq

            # Inflow profile
            one_profile = Expr(src=ConstantTimeVector(1.0, is_zero_one_profile=False), is_profile=True)
            inflow_profile_to_energyinflow = defaultdict(list)
            inflow_level_to_value = dict()
            for m in generator_module_names:
                m_energy_eq = data[m].get_generator().get_energy_eq().get_level()
                m_energy_eq_value = get_level_value(
                    m_energy_eq,
                    db=model,
                    unit="kWh/m3",
                    data_dim=self._data_dim,
                    scen_dim=self._scen_dim,
                    is_max=False,
                )
                for upstream_module in upstream_topology[m]:
                    inflow = data[upstream_module].get_inflow()
                    if inflow:
                        if inflow not in inflow_level_to_value:
                            inflow_level_to_value[inflow] = get_level_value(
                                inflow.get_level(),
                                db=model,
                                unit="m3/s",
                                data_dim=self._data_dim,
                                scen_dim=self._scen_dim,
                                is_max=False,
                            )
                        upstream_energy_inflow = inflow_level_to_value[inflow] * m_energy_eq_value
                        upstream_profile = inflow.get_profile() if inflow.get_profile() else one_profile
                        inflow_profile_to_energyinflow[upstream_profile].append(upstream_energy_inflow)

            profile_weights = [sum(energyinflows) for energyinflows in inflow_profile_to_energyinflow.values()]
            inflow_profile = _aggregate_weighted_expressions(list(inflow_profile_to_energyinflow.keys()), profile_weights)
            inflow = AvgFlowVolume(level=inflow_level, profile=inflow_profile)

            # Reservoir capacity and filling
            if new_id in self._grouped_reservoirs and len(self._grouped_reservoirs[new_id]) > 0:
                reservoir_levels = [
                    data[m].get_reservoir().get_capacity().get_level() * data[m].get_meta(self._metakey_energy_eq_downstream).get_value()
                    for m in self._grouped_reservoirs[new_id]
                ]
                reservoir_level = sum(reservoir_levels) / energy_eq
                reservoir_capacity = StockVolume(level=reservoir_level)

                fillings = [data[m].get_reservoir().get_volume() for m in self._grouped_reservoirs[new_id]]
                energy_eq_downstreams = [data[m].get_meta(self._metakey_energy_eq_downstream).get_value() for m in self._grouped_reservoirs[new_id]]
                sum_filling = self._aggregate_fillings(fillings, energy_eq_downstreams, energy_eq, model, "GWh", new_id, self._grouped_reservoirs[new_id])
                reservoir = HydroReservoir(capacity=reservoir_capacity, volume=sum_filling)
            else:
                reservoir = None

            new_hydro = HydroModule(
                generator=generator,
                reservoir=reservoir,
                inflow=inflow,
                release_capacity=release_capacity,
            )
            new_hydro.add_meta(key=self._metakey_energy_eq_downstream, value=LevelExprMeta(energy_eq))

            data[new_id] = new_hydro

    def _aggregate_fillings(
        self,
        fillings: list[StockVolume],
        energy_eq_downstreams: list[Expr],
        energy_eq: Expr,
        model: Model,
        weight_unit: str,
        group_id: str,
        members: list[str],
    ) -> StockVolume | None:
        """Aggregate reservoir fillings if all fillings are not None."""
        sum_filling = None
        if all(filling.get_level() for filling in fillings):
            level, profiles, weights = self._get_level_profiles_weights_fillings(model, fillings, energy_eq_downstreams, energy_eq, weight_unit)
            profile = _aggregate_weighted_expressions(profiles, weights)
            sum_filling = StockVolume(level=level, profile=profile)
        elif any(filling.get_level() for filling in fillings):
            missing = [member for member, filling in zip(members, fillings, strict=False) if not filling.get_level()]
            message = (
                "Some but not all grouped modules have reservoir filling defined, reservoir filling not aggregated. "
                f"Group: {group_id}, missing filling for {missing}."
            )
            self.send_warning_event(message)
        return sum_filling

    def _get_level_profiles_weights_fillings(
        self,
        model: Model,
        fillings: list[StockVolume],
        energy_eq_downstreams: list[Expr],
        energy_eq: Expr,
        weight_unit: str,
    ) -> tuple[Expr, list[Expr], list[float]]:
        """
        Get aggregated filling level, and profiles with weights from list of fillings.

        Two cases:
        1) All fillings are expressions from previous disaggregation. Can be aggregated more efficiently.
        2) Default case, where we weight fillings based on energy equivalent inflow.
        """
        levels = [filling.get_level() for filling in fillings]
        if all(self._is_disagg_filling_expr(level) for level in levels):
            return _get_level_profile_weights_from_disagg_levelprofiles(model, fillings, self._data_dim, self._scen_dim)
        levels_energy = [filling * ee for filling, ee in zip(levels, energy_eq_downstreams, strict=True)]
        level = sum(levels_energy) / energy_eq
        profiles = [filling.get_profile() for filling in fillings]
        weights = [get_level_value(level_energy, model, weight_unit, self._data_dim, self._scen_dim, False) for level_energy in levels_energy]
        return level, profiles, weights

    def _is_disagg_filling_expr(self, expr: Expr) -> bool:
        """Check if expr is ((weight * agg_level * energy_eq_downstream) / energy_eq_agg) which indicates it comes from disaggregation."""
        if expr.is_leaf():
            return False
        ops, args = expr.get_operations(expect_ops=True, copy_list=False)
        if not (
            ops == "**/"
            and len(args) == 4  # noqa E501
            and all([args[0].is_leaf(), args[3].is_leaf()])
            and not args[0].is_level()
            and not args[0].is_flow()
            and not args[0].is_stock()
            and args[1].is_stock()
            and args[2].is_level()
            and not args[2].is_flow()
            and not args[2].is_stock()
            and args[3].is_level()
            and not args[3].is_flow()
            and not args[3].is_stock()
        ):
            return False
        return args[2].is_leaf() or args[2].get_operations(expect_ops=True, copy_list=False)[0] == "+"

    def _disaggregate(  # noqa: C901
        self,
        model: Model,
        original_data: dict[str, Component | TimeVector | Curve | Expr],
    ) -> None:
        """Disaggregate HydroAggregator."""
        new_data = model.get_data()

        deleted_group_names = self._get_deleted_group_modules(new_data)  # find agg groups that have been deleted
        agg_modules = {key: new_data.pop(key) for key in self._grouped_modules if key not in deleted_group_names}  # isolate agg modules out of new_data

        # Reinstate original detailed modules that are not fully deleted
        for detailed_key, agg_keys in self._aggregation_map.items():
            if agg_keys and all(key in deleted_group_names for key in agg_keys):
                continue
            new_data[detailed_key] = original_data[detailed_key]

        # Set production results in detailed modules
        for agg_key, detailed_keys in self._grouped_modules.items():
            if agg_key in deleted_group_names:
                continue

            agg_production_level = agg_modules[agg_key].get_generator().get_production().get_level()
            if agg_production_level is None:  # keep original production if agg has no production defined
                continue
            if len(detailed_keys) == 1:  # only one detailed module, set production directly
                new_data[detailed_key].get_generator().get_production().set_level(agg_production_level)
                continue
            detailed_production_levels = [new_data[detailed_key].get_generator().get_production().get_level() for detailed_key in detailed_keys]
            if any(detailed_production_levels) and not all(
                detailed_production_levels,
            ):  # if some but not all detailed modules have production defined, skip setting productio
                missing = [detailed_key for detailed_key, level in zip(detailed_keys, detailed_production_levels, strict=False) if not level]
                message = f"Some but not all grouped modules have production defined. Production not disaggregated for {agg_key}, missing for {missing}."
                self.send_warning_event(message)
                continue
            if _all_detailed_exprs_in_sum_expr(agg_production_level, detailed_production_levels):  # if agg production is sum of detailed levels,  keep original
                continue
            production_weights = self._get_disaggregation_production_weights(model, detailed_keys)  # default method
            for detailed_key in detailed_keys:
                self._set_weighted_production(new_data[detailed_key], agg_modules[agg_key], production_weights[detailed_key])

        # Set filling results in detailed modules
        for agg_key, detailed_keys in self._grouped_reservoirs.items():
            if agg_key in deleted_group_names:
                continue

            agg_filling_level = agg_modules[agg_key].get_reservoir().get_volume().get_level()
            if agg_filling_level is None:  # keep original filling if agg has no filling defined
                continue
            if len(detailed_keys) == 1:  # only one detailed module, set filling directly
                new_data[detailed_key].get_reservoir().get_volume().set_level(agg_filling_level)
                continue
            detailed_filling_levels = [new_data[detailed_key].get_reservoir().get_volume().get_level() for detailed_key in detailed_keys]
            if any(detailed_filling_levels) and not all(
                detailed_filling_levels,
            ):  # if some but not all detailed modules have filling defined, skip setting filling
                missing = [detailed_key for detailed_key, level in zip(detailed_keys, detailed_filling_levels, strict=False) if not level]
                message = f"Some but not all grouped modules have filling defined. Filling not disaggregated for {agg_key}, missing for {missing}."
                self.send_warning_event(message)
                continue
            detailed_energy_eq_downstreams = [new_data[detailed_key].get_meta(self._metakey_energy_eq_downstream).get_value() for detailed_key in detailed_keys]
            agg_energy_eq_downstream = agg_modules[agg_key].get_meta(self._metakey_energy_eq_downstream).get_value()
            agg_detailed_fillings = [
                detailed_filling * detailed_energy_eq
                for detailed_filling, detailed_energy_eq in zip(detailed_filling_levels, detailed_energy_eq_downstreams, strict=True)
                if detailed_filling and detailed_energy_eq
            ]
            if self._is_sum_filling_expr(
                agg_filling_level,
                agg_detailed_fillings,
                agg_energy_eq_downstream,
            ):  # if agg filling is sum of detailed levels, keep original
                continue
            reservoir_weights = self._get_disaggregation_filling_weights(model, detailed_keys)  # default method
            for detailed_key in detailed_keys:
                self._set_weighted_filling(new_data[detailed_key], agg_modules[agg_key], reservoir_weights[detailed_key])

        self._grouped_modules.clear()
        self._grouped_reservoirs.clear()

    def _get_deleted_group_modules(self, new_data: dict[str, Component | TimeVector | Curve | Expr]) -> set[str]:
        deleted_group_names: set[str] = set()

        for group_name in self._grouped_modules:
            if group_name not in new_data:
                deleted_group_names.add(group_name)
                continue

        return deleted_group_names

    def _get_disaggregation_production_weights(
        self,
        model: Model,
        detailed_keys: list[str],
    ) -> dict[str, float]:
        """Get weights to disaggregate production based on production capacity."""
        # Calculate production capacity for each detailed module
        data = model.get_data()
        production_weights = dict()  # detailed_key -> production_weight
        production_weight_factors = dict()  # detailed_key -> production_weight_factor
        for det in detailed_keys:
            det_module = data[det]
            release_capacity_level = det_module.get_release_capacity().get_level()
            generator_energy_eq = det_module.get_generator().get_energy_eq().get_level()
            production_weight = get_level_value(
                release_capacity_level * generator_energy_eq,
                db=model,
                unit="kW",
                data_dim=self._data_dim,
                scen_dim=self._scen_dim,
                is_max=False,
            )
            production_weights[det] = production_weight

        # Calculate production weight for each detailed module
        for det in detailed_keys:
            production_weight_factors[det] = production_weights[det] / sum(production_weights.values())

        return production_weight_factors

    def _get_disaggregation_filling_weights(
        self,
        model: Model,
        detailed_keys: list[str],
    ) -> dict[str, float]:
        """Get weights to disaggregate filling based on reservoir capacity."""
        # Calculate reservoir capacity for each detailed module
        data = model.get_data()
        filling_weights = dict()  # detailed_key -> reservoir_weight
        filling_weight_factors = dict()  # detailed_key -> reservoir_weight_factor
        for det in detailed_keys:
            det_module = data[det]
            reservoir_capacity_level = det_module.get_reservoir().get_capacity().get_level()
            reservoir_energy_eq = det_module.get_meta(self._metakey_energy_eq_downstream).get_value()
            reservoir_weight = get_level_value(
                reservoir_capacity_level * reservoir_energy_eq,
                db=model,
                unit="GWh",
                data_dim=self._data_dim,
                scen_dim=self._scen_dim,
                is_max=False,
            )
            filling_weights[det] = reservoir_weight

        # Calculate reservoir weight for each detailed module
        for det in detailed_keys:
            filling_weight_factors[det] = filling_weights[det] / sum(filling_weights.values())

        return filling_weight_factors

    def _set_weighted_production(self, detailed_module: HydroModule, agg_module: HydroModule, production_weight: float) -> None:
        """Set production level and profile for detailed module based on aggregated module."""
        agg_production_level = agg_module.get_generator().get_production().get_level()
        agg_production_profile = agg_module.get_generator().get_production().get_profile()
        production_level = production_weight * agg_production_level
        detailed_module.get_generator().get_production().set_level(production_level)
        detailed_module.get_generator().get_production().set_profile(agg_production_profile)

    def _is_sum_filling_expr(self, agg_filling: Expr, agg_detailed_fillings: list[Expr], agg_energy_eq_downstream: Expr) -> bool:
        """Check if expr is (sum(filling * energy_eq_downstream)) / agg_energy_eq_downstream, indicating it comes from aggregation."""
        if agg_filling.is_leaf():
            return False
        ops, args = agg_filling.get_operations(expect_ops=True, copy_list=False)
        if not (ops == "/" and len(args) == 2) and args[1] == agg_energy_eq_downstream:  # noqa E501
            return False
        ops_sum, args_sum = args[0].get_operations(expect_ops=True, copy_list=False)
        if "+" not in ops_sum:
            return False
        if len(args_sum) != len(agg_detailed_fillings):
            return False
        return all(arg in agg_detailed_fillings for arg in args_sum)

    def _set_weighted_filling(self, detailed_module: HydroModule, agg_module: HydroModule, filling_weight: float) -> None:
        """Set filling level and profile for detailed module based on aggregated module."""
        agg_filling_level = agg_module.get_reservoir().get_volume().get_level()
        agg_filling_profile = agg_module.get_reservoir().get_volume().get_profile()
        if agg_filling_level:  # keep original filling if agg has no filling defined
            agg_energy_eq = agg_module.get_meta(self._metakey_energy_eq_downstream).get_value()
            detailed_energy_eq = detailed_module.get_meta(self._metakey_energy_eq_downstream).get_value()

            filling_level = (filling_weight * agg_filling_level * agg_energy_eq) / detailed_energy_eq
            detailed_module.get_reservoir().get_volume().set_level(filling_level)
            detailed_module.get_reservoir().get_volume().set_profile(agg_filling_profile)
