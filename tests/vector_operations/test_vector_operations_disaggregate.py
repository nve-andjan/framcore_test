import numpy as np
import pytest

from framcore.expressions._time_vector_operations import disaggregate


@pytest.fixture
def default_input():
    return np.ones(52, dtype=np.float32)

@pytest.fixture
def default_output():
    return np.zeros(52*168, dtype=np.float32)

def test_when_disaggfunc_repeat_should_repeat_input_vector_values_in_output_vector_multiplier_times():
    in_x = np.array([2, 3, 4], dtype=np.float32)
    out_x = np.zeros(9, dtype=np.float32)
    
    disaggregate(in_x, out_x, is_disaggfunc_repeat=True)

    assert np.size(out_x) == 9
    assert np.array_equal(out_x, np.array([2, 2, 2, 3, 3, 3, 4, 4, 4], dtype=np.float32))

def test_when_disaggfunc_not_repeat_should_calculate_average_for_each_multiplier_elements_in_output_vector():
    in_x = np.array([2, 3, 4], dtype=np.float32)
    out_x = np.zeros(9, dtype=np.float32)

    disaggregate(in_x, out_x, is_disaggfunc_repeat=False)

    assert np.size(out_x) == 9
    assert np.array_equal(out_x, np.array([2/3, 2/3, 2/3, 3/3, 3/3, 3/3, 4/3, 4/3, 4/3], dtype=np.float32))

def test_when_input_array_is_not_vector_raise_exception(default_output):
    in_x = np.ones((2, 52), dtype=np.float32)
    out_x = default_output

    try:
        disaggregate(in_x, out_x, is_disaggfunc_repeat=True)
    except AssertionError:
        assert True
    else:
        assert False, "Expected AssertionError not raised."

def test_when_output_array_is_not_vector_raise_exception(default_input):
    in_x = default_input
    out_x = np.zeros((2, 52*168), dtype=np.float32)

    try:
        disaggregate(in_x, out_x, is_disaggfunc_repeat=True)
    except AssertionError:
        assert True
    else:
        assert False, "Expected AssertionError not raised."

def test_when_input_vector_size_is_greater_than_output_vector_size_raise_exception(default_output):
    in_x = np.ones(53*168, dtype=np.float32)
    out_x = default_output

    try:
        disaggregate(in_x, out_x, is_disaggfunc_repeat=True)
    except AssertionError:
        assert True
    else:
        assert False, "Expected AssertionError not raised."

def test_when_input_vector_size_is_not_multiplier_of_output_vector_size_raise_exception(default_output):
    in_x = np.ones(51, dtype=np.float32)
    out_x = default_output

    try:
        disaggregate(in_x, out_x, is_disaggfunc_repeat=True)
    except AssertionError:
        assert True
    else:
        assert False, "Expected AssertionError not raised."

def test_when_vector_types_are_different_raise_exception(default_output):
    in_x = np.ones(52, dtype=np.int32)
    out_x = default_output

    try:
        disaggregate(in_x, out_x, is_disaggfunc_repeat=True)
    except AssertionError:
        assert True
    else:
        assert False, "Expected AssertionError not raised."