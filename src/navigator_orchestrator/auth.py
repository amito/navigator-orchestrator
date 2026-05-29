from __future__ import annotations

from contextvars import ContextVar

auth_token_var: ContextVar[str | None] = ContextVar("auth_token", default=None)


def extract_bearer_token(header_value: str | None) -> str | None:
    """Extract the bearer token from an Authorization header value.

    Returns None if the header is missing or doesn't start with 'Bearer '.
    """
    if not header_value:
        return None
    if not header_value.startswith("Bearer "):
        return None
    return header_value[7:]
