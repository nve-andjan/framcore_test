import numpy as np
import pytest

from framcore.expressions._time_vector_operations import periodize_modeltime

DEFAULT_INPUT_START_YEAR: int = 2000
DEFAULT_OUTPUT_START_YEAR: int = 2000
DEFAULT_INPUT_NUM_OF_YEARS: int = 10


@pytest.fixture
def ten_years_weekly_data():
    return np.arange(1, 10 * 52 + 1, dtype=np.float32)

@pytest.mark.parametrize("input_start_year, output_start_year, output_num_of_years", [
    (DEFAULT_INPUT_START_YEAR, 2000, 1), 
    (DEFAULT_INPUT_START_YEAR, 2002, 5),
    (DEFAULT_INPUT_START_YEAR, 2009, 1),
    (DEFAULT_INPUT_START_YEAR, DEFAULT_INPUT_START_YEAR, 10),
])
def test_given_ten_years_data_should_take_3_years_data(ten_years_weekly_data, input_start_year, output_start_year, output_num_of_years):
    input_num_of_years = 10

    result = periodize_modeltime(ten_years_weekly_data, input_start_year, input_num_of_years, output_start_year, output_num_of_years)

    assert result.size == output_num_of_years * 52
    assert result[0] == ten_years_weekly_data[52 * (output_start_year - input_start_year)]

@pytest.mark.parametrize("output_start_year, output_num_of_years", [
    (2010, 1),
    (2009, 2),
    (2001, 10),
])
def test_when_taking_out_of_bounds_data_should_raise_exception(ten_years_weekly_data, output_start_year, output_num_of_years):
    input_num_of_years = 10

    with pytest.raises(AssertionError):
        periodize_modeltime(ten_years_weekly_data, DEFAULT_INPUT_START_YEAR, input_num_of_years, output_start_year, output_num_of_years)

def test_when_output_start_year_is_less_than_input_start_year_should_raise_exception(ten_years_weekly_data):
    input_num_of_years = 10
    output_num_of_years = 1

    with pytest.raises(AssertionError):
        periodize_modeltime(ten_years_weekly_data, DEFAULT_INPUT_START_YEAR, input_num_of_years, DEFAULT_INPUT_START_YEAR - 1, output_num_of_years)

def test_when_input_vector_is_not_vector_should_raise_exception(ten_years_weekly_data):
    input_num_of_years = 10
    output_num_of_years = 1

    with pytest.raises(AssertionError):
        periodize_modeltime(np.array([[1, 2], [3, 4]]), DEFAULT_INPUT_START_YEAR, input_num_of_years, DEFAULT_OUTPUT_START_YEAR, output_num_of_years)

def test_when_input_num_years_is_less_than_input_vector_size_should_raise_exception(ten_years_weekly_data):
    output_num_of_years = 1

    with pytest.raises(AssertionError):
        periodize_modeltime(ten_years_weekly_data, DEFAULT_INPUT_START_YEAR, ten_years_weekly_data.size - 1, DEFAULT_OUTPUT_START_YEAR, output_num_of_years)

def test_when_input_num_years_is_not_multiple_of_input_vector_size_should_raise_exception(ten_years_weekly_data):
    output_num_of_years = 1

    with pytest.raises(AssertionError):
        periodize_modeltime(ten_years_weekly_data, DEFAULT_INPUT_START_YEAR, ten_years_weekly_data.size + 1, DEFAULT_OUTPUT_START_YEAR, output_num_of_years)

def test_when_output_num_years_is_greater_than_input_num_years_should_raise_exception(ten_years_weekly_data):
    input_num_of_years = 10

    with pytest.raises(AssertionError):
        periodize_modeltime(ten_years_weekly_data, DEFAULT_INPUT_START_YEAR, input_num_of_years, DEFAULT_OUTPUT_START_YEAR, input_num_of_years + 1)