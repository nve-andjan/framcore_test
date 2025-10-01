from datetime import timedelta

from framcore import Model
from framcore.expressions import Expr, get_level_value, get_profile_vector
from framcore.querydbs import ModelDB
from framcore.timeindexes import ModelYear, ProfileTimeIndex
from framcore.timevectors import ConstantTimeVector


def _setup() -> Model:
    model = Model()

    profile_tv = ConstantTimeVector(0.5, unit=None, is_max_level=None, is_zero_one_profile=True, reference_period=None)
    model.add("profile_tv", profile_tv)

    profile_expr = Expr(src="profile_tv", is_profile=True)
    model.add("profile_expr", profile_expr)

    level_tv = ConstantTimeVector(200.0, unit="MW", is_max_level=True, is_zero_one_profile=None, reference_period=None)
    model.add("level_tv", level_tv)

    level_expr = Expr(src="level_tv", is_level=True, profile=profile_expr)
    model.add("level_expr", level_expr)

    return model, level_expr, profile_expr

def test_get_level_value():
    model, level_expr, _ = _setup()
    query_db = ModelDB(model)

    level_value = get_level_value(
        level_expr,
        db=query_db,
        unit="MW",
        data_dim=ModelYear(2025),
        scen_dim=ProfileTimeIndex(1981, 10, timedelta(days=1), is_52_week_years=True),
        is_max=True,
    )

    assert level_value == 200.0, f"Expected 200.0, got {level_value}"

def test_get_profile_vector():
    model, _, profile_expr = _setup()
    query_db = ModelDB(model)

    profile_vector = get_profile_vector(
        profile_expr,
        query_db,
        data_dim=ModelYear(2025),
        scen_dim=ProfileTimeIndex(1981, 10, timedelta(days=1), is_52_week_years=True),
        is_zero_one=True,
    )

    assert all(value == 0.5 for value in profile_vector), "All values in the profile vector should be 0.5"
