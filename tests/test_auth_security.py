from app.auth import is_safe_next_url


def test_relative_redirects_are_allowed():
    assert is_safe_next_url("/dashboard")
    assert is_safe_next_url("/modules/sujets?filter=active")


def test_external_and_scheme_relative_redirects_are_rejected():
    assert not is_safe_next_url("https://attacker.example")
    assert not is_safe_next_url("//attacker.example/path")
    assert not is_safe_next_url("javascript:alert(1)")
    assert not is_safe_next_url("")
    assert not is_safe_next_url("dashboard")
