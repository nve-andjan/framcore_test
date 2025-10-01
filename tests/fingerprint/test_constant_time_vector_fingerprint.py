import copy

import pytest

from framcore.timevectors import ConstantTimeVector, ReferencePeriod


@pytest.fixture
def default_time_vector():
    return ConstantTimeVector(
        scalar=100.0,
        unit="MW",
        is_max_level=True,
        is_zero_one_profile=None,
        reference_period=None,
    )


def test_same_constant_time_vectors_should_have_same_fingerprint(default_time_vector: ConstantTimeVector):
    tv1 = copy.deepcopy(default_time_vector)
    tv2 = copy.deepcopy(default_time_vector)

    assert tv1.get_fingerprint().get_hash() == tv2.get_fingerprint().get_hash()


@pytest.mark.parametrize(
    "target_vector",
    [
        ConstantTimeVector(scalar=200.0, unit="MW", is_max_level=True, is_zero_one_profile=None, reference_period=None),
        ConstantTimeVector(scalar=100.0, unit="GW", is_max_level=True, is_zero_one_profile=None, reference_period=None),
        ConstantTimeVector(scalar=100.0, unit="MW", is_max_level=None, is_zero_one_profile=True, reference_period=None),
        ConstantTimeVector(scalar=100.0, unit="MW", is_max_level=True, is_zero_one_profile=None, reference_period=ReferencePeriod(2020, 5)),
    ],
)
def test_time_vectors_with_different_field_values_should_have_different_fingerprints(
    default_time_vector: ConstantTimeVector, target_vector: ConstantTimeVector,
):
    assert default_time_vector.get_fingerprint().get_hash() != target_vector.get_fingerprint().get_hash()
