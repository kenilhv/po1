from __future__ import annotations

import secrets
from typing import Literal

Role = Literal["ap", "cfo"]

_CODES: dict[str, Role] = {
    "AP2024": "ap",
    "CFO2024": "cfo",
}

_tokens: dict[str, Role] = {}


def login(code: str) -> tuple[str, Role] | None:
    role = _CODES.get(code.strip())
    if not role:
        return None
    token = secrets.token_urlsafe(32)
    _tokens[token] = role
    return token, role


def logout(token: str) -> None:
    _tokens.pop(token, None)


def get_role(token: str | None) -> Role | None:
    if not token:
        return None
    return _tokens.get(token)
