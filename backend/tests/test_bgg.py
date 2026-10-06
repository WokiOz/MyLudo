import httpx
import pytest

from app.integrations.bgg import BggClient, BggError, parse_thing
from tests.bgg_fixtures import CATAN, bgg_transport


def test_parse_thing():
    game = parse_thing(CATAN)
    assert game.name == "Catan"
    assert (game.min_players, game.max_players) == (3, 4)
    assert game.best_players == "3,4"
    assert (game.min_time, game.max_time, game.min_age) == (60, 120, 10)
    assert game.publisher == "Kosmos"
    assert (game.weight, game.rating) == (2.32, 7.12)
    assert game.categories == ["Negotiation", "Inconnue de la table"]


def test_search_puts_exact_match_first():
    hits = BggClient("jeton", transport=bgg_transport()).search("catan")
    assert [h.name for h in hits] == ["Catan", "Catan Junior", "Catan : Marins"]
    assert hits[2].is_expansion


def test_queued_responses_are_retried():
    client = BggClient("jeton", transport=bgg_transport(queued=2), retry_delay=0)
    assert client.fetch(13).name == "Catan"


@pytest.mark.parametrize(
    ("status", "message"),
    [(401, "jeton"), (429, "limite"), (500, "erreur")],
)
def test_http_errors_become_french_messages(status, message):
    client = BggClient("jeton", transport=bgg_transport(status=status))
    with pytest.raises(BggError, match=message):
        client.fetch(13)


def test_network_failure():
    def boom(request):
        raise httpx.ConnectError("hors ligne")

    client = BggClient("jeton", transport=httpx.MockTransport(boom))
    with pytest.raises(BggError, match="ne répond pas"):
        client.search("catan")


def test_unknown_game():
    with pytest.raises(BggError, match="introuvable"):
        BggClient("jeton", transport=bgg_transport()).fetch(999)


def test_search_route_flags_known_games(client):
    assert client.post("/api/bgg/import", json={"bgg_id": 13}).status_code == 201
    hits = client.get("/api/bgg/search", params={"q": "catan"}).json()
    by_name = {h["name"]: h for h in hits}
    assert by_name["Catan"]["game_id"] is not None
    assert by_name["Catan Junior"]["game_id"] is None


def test_import_creates_game_with_french_tags(client):
    game = client.post("/api/bgg/import", json={"bgg_id": 13, "status": "wishlist"}).json()
    assert game["name_fr"] == "Catan" and game["bgg_id"] == 13
    assert game["status"] == "wishlist" and game["bgg_rating"] == 7.12
    labels = {t["label"] for t in game["tags"]}
    assert {"Négociation", "Placement d'ouvriers", "Échanges", "Lancer de dés"} <= labels
    assert {"Moyen", "3–4 joueurs", "1–2 h", "Idéal à 3", "Idéal à 4"} <= labels
    kinds = {t["label"]: t["kind"] for t in game["tags"]}
    assert kinds["Négociation"] == "style" and kinds["Échanges"] == "mechanic"


def test_import_twice_is_refused(client):
    client.post("/api/bgg/import", json={"bgg_id": 13})
    response = client.post("/api/bgg/import", json={"bgg_id": 13})
    assert response.status_code == 409


def test_expansion_is_linked_to_its_base_game(client):
    base = client.post("/api/bgg/import", json={"bgg_id": 13}).json()
    extension = client.post("/api/bgg/import", json={"bgg_id": 200}).json()
    assert extension["base_game_id"] == base["id"]


def test_bgg_error_is_reported(client):
    assert client.post("/api/bgg/import", json={"bgg_id": 999}).status_code == 502


def test_not_configured(make_client, monkeypatch):
    client = make_client()
    from app.api.bgg import get_bgg_client
    from app.main import app

    del app.dependency_overrides[get_bgg_client]
    monkeypatch.setenv("BGG_TOKEN", "")
    from app.config import get_settings

    get_settings.cache_clear()
    response = client.get("/api/bgg/search", params={"q": "catan"})
    assert response.status_code == 503
    assert "BGG_TOKEN" in response.json()["detail"]
