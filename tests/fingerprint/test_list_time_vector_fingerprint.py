import copy

import numpy as np
import pandas as pd
import pytest

from framcore.timeindexes import ListTimeIndex
from framcore.timevectors import ListTimeVector


def test_same_list_time_vectors_should_have_same_fingerprint(default_vector):
    ltv1 = copy.deepcopy(default_vector)
    ltv2 = copy.deepcopy(default_vector)

    assert ltv1.get_fingerprint().get_hash() == ltv2.get_fingerprint().get_hash()

def default_index():
    return ListTimeIndex(
        datetime_list=pd.date_range(start="2023-01-01", periods=3, freq="D"),
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )

def other_index():
    return ListTimeIndex(
        datetime_list=pd.date_range(start="2024-01-01", periods=3, freq="D"),
        is_52_week_years=False,
        extrapolate_first_point=False,
        extrapolate_last_point=False,
    )


def default_vector_values():
    return np.array([1000, 1000, 1000])


@pytest.fixture
def default_vector():
    return ListTimeVector(timeindex=default_index(), vector=default_vector_values(), unit="MW", is_max_level=False, is_zero_one_profile=None)


@pytest.mark.parametrize(
    "test_vector",
    [
        ListTimeVector(timeindex=other_index(), vector=default_vector_values(), unit="MW", is_max_level=False, is_zero_one_profile=None),
        ListTimeVector(timeindex=default_index(), vector=np.array([10, 10, 10]), unit="MW", is_max_level=False, is_zero_one_profile=None),
        ListTimeVector(timeindex=default_index(), vector=default_vector_values(), unit="GW", is_max_level=False, is_zero_one_profile=None),
        ListTimeVector(timeindex=default_index(), vector=default_vector_values(), unit="MW", is_max_level=None, is_zero_one_profile=True),
    ],
)
def test_list_time_vector_with_different_field_values_should_have_different_fingerprint(default_vector, test_vector):
    assert default_vector.get_fingerprint().get_hash() != test_vector.get_fingerprint().get_hash()
