from app.api.videos import get_optional_youtube_client
from app.main import app
from tests.youtube_fixtures import LUDO, OTHER


def make_game(client, name="Catan"):
    return client.post("/api/games", json={"name_fr": name}).json()


def test_suggestions(client):
    game = make_game(client)
    response = client.get(f"/api/games/{game['id']}/videos/suggestions")
    assert response.status_code == 200
    videos = response.json()
    assert [v["youtube_id"] for v in videos] == [LUDO, OTHER]
    assert videos[0]["priority"] is True and videos[0]["already_added"] is False


def test_suggestions_without_key_is_503(make_client, monkeypatch):
    from app.api.videos import get_youtube_client

    client = make_client()
    del app.dependency_overrides[get_youtube_client]
    monkeypatch.setenv("YOUTUBE_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    game = make_game(client)
    response = client.get(f"/api/games/{game['id']}/videos/suggestions")
    assert response.status_code == 503 and "YOUTUBE_API_KEY" in response.json()["detail"]


def test_pick_suggestion_then_flagged_as_added(client):
    game = make_game(client)
    pick = {
        "youtube_id": LUDO,
        "title": "Catan - Règles du jeu",
        "channel": "Ludochrono",
        "language": "fr",
    }
    response = client.post(f"/api/games/{game['id']}/videos/pick", json=pick)
    assert response.status_code == 201 and response.json()["source"] == "auto"
    assert client.post(f"/api/games/{game['id']}/videos/pick", json=pick).status_code == 409

    suggestions = client.get(f"/api/games/{game['id']}/videos/suggestions").json()
    assert {v["youtube_id"]: v["already_added"] for v in suggestions} == {LUDO: True, OTHER: False}
    assert [v["youtube_id"] for v in client.get(f"/api/games/{game['id']}").json()["videos"]] == [
        LUDO
    ]


def test_add_link_fills_title_from_youtube(client):
    game = make_game(client)
    response = client.post(
        f"/api/games/{game['id']}/videos", json={"url": f"https://youtu.be/{LUDO}?si=x"}
    )
    video = response.json()
    assert response.status_code == 201
    assert (video["title"], video["channel"], video["language"]) == (
        "Catan - Règles du jeu",
        "Ludochrono",
        "fr",
    )
    assert video["source"] == "manual"


def test_add_link_without_youtube_key_keeps_user_title(client):
    app.dependency_overrides[get_optional_youtube_client] = lambda: None
    game = make_game(client)
    response = client.post(
        f"/api/games/{game['id']}/videos",
        json={"url": f"https://www.youtube.com/watch?v={LUDO}", "title": "  Ma vidéo "},
    )
    assert response.status_code == 201 and response.json()["title"] == "Ma vidéo"
    other = client.post(
        f"/api/games/{game['id']}/videos", json={"url": f"https://youtu.be/{OTHER}"}
    ).json()
    assert other["title"] == "Vidéo YouTube" and other["channel"] is None


def test_add_link_rejects_bad_and_duplicate_links(client):
    game = make_game(client)
    url = f"/api/games/{game['id']}/videos"
    assert client.post(url, json={"url": "https://example.com/x"}).status_code == 422
    assert client.post(url, json={"url": "https://youtu.be/ZZZZZZZZZZZ"}).status_code == 422
    assert client.post(url, json={"url": f"https://youtu.be/{LUDO}"}).status_code == 201
    assert client.post(url, json={"url": f"https://youtu.be/{LUDO}"}).status_code == 409


def test_delete_video_and_cascade(client):
    game = make_game(client)
    video = client.post(
        f"/api/games/{game['id']}/videos", json={"url": f"https://youtu.be/{LUDO}"}
    ).json()
    assert client.delete(f"/api/videos/{video['id']}").status_code == 204
    assert client.delete(f"/api/videos/{video['id']}").status_code == 404
    client.post(f"/api/games/{game['id']}/videos", json={"url": f"https://youtu.be/{LUDO}"})
    assert client.delete(f"/api/games/{game['id']}").status_code == 204


def test_video_routes_need_login(make_client):
    client = make_client("secret")
    assert client.get("/api/games/1/videos/suggestions").status_code == 401
    assert client.post("/api/games/1/videos", json={"url": "x"}).status_code == 401
    assert client.delete("/api/videos/1").status_code == 401
