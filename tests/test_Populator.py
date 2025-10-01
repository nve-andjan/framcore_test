import re
from pathlib import Path
from unittest.mock import patch

import pytest

from framcore import Model
from framcore.components import Component
from framcore.curves import Curve
from framcore.expressions import Expr
from framcore.populators import Populator
from framcore.timevectors import TimeVector


@pytest.fixture
def base_path() -> str:
    return "framcore.populators.Populator.Base"


def create_tmp_file(file_path: Path):
    with file_path.open("w") as f:
        f.write("")


def test_populate_require_unique_ids(tmp_path: Path, base_path: str) -> None:
    existing_source = tmp_path / Path("test1.txt")
    create_tmp_file(existing_source)
    existing_tv = "existing_tv1"
    test_existing_data = {
        "id1": existing_tv,
    }

    new_source = tmp_path / Path("test2.txt")
    create_tmp_file(new_source)
    new_tv = "new_tv1"
    new_tv2 = "new_tv2"
    test_new_data = {
        "id1": new_tv,
        "id2": new_tv2,
    }

    class TestPopulator(Populator):
        def _populate(self) -> dict[str, Component | TimeVector | Curve | Expr]:
            self._registered_ids = {
                "id1": [new_source],
                "id2": [new_source],
            }
            return test_new_data

    TestPopulator.__abstractmethods__ = False

    model = Model()
    model._data.update(test_existing_data)  # noqa: SLF001
    populator = TestPopulator()

    expected_error_message = f"Found 1 error:\nDuplicate ID found: 'id1' in sources {[new_source, model]}"

    with patch(base_path + ".send_error_event") as mock_send_error_event, pytest.raises(RuntimeError, match=re.escape(expected_error_message)):  # noqa: PT012
        populator.populate(model)
        assert mock_send_error_event.call_count == 1


def test_check_duplicate_ids_require_unique_ids():
    class TestPopulator(Populator):
        pass

    TestPopulator.__abstractmethods__ = False

    populator = TestPopulator()

    test_id = "id1"
    test_source = "id1_source"
    test_source_2 = "id1_source_2"

    populator._registered_ids = {test_id: [test_source, test_source]}
    result = populator._check_duplicate_ids()
    expected = {f"Duplicate ID found: '{test_id}' in sources {[test_source, test_source]}"}
    assert result == expected

    populator._registered_ids = {test_id: [test_source, test_source_2]}
    result = populator._check_duplicate_ids()
    expected = {f"Duplicate ID found: '{test_id}' in sources {[test_source, test_source_2]}"}
    assert result == expected


def test_register_id_not_previously_registered():
    class TestPopulator(Populator):
        pass

    TestPopulator.__abstractmethods__ = False

    populator = TestPopulator()

    test_id = "id1"
    test_source = "id1_source"
    populator._register_id(test_id, test_source)

    expected_result = {test_id: [test_source]}
    assert populator._registered_ids == expected_result


def test_register_id_previously_registered():
    class TestPopulator(Populator):
        pass

    TestPopulator.__abstractmethods__ = False

    populator = TestPopulator()

    test_id = "id1"
    test_source = "id1_source"
    test_source_2 = "id1_source_2"
    populator._registered_ids = {test_id: [test_source]}

    populator._register_id(test_id, test_source)
    expected_result = {test_id: [test_source, test_source]}
    assert populator._registered_ids == expected_result

    populator._register_id(test_id, test_source_2)
    expected_result = {test_id: [test_source, test_source, test_source_2]}
    assert populator._registered_ids == expected_result


def test_register_reference_not_previously_registered():
    class TestPopulator(Populator):
        pass

    TestPopulator.__abstractmethods__ = False

    populator = TestPopulator()

    test_id = "id1"
    test_refs = {"ref1", "ref2"}
    populator._register_references(test_id, test_refs)

    result = populator._registered_refs
    expected = {"ref1": {test_id}, "ref2": {test_id}}
    assert result == expected


def test_register_reference_previously_registered():
    class TestPopulator(Populator):
        pass

    TestPopulator.__abstractmethods__ = False

    populator = TestPopulator()
    populator._registered_refs = {"ref1": {"id1"}, "ref2": {"id1"}}

    test_id = "id2"
    test_refs = {"ref1", "ref3"}
    populator._register_references(test_id, test_refs)

    result = populator._registered_refs
    expected = {"ref1": {test_id, "id1"}, "ref2": {"id1"}, "ref3": {test_id}}
    assert result == expected


# def test_integration_populate_require_unique_ids(tmp_path: Path, base_path: str) -> None:

#     class TestLoader(FileLoader, TimeVectorLoader):

#         _SUPPORTED_SUFFIXES: ClassVar[list] = [".txt"]

#         def __init__(self,
#                      source: Path|str,
#                      relative_loc: Optional[Union[Path, str]] = None) -> None:
#             super().__init__(source, relative_loc)

#     TestLoader.__abstractmethods__ = False

#     class TestLoadedTimeVector(TimeVector):

#         def __init__(self, vector_id: str, loader: TimeVectorLoader) -> None:
#             self._vector_id = vector_id
#             self._loader = loader

#     TestLoadedTimeVector.__abstractmethods__ = False

#     existing_source = tmp_path / Path("test1.txt")
#     create_tmp_file(existing_source)
#     existing_loader = TestLoader(existing_source)
#     existing_tv = TestLoadedTimeVector("id1", existing_loader)
#     test_existing_data = {
#         "id1": existing_tv,
#     }

#     new_source = tmp_path / Path("test2.txt")
#     create_tmp_file(new_source)
#     new_loader = TestLoader(new_source)
#     new_tv = TestLoadedTimeVector("id1", new_loader)
#     new_tv2 =  TestLoadedTimeVector("id2", new_loader)
#     test_new_data = {
#         "id1": new_tv,
#         "id2": new_tv2,
#     }

#     expected_duplicates = {
#         "id1": [new_source, existing_source],
#         }

#     model = Model()
#     model._data.update(test_existing_data)

#     class TestPopulator(NVEEnergyModelPopulator):

#         def __init__(self, source: Path) -> None:
#             super().__init__(source)

#         def _populate(self) -> dict[str, Union[Component, TimeVector, Curve, Expr]]:
#             return test_new_data

#     populator = TestPopulator("test")

#     with patch(base_path + ".send_error_event") as mock_send_error_event, \
#         pytest.raises(ValueError, match=re.escape(f"Duplicate ID's found: {expected_duplicates}.")):
#         populator.populate(model)
#         assert mock_send_error_event.call_count == 1
