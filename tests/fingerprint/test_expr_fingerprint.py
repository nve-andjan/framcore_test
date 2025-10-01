from framcore.expressions import Expr


def test_same_exprs_should_have_same_fingerprint():
    expr1 = create_expr(dict())
    expr2 = create_expr(dict())

    assert expr1.get_fingerprint().get_hash() == expr2.get_fingerprint().get_hash()

def test_exprs_with_different_src_should_have_different_fingerprints():
    expr1 = create_expr(dict(src="capacity_level_gas_ccgt_no2"))
    expr2 = create_expr(dict(src="capacity_level_gas_ccgt_no3"))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def test_exprs_with_different_is_stock_should_have_different_fingerprints():
    expr1 = create_expr(dict(is_stock=True))
    expr2 = create_expr(dict(is_stock=False))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def test_exprs_with_different_is_flow_should_have_different_fingerprints():
    expr1 = create_expr(dict(is_flow=True))
    expr2 = create_expr(dict(is_flow=False))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def test_exprs_with_different_is_profile_should_have_different_fingerprints():
    expr1 = create_expr(dict(is_profile=True))
    expr2 = create_expr(dict(is_profile=False))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def test_exprs_with_different_is_level_should_have_different_fingerprints():
    expr1 = create_expr(dict(is_level=True))
    expr2 = create_expr(dict(is_level=False))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def test_exprs_with_different_profile_should_have_different_fingerprints():
    expr1 = create_expr(dict(profile=Expr(src="profile1")))
    expr2 = create_expr(dict(profile=Expr(src="profile2")))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def test_exprs_with_different_operations_should_have_different_fingerprints():
    expr1 = create_expr(dict(operations=("+", [Expr(src="a"), Expr(src="b")])))
    expr2 = create_expr(dict(operations=("-", [Expr(src="a"), Expr(src="b")])))

    assert expr1.get_fingerprint().get_hash() != expr2.get_fingerprint().get_hash()

def create_expr(props: dict) -> Expr:
    return Expr(src=props.get("src"), is_stock=props.get("is_stock", False), is_flow=props.get("is_flow", False), is_profile=props.get("is_profile", False), is_level=props.get("is_level", False), profile=props.get("profile"), operations=props.get("operations"))
