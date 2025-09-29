"""Utility functions for aggregation and disaggregation of model attributes."""

from math import isclose

from framcore.attributes import AvgFlowVolume, Cost, LevelProfile
from framcore.expressions import Expr, get_level_value
from framcore.Model import Model
from framcore.timeindexes import FixedFrequencyTimeIndex, SinglePeriodTimeIndex
from framcore.timevectors import ConstantTimeVector


# Aggregation util functions ---------------------------------------------------------------------
# Only for results
def _aggregate_result_volumes(
    model: Model,
    volumes: list[AvgFlowVolume],
    weight_unit: str,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
    group_id: str,
    grouped_ids: list[str],
) -> AvgFlowVolume | None:
    """Aggregate result volumes for grouped components. If some but not all grouped components have volume defined, send warning and return None."""
    sum_volume = None
    if all(volume.get_level() for volume in volumes):
        level, profiles, weights = _get_level_profile_weights_volumes_from_results(model, volumes, weight_unit, data_dim, scen_dim)
        profile = _aggregate_weighted_expressions(profiles, weights)
        sum_volume = AvgFlowVolume(level=level, profile=profile)
    elif any(volume.get_level() for volume in volumes):
        missing = [grouped_id for grouped_id, volume in zip(grouped_ids, volumes, strict=False) if not volume.get_level()]
        message = f"Some but not all grouped components have volume defined. Volume not aggregated for {group_id}, missing volume for {missing}."
        model.send_warning_event(message)
    return sum_volume


def _get_level_profile_weights_volumes_from_results(
    model: Model,
    volumes: list[AvgFlowVolume],
    weight_unit: str,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
) -> tuple[Expr, list[Expr], list[float]]:
    """
    Get aggregated level, and profiles with weights from list of volumes.

    Two cases:
    1. All volumes have previously been disaggregated (levels are weight * LevelExpr). Can be aggregated more efficiently.
    2. Default: sum levels and get weights from level values.
    """
    levels = [volume.get_level() for volume in volumes]
    if all(_is_weight_flow_expr(level) for level in levels):
        return _get_level_profile_weights_from_disagg_levelprofiles(model, volumes, data_dim, scen_dim)
    level = sum(levels)
    profiles = [volume.get_profile() for volume in volumes]
    weights = [get_level_value(level, model, weight_unit, data_dim, scen_dim, False) for level in levels]
    return level, profiles, weights


def _get_level_profile_weights_from_disagg_levelprofiles(
    model: Model,
    objs: list[LevelProfile],
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
) -> tuple[Expr, list[Expr], list[float]]:
    """
    Get aggregated level, and profiles with weights from disaggregated LevelProfiles with Level = weight * LevelExpr.

    Two cases:
    - If all sum weights are 1, return sum of levels and profiles with weights 1.
    - Otherwise, return weighted sum of levels, and profiles with weights from level expressions.
    """
    weights = _get_weights_from_levelprofiles(model, objs, data_dim, scen_dim)
    if all(isclose(weight, 1.0, rel_tol=1e-6) for weight in weights.values()):
        level = sum([obj[0] for obj in weights])  # all weights 1, return sum of objs
        profiles = [obj[1] for obj in weights]
        weights = [1.0 for _ in weights]
        return level, profiles, weights
    level = sum([weight * obj[0] for obj, weight in weights.items()])  # return weighted sum of objs
    profiles = [obj[1] for obj in weights]
    weights = [weight for weight in weights.values()]
    return level, profiles, weights


# Generic
def _aggregate_weighted_expressions(exprs: list[Expr], weights: list[float]) -> Expr:
    """Calculate weighted average of expressions with sum of weights = 1. If all profiles are identical, return that expr."""
    if any(e is None for e in exprs):
        message = f"Cannot aggregate profiles if some profiles are None: {exprs}."
        raise ValueError(message)
    if all(exprs[0] == e for e in exprs):
        return exprs[0]
    weights_dict = dict()
    for e, w in zip(exprs, weights, strict=True):
        if e not in weights_dict:
            weights_dict[e] = 0.0
        weights_dict[e] += w / sum(weights)
    return sum([w * e for e, w in weights_dict.items()])


def _is_weight_flow_expr(expr: Expr) -> bool:
    """Check if expr is weight * FlowExpr, which indicates it comes from disaggregation."""
    if expr.is_leaf():
        return False
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if ops != "*" or len(args) != 2 or not args[0].is_leaf():  # noqa E501
        return False
    if not (not args[0].is_level() and not args[0].is_profile()):
        return False
    return args[1].is_flow()


def _get_weights_from_levelprofiles(
    model: Model,
    objs: list[LevelProfile],
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
) -> dict[tuple[Expr, Expr], float]:
    """Get sum of weights for each unique (level, profile) pair from disaggregated LevelProfiles with Level = weight * LevelExpr."""
    weights = dict()
    for obj in objs:
        ops, args = obj.get_level().get_operations(expect_ops=True, copy_list=False)
        key = (args[1], obj.get_profile())
        if key not in weights:
            weights[key] = 0.0
        weights[key] += get_level_value(args[0], model, unit=None, data_dim=data_dim, scen_dim=scen_dim, is_max=False)

    for key in weights:  # noqa: PLC0206
        if isclose(weights[key], 1.0, rel_tol=1e-6):
            weights[key] = 1.0

    if any(weight > 1.0 for weight in weights.values()):
        message = f"Sum of weights are over 1 for some level/profile combinations: {weights}."
        raise ValueError(message)

    return weights


def _aggregate_costs(
    model: Model,
    costs: list[Cost],
    weights: list[float],
    weight_unit: str,
    data_dim: SinglePeriodTimeIndex,
    scen_dim: FixedFrequencyTimeIndex,
) -> tuple[Expr, Expr | None, Expr | None]:
    """Aggregate a list of costs with weights. Aggregated cost has weighted level, profile and intercept."""
    # Initialize default values
    aggregated_level = None
    aggregated_profile = None
    aggregated_intercept = None

    # Handle levels
    zero_level = Expr(ConstantTimeVector(0.0, is_max_level=False), is_level=True)
    cost_levels = [cost.get_level() if cost.get_level() else zero_level for cost in costs]
    aggregated_level = _aggregate_weighted_expressions(cost_levels, weights)

    # Handle profiles
    cost_profiles = [cost.get_profile() for cost in costs]
    if any(cost_profiles):
        one_profile = Expr(src=ConstantTimeVector(1.0, is_zero_one_profile=False), is_profile=True)
        cost_profiles = [profile if profile else one_profile for profile in cost_profiles]
        cost_level_values = [get_level_value(level, model, weight_unit, data_dim, scen_dim, False) for level in cost_levels]
        profile_weights = [clv * weight for clv, weight in zip(cost_level_values, weights, strict=True)]
        aggregated_profile = _aggregate_weighted_expressions(cost_profiles, profile_weights)

    # Handle intercepts
    cost_intercepts = [cost.get_intercept() for cost in costs]
    if any(cost_intercepts):
        one_profile = Expr(src=ConstantTimeVector(1.0, is_zero_one_profile=False), is_profile=True)
        cost_intercepts = [intercept if intercept else one_profile for intercept in cost_intercepts]
        aggregated_intercept = _aggregate_weighted_expressions(cost_intercepts, weights)

    return aggregated_level, aggregated_profile, aggregated_intercept


# Disaggregation util functions ---------------------------------------------------------------------
def _all_detailed_exprs_in_sum_expr(expr: Expr, detailed_exprs: list[Expr]) -> bool:
    """Check if expr is sum of detailed exprs. Does not handle the case where len(exprs) == 1."""
    if expr.is_leaf():
        return False
    ops, args = expr.get_operations(expect_ops=True, copy_list=False)
    if ops != "+" or len(args) != len(detailed_exprs):
        return False
    return all(arg in detailed_exprs for arg in args)
