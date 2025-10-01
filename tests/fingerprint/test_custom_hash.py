import pytest

from framcore.fingerprints import fingerprint as fp


def test_when_null_then_null_string():
    assert fp._custom_hash(None) == "None"

@pytest.mark.parametrize(("value", "expected"), [
    ("test", "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"),
    ("some other string", "f1bb3c727e6a970391e4a9df119935299de65ab2"),
])
def test_when_str_then_sha1_hash(value, expected):
    result = fp._custom_hash(value)
    assert expected == result

@pytest.mark.parametrize(("value", "expected"), [
    (1, "1"),
    (True, "True"),
    (1.1, "1.1"),
])
def test_when_primitives_then_simple_hash(value, expected):
    result = fp._custom_hash(value)
    assert expected == result
