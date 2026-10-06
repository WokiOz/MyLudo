import anthropic
import pytest

from app.api.rules import get_claude_client
from app.integrations import claude
from app.main import app
from tests.claude_fixtures import REQUESTS, claude_client, message


@pytest.fixture(autouse=True)
def _reset_requests():
    REQUESTS.clear()


def make_game(client):
    return client.post(
        "/api/games",
        json={
            "name_fr": "Les Aventuriers du Rail",
            "year": 2004,
            "min_players": 2,
            "max_players": 5,
            "min_time": 30,
            "max_time": 60,
        },
    ).json()


def test_templates_cover_both_kinds(client):
    templates = client.get("/api/rules/templates").json()
    assert set(templates) == {"summary", "beginner_guide"}
    assert "## Aide-mémoire du tour" in templates["beginner_guide"]


def test_save_read_replace_and_delete(client):
    game = make_game(client)
    url = f"/api/games/{game['id']}/rules/summary"
    assert client.get(f"/api/games/{game['id']}/rules").json() == []

    assert client.put(url, json={"content_md": "## But\nRelier des villes."}).status_code == 204
    sheets = client.get(f"/api/games/{game['id']}/rules").json()
    assert [(s["kind"], s["origin"], s["reviewed"]) for s in sheets] == [
        ("summary", "manual", True)
    ]

    client.put(url, json={"content_md": "  Nouveau texte  "})
    sheets = client.get(f"/api/games/{game['id']}/rules").json()
    assert len(sheets) == 1 and sheets[0]["content_md"] == "Nouveau texte"
    detail = client.get(f"/api/games/{game['id']}").json()
    assert detail["rules"] == [{"kind": "summary", "origin": "manual", "reviewed": True}]

    assert client.put(url, json={"content_md": "   "}).status_code == 204
    assert client.get(f"/api/games/{game['id']}/rules").json() == []


def test_ai_draft_needs_review(client):
    game = make_game(client)
    url = f"/api/games/{game['id']}/rules/beginner_guide"
    client.put(url, json={"content_md": "Brouillon", "origin": "ai_draft", "reviewed": False})
    assert client.get(f"/api/games/{game['id']}").json()["rules"][0]["reviewed"] is False
    client.put(url, json={"content_md": "Brouillon relu", "origin": "ai_draft", "reviewed": True})
    assert client.get(f"/api/games/{game['id']}").json()["rules"][0]["reviewed"] is True
    # Un texte écrit à la main est toujours considéré comme relu.
    client.put(url, json={"content_md": "Écrit à la main", "origin": "manual", "reviewed": False})
    assert client.get(f"/api/games/{game['id']}").json()["rules"][0]["reviewed"] is True


def test_rule_validation(client):
    game = make_game(client)
    assert (
        client.put(f"/api/games/{game['id']}/rules/autre", json={"content_md": "x"}).status_code
        == 422
    )
    big = {"content_md": "x" * 20001}
    assert client.put(f"/api/games/{game['id']}/rules/summary", json=big).status_code == 422
    assert client.put("/api/games/999/rules/summary", json={"content_md": "x"}).status_code == 404


def test_draft_is_returned_not_saved_and_uses_notes(client):
    game = make_game(client)
    client.post(
        f"/api/games/{game['id']}/notes",
        json={"kind": "forgotten_rule", "text": "On pioche 2 cartes wagon"},
    )
    response = client.post(f"/api/games/{game['id']}/rules/summary/draft")
    assert response.status_code == 200
    assert response.json()["content_md"].startswith("## But du jeu")
    assert client.get(f"/api/games/{game['id']}/rules").json() == []

    prompt = REQUESTS[-1]["json"]["messages"][0]["content"]
    assert "Les Aventuriers du Rail" in prompt and "2–5 joueurs" in prompt
    assert "On pioche 2 cartes wagon" in prompt and "## But du jeu" in prompt


def test_draft_request_shape(client):
    game = make_game(client)
    client.post(f"/api/games/{game['id']}/rules/beginner_guide/draft")
    request = REQUESTS[-1]
    body = request["json"]
    assert body["model"] == "claude-opus-5-5"
    assert body["fallbacks"] == "default"
    assert body["output_config"] == {"effort": "medium"}
    assert "thinking" not in body and "temperature" not in body
    assert "server-side-fallback-2026-07-01" in request["headers"]["anthropic-beta"]
    assert "Ne recopie jamais" in body["system"]
    assert "## Aide-mémoire du tour" in body["messages"][0]["content"]


def test_draft_without_key_is_503(make_client, monkeypatch):
    client = make_client()
    del app.dependency_overrides[get_claude_client]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    game = make_game(client)
    response = client.post(f"/api/games/{game['id']}/rules/summary/draft")
    assert response.status_code == 503 and "ANTHROPIC_API_KEY" in response.json()["detail"]


@pytest.mark.parametrize(
    ("body", "status", "expected"),
    [
        (message("", "refusal"), 200, "refusé"),
        (message(""), 200, "rien renvoyé"),
        (None, 401, "ANTHROPIC_API_KEY"),
        (None, 429, "Trop de demandes"),
        (None, 500, "erreur (500)"),
    ],
)
def test_draft_errors(client, body, status, expected):
    app.dependency_overrides[get_claude_client] = lambda: claude_client(body, status)
    game = make_game(client)
    response = client.post(f"/api/games/{game['id']}/rules/summary/draft")
    assert response.status_code == 502 and expected in response.json()["detail"]


def test_truncated_draft_is_flagged():
    client = claude_client(message("## But du jeu\nDébut", "max_tokens"))
    text = claude.draft({"name_fr": "Jeu"}, [], "summary", client)
    assert text.endswith("à compléter.\n")


def test_connection_error_is_french():
    import httpx2

    def boom(request):
        raise httpx2.ConnectError("hors ligne")

    client = anthropic.Anthropic(
        api_key="x",
        max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(boom)),
    )
    with pytest.raises(claude.ClaudeError, match="ne répond pas"):
        claude.draft({"name_fr": "Jeu"}, [], "summary", client)


def test_model_is_configurable(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    get_settings.cache_clear()
    claude.draft({"name_fr": "Jeu"}, [], "summary", claude_client())
    get_settings.cache_clear()
    assert REQUESTS[-1]["json"]["model"] == "claude-sonnet-5-5"


def test_rule_routes_need_login(make_client):
    client = make_client("secret")
    assert client.get("/api/rules/templates").status_code == 401
    assert client.put("/api/games/1/rules/summary", json={"content_md": "x"}).status_code == 401
    assert client.post("/api/games/1/rules/summary/draft").status_code == 401
