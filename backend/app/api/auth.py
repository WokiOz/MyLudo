from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app import auth

router = APIRouter(prefix="/api/auth", tags=["connexion"])


class LoginIn(BaseModel):
    password: str


@router.get("/status")
def status(request: Request) -> dict:
    return {
        "auth_required": auth.auth_required(),
        "authenticated": auth.is_authenticated(request),
    }


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response) -> dict:
    if not auth.auth_required():
        return {"authenticated": True}
    client = request.client.host if request.client else "inconnu"
    if auth.is_locked(client):
        raise HTTPException(429, "Trop de tentatives. Réessaie dans quelques minutes.")
    if not auth.check_password(body.password):
        auth.register_failure(client)
        raise HTTPException(401, "Mot de passe incorrect.")
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(),
        max_age=auth.SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    return {"authenticated": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(auth.COOKIE_NAME)
    return {"authenticated": False}
