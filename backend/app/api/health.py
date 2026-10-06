from fastapi import APIRouter, Depends

from app.auth import require_auth
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["santé"])


@router.get("/health")
def health() -> dict:
    """Sonde publique, utilisée par Docker."""
    return {"status": "ok"}


@router.get("/status", dependencies=[Depends(require_auth)])
def status() -> dict:
    """Intégrations configurées."""
    s = get_settings()
    return {
        "integrations": {
            "boardgamegeek": bool(s.bgg_token),
            "youtube": bool(s.youtube_api_key),
            "youtube_channels": s.youtube_channel_names,
            "claude": bool(s.anthropic_api_key),
            "price_sources": s.enabled_price_sources,
        },
    }
