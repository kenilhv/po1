from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import require_auth
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    code: str


@router.post("/login")
def login(body: LoginBody):
    result = auth_service.login(body.code)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code")
    token, role = result
    return {"token": token, "role": role}


@router.post("/logout")
def logout(auth: tuple[str, str] = Depends(require_auth)):
    auth_service.logout(auth[0])
    return {"success": True}


@router.get("/me")
def me(auth: tuple[str, str] = Depends(require_auth)):
    return {"role": auth[1]}
