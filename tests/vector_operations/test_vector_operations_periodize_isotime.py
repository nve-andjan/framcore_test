from datetime import date

import numpy as np
import pytest

from framcore.expressions._time_vector_operations import periodize_isotime

DEFAULT_START_YEAR = 2020
DEFAULT_START_DATE = date.fromisocalendar(DEFAULT_START_YEAR, 1, 1)
DEFAULT_END_DATE = date.fromisocalendar(2030, 1, 1)
HOURS_PER_WEEK = 168
MINUTES_PER_WEEK = 10080
WEEKS = np.array([53, 52, 52, 52, 52, 52, 53, 52, 52, 52])  # Number of weeks in each year from 2020 to 2029

@pytest.fixture
def ten_years_annual_data():
    return np.arange(1, 11, dtype=np.float32)

@pytest.fixture
def ten_years_monthly_data():
    return np.arange(1, 10 * 12 + 1, dtype=np.float32)

@pytest.fixture
def ten_years_weekly_data():
    weeks_between = (DEFAULT_END_DATE - DEFAULT_START_DATE).days // 7
    return np.arange(1, weeks_between + 1, dtype=np.float32)

@pytest.fixture
def ten_years_daily_data():
    days_between = (DEFAULT_END_DATE - DEFAULT_START_DATE).days
    return np.arange(1, days_between + 1, dtype=np.float32)

@pytest.fixture
def ten_years_hourly_data():
    hours_between = (DEFAULT_END_DATE - DEFAULT_START_DATE).days * 24
    return np.arange(1, hours_between + 1, dtype=np.float32)

@pytest.fixture
def ten_years_minutely_data():
    minutes_between = (DEFAULT_END_DATE - DEFAULT_START_DATE).days * 24 * 60
    return np.arange(1, minutes_between + 1, dtype=np.float32)

@pytest.mark.parametrize("output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx", [
    (2020, 1, 1, 0, 1),
    (2020, 2, 2, 0, 2),
    (2021, 1, 1, 1, 2),
    (2029, 1, 1, 9, 10),
])
def test_periodize_isotime_annual_data(ten_years_annual_data, output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx):
    input_number_of_years = 10

    result_vector = periodize_isotime(ten_years_annual_data, DEFAULT_START_YEAR, input_number_of_years, output_start_year, output_num_years)

    assert result_vector.size == expected_ouput_vector_size
    assert np.array_equal(result_vector, ten_years_annual_data[start_indx:end_idx])

@pytest.mark.parametrize("output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx", [
    (2020, 1, 12, 0, 12),
    (2020, 2, 24, 0, 24),
    (2021, 1, 12, 12, 24),
    (2029, 1, 12, 108, 120),
])
def test_periodize_isotime_monthly_data(ten_years_monthly_data, output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx):
    input_number_of_years = 10

    result_vector = periodize_isotime(ten_years_monthly_data, DEFAULT_START_YEAR, input_number_of_years, output_start_year, output_num_years)

    assert result_vector.size == expected_ouput_vector_size
    assert np.array_equal(result_vector, ten_years_monthly_data[start_indx:end_idx])

@pytest.mark.parametrize("output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx", [
    (2020, 1, 53, 0, 53),
    (2020, 2, WEEKS[:2].sum(), 0, WEEKS[:2].sum()),
    (2021, 1, 52, 53, WEEKS[:2].sum()),
    (2029, 1, 52, WEEKS[:9].sum(), WEEKS.sum()),
])
def test_periodize_isotime_weekly_data(ten_years_weekly_data, output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx):
    input_number_of_years = 10

    result_vector = periodize_isotime(ten_years_weekly_data, DEFAULT_START_YEAR, input_number_of_years, output_start_year, output_num_years)

    assert result_vector.size == expected_ouput_vector_size
    assert np.array_equal(result_vector, ten_years_weekly_data[start_indx:end_idx])

@pytest.mark.parametrize("output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx", [
    (2020, 1, 53 * 7, 0, 53 * 7), # 53 weeks in a year, 7 days per week
    (2020, 7, WEEKS[:7].sum() * 7, 0, WEEKS[:7].sum() * 7), # # 7 years of data, 2020 and 2026 are 53 weeks years
    (2029, 1, 52 * 7, WEEKS[:9].sum() * 7, WEEKS.sum() * 7),
])
def test_periodize_isotime_daily_data(ten_years_daily_data, output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx):
    input_number_of_years = 10

    result_vector = periodize_isotime(ten_years_daily_data, DEFAULT_START_YEAR, input_number_of_years, output_start_year, output_num_years)

    assert result_vector.size == expected_ouput_vector_size
    assert np.array_equal(result_vector, ten_years_daily_data[start_indx:end_idx])

@pytest.mark.parametrize("output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx", [
    (2020, 1, 53 * HOURS_PER_WEEK, 0, 53 * HOURS_PER_WEEK), # 53 weeks in a year
    (2020, 7, WEEKS[:7].sum() * HOURS_PER_WEEK, 0, WEEKS[:7].sum() * HOURS_PER_WEEK), # # 7 years of data, 2020 and 2026 are 53 weeks years
    (2026, 4, WEEKS[6:10].sum() * HOURS_PER_WEEK, WEEKS[:6].sum() * HOURS_PER_WEEK, WEEKS.sum() * HOURS_PER_WEEK),
])
def test_periodize_isotime_hourly_data(ten_years_hourly_data, output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx):
    input_number_of_years = 10

    result_vector = periodize_isotime(ten_years_hourly_data, DEFAULT_START_YEAR, input_number_of_years, output_start_year, output_num_years)

    assert result_vector.size == expected_ouput_vector_size
    assert np.array_equal(result_vector, ten_years_hourly_data[start_indx:end_idx])

@pytest.mark.parametrize("output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx", [
    (2020, 1, 53 * MINUTES_PER_WEEK, 0, 53 * MINUTES_PER_WEEK), # 53 weeks in a year
    (2020, 7, WEEKS[:7].sum() * MINUTES_PER_WEEK, 0, WEEKS[:7].sum() * MINUTES_PER_WEEK), # 7 years of data, 2020 and 2026 are 53 weeks years
    (2026, 4, WEEKS[6:10].sum() * MINUTES_PER_WEEK, WEEKS[:6].sum() * MINUTES_PER_WEEK, WEEKS.sum() * MINUTES_PER_WEEK),
])
def test_periodize_isotime_minutely_data(ten_years_minutely_data, output_start_year, output_num_years, expected_ouput_vector_size, start_indx, end_idx):
    input_number_of_years = 10

    result_vector = periodize_isotime(ten_years_minutely_data, DEFAULT_START_YEAR, input_number_of_years, output_start_year, output_num_years)

    assert result_vector.size == expected_ouput_vector_size
    assert np.array_equal(result_vector, ten_years_minutely_data[start_indx:end_idx])

def test_when_input_vector_is_not_vector_should_raise_exception(ten_years_annual_data):
    input_number_of_years = 10
    output_num_years = 1

    with pytest.raises(AssertionError):
        periodize_isotime(np.array([[1, 2], [3, 4]]), DEFAULT_START_YEAR, input_number_of_years, DEFAULT_START_YEAR, output_num_years)

def test_when_input_start_year_is_greater_than_output_start_year_should_raise_exception(ten_years_annual_data):
    input_number_of_years = 10
    output_num_years = 1

    with pytest.raises(AssertionError):
        periodize_isotime(ten_years_annual_data, DEFAULT_START_YEAR, input_number_of_years, DEFAULT_START_YEAR - 1, output_num_years)

def test_when_input_num_years_is_greater_than_input_vector_size_should_raise_exception(ten_years_annual_data):
    output_num_years = 1

    with pytest.raises(AssertionError):
        periodize_isotime(ten_years_annual_data, DEFAULT_START_YEAR, ten_years_annual_data.size + 1, DEFAULT_START_YEAR, output_num_years)

def test_when_output_num_years_is_greater_than_input_vector_size_should_raise_exception(ten_years_annual_data):
    input_number_of_years = 10

    with pytest.raises(AssertionError):
        periodize_isotime(ten_years_annual_data, DEFAULT_START_YEAR, input_number_of_years, DEFAULT_START_YEAR, ten_years_annual_data.size + 1)

def test_when_input_vector_size_is_not_multiple_of_input_num_years_should_raise_exception(ten_years_annual_data):
    input_vector = ten_years_annual_data[:-1]
    input_number_of_years = 10
    output_num_years = 1

    with pytest.raises(AssertionError):
        periodize_isotime(input_vector, DEFAULT_START_YEAR, input_number_of_years, DEFAULT_START_YEAR, output_num_years)