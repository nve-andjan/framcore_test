import copy

import pandas as pd
import pytest

from framcore.timeindexes import ListTimeIndex


def default_datetime_list():
    return pd.date_range(start="2023-01-01", periods=3, freq="D")

@pytest.fixture
def default_index():
    return ListTimeIndex(
        datetime_list=default_datetime_list(),
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )


def test_same_list_time_indexes_should_have_same_fingerprint(default_index):
    index1 = copy.deepcopy(default_index)
    index2 = copy.deepcopy(default_index)

    assert index1.get_fingerprint().get_hash() == index2.get_fingerprint().get_hash()


@pytest.mark.parametrize(
    "target_index", [
        ListTimeIndex(datetime_list=pd.date_range(start="2024-01-01", periods=3, freq="D"), is_52_week_years=False, extrapolate_first_point=False, extrapolate_last_point=False),
        ListTimeIndex(datetime_list=default_datetime_list(), is_52_week_years=True, extrapolate_first_point=False, extrapolate_last_point=False),
        ListTimeIndex(datetime_list=default_datetime_list(), is_52_week_years=False, extrapolate_first_point=True, extrapolate_last_point=False),
        ListTimeIndex(datetime_list=default_datetime_list(), is_52_week_years=False, extrapolate_first_point=False, extrapolate_last_point=True),
    ]
)
def test_litst_time_indexes_with_different_field_values_should_have_different_fingerprints(default_index, target_index):
    assert default_index.get_fingerprint().get_hash() != target_index.get_fingerprint().get_hash()
