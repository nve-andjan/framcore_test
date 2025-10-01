from unittest.mock import MagicMock, Mock

import numpy as np

from framcore.timevectors import LoadedTimeVector


def test_get_vector():
    class TestLoadedTimeVector(LoadedTimeVector):
        def __init__(self, vector_id, loader):
            self._vector_id = vector_id
            self._loader = loader

    expected = np.array([1, 2], dtype=np.float64)
    mocked_loader = MagicMock()
    mocked_loader_get_values = Mock(return_value=expected)
    mocked_loader.get_values = mocked_loader_get_values

    test_id = "test_id"
    test_tv = TestLoadedTimeVector(test_id, mocked_loader)

    result = test_tv.get_vector(is_float32=False)
    assert np.all(result == expected)
    mocked_loader_get_values.assert_called_once_with(test_id)


def test_get_time_index():
    class TestLoadedTimeVector(LoadedTimeVector):
        def __init__(self, vector_id, loader):
            self._vector_id = vector_id
            self._loader = loader

    expected = "index"
    mocked_loader = MagicMock()
    mocked_loader_get_index = Mock(return_value=expected)
    mocked_loader.get_index = mocked_loader_get_index

    test_id = "test_id"
    test_tv = TestLoadedTimeVector(test_id, mocked_loader)

    result = test_tv.get_timeindex()
    assert result == expected
    mocked_loader_get_index.assert_called_once()


def test_is_constant():
    class TestLoadedTimeVector(LoadedTimeVector):
        def __init__(self):
            pass

    test_tv = TestLoadedTimeVector()
    assert not test_tv.is_constant()
