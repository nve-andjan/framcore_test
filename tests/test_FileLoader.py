import re
from pathlib import Path
from unittest.mock import patch

import pytest

from framcore.loaders import FileLoader


@pytest.fixture
def loader_path():
    return "framcore.loaders.loaders"

def test_init(tmp_path, loader_path):
    source = Path(tmp_path)
    relative_loc = "test.txt"

    path = source / relative_loc
    with path.open("w") as f:
        f.write("Test")

    FileLoader.__abstractmethods__ = False
    with patch(loader_path + ".FileLoader._SUPPORTED_SUFFIXES", new=[".txt"]), \
        patch(loader_path + ".Base._check_type") as mock_check_type:
        FileLoader(source, relative_loc)

        assert mock_check_type.call_count == 2

def test_init_check_path_exists_raise_error(loader_path):
    path = "test.xlsx"

    FileLoader.__abstractmethods__ = False
    with patch(loader_path + ".Base.send_error_event") as mock_send_error_event, \
         pytest.raises(FileNotFoundError,  # noqa: PT012
                       match = re.escape(f"File {path} does not exist. Could not create {FileLoader}.")):
        FileLoader(path)
        assert mock_send_error_event.call_count == 1

def test_init_check_path_supported_raise_error(tmp_path, loader_path):
    path = Path(tmp_path / "test.txt")
    with path.open("w") as f:
        f.write("Test")

    FileLoader.__abstractmethods__ = False
    match_msg = f"File type of {path}, .txt is not supported by {FileLoader}. Supported filetypes: {[]}"
    with patch(loader_path + ".Base.send_error_event") as mock_send_error_event, \
         pytest.raises(ValueError,  # noqa: PT012
                       match = re.escape(match_msg)):
        FileLoader(path)
        assert mock_send_error_event.call_count == 1
