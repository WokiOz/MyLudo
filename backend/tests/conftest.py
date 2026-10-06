import pytest
from fastapi.testclient import TestClient

from app import auth, db
from app.api.bgg import get_bgg_client
from app.api.rules import get_claude_client
from app.api.videos import get_optional_youtube_client, get_youtube_client
from app.config import get_settings
from app.integrations.bgg import BggClient
from app.integrations.youtube import YouTubeClient
from app.main import app
from tests.bgg_fixtures import bgg_transport
from tests.claude_fixtures import claude_client
from tests.youtube_fixtures import youtube_transport


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    """Fabrique un client de test sur une base neuve, migrations comprises."""
    opened = []

    def _make(password: str = "") -> TestClient:
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test-{len(opened)}.db")
        monkeypatch.setenv("APP_PASSWORD", password)
        monkeypatch.setenv("BGG_TOKEN", "jeton")
        get_settings.cache_clear()
        db.reset_engine()
        auth.reset_failures()
        app.dependency_overrides[get_bgg_client] = lambda: BggClient(
            "jeton", transport=bgg_transport(), retry_delay=0
        )
        app.dependency_overrides[get_youtube_client] = lambda: YouTubeClient(
            "cle-secrete", transport=youtube_transport()
        )
        app.dependency_overrides[get_optional_youtube_client] = lambda: YouTubeClient(
            "cle-secrete", transport=youtube_transport()
        )
        app.dependency_overrides[get_claude_client] = lambda: claude_client()
        client = TestClient(app)
        client.__enter__()
        opened.append(client)
        return client

    yield _make
    for client in opened:
        client.__exit__(None, None, None)
    app.dependency_overrides.clear()
    db.reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
