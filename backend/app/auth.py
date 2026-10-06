"""Protection par mot de passe unique (APP_PASSWORD), session par cookie signé."""

import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from app.config import get_settings

COOKIE_NAME = "myludo_session"
SESSION_SECONDS = 30 * 24 * 3600
MAX_FAILURES = 5
FAILURE_WINDOW = 300

_failures: dict[str, list[float]] = {}


def auth_required() -> bool:
    return bool(get_settings().app_password)


def _key() -> bytes:
    return hashlib.sha256(("myludo-session:" + get_settings().app_password).encode()).digest()


def _sign(expires: int) -> str:
    return hmac.new(_key(), str(expires).encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    expires = int(time.time()) + SESSION_SECONDS
    return f"{expires}.{_sign(expires)}"


def token_valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    expires, _, signature = token.partition(".")
    if not expires.isdigit() or int(expires) < time.time():
        return False
    return hmac.compare_digest(signature, _sign(int(expires)))


def is_authenticated(request: Request) -> bool:
    return not auth_required() or token_valid(request.cookies.get(COOKIE_NAME))


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Connexion requise.")


def check_password(candidate: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(candidate.encode()).digest(),
        hashlib.sha256(get_settings().app_password.encode()).digest(),
    )


def register_failure(client: str) -> None:
    now = time.time()
    recent = [t for t in _failures.get(client, []) if now - t < FAILURE_WINDOW]
    recent.append(now)
    _failures[client] = recent


def is_locked(client: str) -> bool:
    now = time.time()
    recent = [t for t in _failures.get(client, []) if now - t < FAILURE_WINDOW]
    _failures[client] = recent
    return len(recent) >= MAX_FAILURES


def reset_failures() -> None:
    _failures.clear()
