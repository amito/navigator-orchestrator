from navigator_orchestrator.auth import auth_token_var, extract_bearer_token


def test_extract_bearer_token():
    assert extract_bearer_token("Bearer abc123") == "abc123"


def test_extract_bearer_token_no_prefix():
    assert extract_bearer_token("abc123") is None


def test_extract_bearer_token_none():
    assert extract_bearer_token(None) is None


def test_extract_bearer_token_empty():
    assert extract_bearer_token("") is None


def test_contextvar_default_is_none():
    assert auth_token_var.get() is None


def test_contextvar_set_and_get():
    token = auth_token_var.set("my-token")
    assert auth_token_var.get() == "my-token"
    auth_token_var.reset(token)
    assert auth_token_var.get() is None
