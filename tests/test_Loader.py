import re
from pathlib import Path

import pytest

from framcore.loaders import Loader


def test_get_ids_require_unique_ids() -> None:
    test_path = Path(r"test/path.xlsx")
    class TestLoader(Loader):

        def __init__(self, source: Path = None) -> None:
             self.source = source
             self._content_ids = None

        def get_source(self) -> Path:
            return Path(self.source)

        def _get_ids(self) -> list:
            return ["id1", "id2", "id3", "id1"]

    TestLoader.__abstractmethods__ = False

    test_loader = TestLoader(test_path)
    with pytest.raises(ValueError,
                      match=re.escape(f"Duplicate ID's found in {test_path}: ['id1']")):
        test_loader.get_ids()

def test_id_exists_require_existing_id():
    class TestLoader(Loader):

        def get_ids(self) -> list:
            return []

    TestLoader.__abstractmethods__ = False

    test_loader = TestLoader()
    test_id = "non_existent_id"
    with pytest.raises(KeyError, match=re.escape((f"Could not find ID {test_id} in {test_loader}."  # noqa: UP034
                                                  f" Existing IDs: {test_loader.get_ids()}"))):
        test_loader._id_exsists(test_id)
