from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, status

from services import auth_service

Role = Literal["ap", "cfo"]


def _bearer(authorization: str | None = Header(default=None)) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def require_auth(authorization: Annotated[str | None, Depends(_bearer)]) -> tuple[str, Role]:
    token = authorization
    role = auth_service.get_role(token)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return token, role  # type: ignore[return-value]


def require_ap(auth: Annotated[tuple[str, Role], Depends(require_auth)]) -> tuple[str, Role]:
    token, role = auth
    if role != "ap":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AP role required")
    return token, role


def require_cfo(auth: Annotated[tuple[str, Role], Depends(require_auth)]) -> tuple[str, Role]:
    token, role = auth
    if role != "cfo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CFO role required")
    return token, role
