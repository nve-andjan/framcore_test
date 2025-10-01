import pytest

from framcore.expressions import Expr, ensure_expr


def test_returns_none_with_input_none():
    expected = None
    result = ensure_expr(None)

    assert result == expected


def test_returns_expr_when_expected_type():
    expected = Expr("1", is_level=True)
    result = ensure_expr(expected, is_level=True)
    assert result == expected


@pytest.mark.parametrize(
    "input_expr",
    [Expr("1", is_flow=True), Expr("1", is_stock=True), Expr("1", is_level=True), Expr("1", is_profile=True)],
)
def test_fails_when_unexpected_expr_type(input_expr: Expr) -> None:
    match_message = (
        "Given Expr has a mismatch between expected and actual flow/stock or level/profile status:\nExpected: "
        f"is_flow - {False}, is_stock - {False}, is_level - {False}, is_profile - {False}\n"
        f"Actual: is_flow - {input_expr.is_flow()}, is_stock - {input_expr.is_stock()}, "
        f"is_level - {input_expr.is_level()}, is_profile - {input_expr.is_profile()}"
    )
    with pytest.raises(ValueError, match=match_message):
        ensure_expr(input_expr)
