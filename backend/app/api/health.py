from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["santé"])


@router.get("/health")
def health() -> dict:
    """État de l'appli et des intégrations configurées."""
    s = get_settings()
    return {
        "status": "ok",
        "integrations": {
            "boardgamegeek": bool(s.bgg_token),
            "youtube": bool(s.youtube_api_key),
            "claude": bool(s.anthropic_api_key),
            "price_sources": s.enabled_price_sources,
        },
    }
