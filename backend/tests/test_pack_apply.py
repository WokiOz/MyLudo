from app.api.videos import get_optional_youtube_client
from app.main import app
from app.services.packs import load_pack


def make(client, name, **fields):
    return client.post("/api/games", json={"name_fr": name, **fields}).json()


def test_preview_only_lists_games_already_owned(client):
    make(client, "Catan")
    make(client, "Un jeu inconnu")
    preview = client.get("/api/pack").json()
    assert preview["total"] == len(load_pack().games)
    assert preview["in_collection"] == 1 and preview["to_add"] == 1
    catan = next(g for g in preview["games"] if g["name"] == "Catan")
    assert catan["game_id"] is not None
    assert (catan["new_videos"], catan["new_sheets"]) == (1, 2)


def test_apply_adds_videos_and_unreviewed_drafts(client):
    game = make(client, "Catan")
    result = client.post("/api/pack/apply").json()
    assert result == {"games": 1, "videos_added": 1, "sheets_added": 2}

    detail = client.get(f"/api/games/{game['id']}").json()
    assert len(detail["videos"]) == 1 and detail["videos"][0]["channel"] == "Ludovox"
    assert detail["videos"][0]["language"] == "fr" and detail["videos"][0]["source"] == "auto"
    assert {(r["kind"], r["origin"], r["reviewed"]) for r in detail["rules"]} == {
        ("summary", "ai_draft", False),
        ("beginner_guide", "ai_draft", False),
    }
    rules = client.get(f"/api/games/{game['id']}/rules").json()
    assert all(r["content_md"].startswith("## ") for r in rules)


def test_apply_creates_no_game_and_is_idempotent(client):
    make(client, "Catan")
    client.post("/api/pack/apply")
    again = client.post("/api/pack/apply").json()
    assert again == {"games": 0, "videos_added": 0, "sheets_added": 0}
    assert len(client.get("/api/games").json()) == 1
    assert client.get("/api/pack").json()["to_add"] == 0


def test_apply_never_overwrites_the_users_own_texts(client):
    game = make(client, "Carcassonne")
    client.put(
        f"/api/games/{game['id']}/rules/summary",
        json={"content_md": "Mon résumé à moi", "origin": "manual"},
    )
    result = client.post("/api/pack/apply").json()
    assert result["sheets_added"] == 1  # seule la fiche débutants manquait
    rules = {r["kind"]: r for r in client.get(f"/api/games/{game['id']}/rules").json()}
    assert rules["summary"]["content_md"] == "Mon résumé à moi"
    assert rules["summary"]["origin"] == "manual" and rules["summary"]["reviewed"] is True
    assert rules["beginner_guide"]["origin"] == "ai_draft"


def test_apply_keeps_videos_already_added(client):
    app.dependency_overrides[get_optional_youtube_client] = lambda: None
    game = make(client, "Catan")
    added = client.post(
        f"/api/games/{game['id']}/videos", json={"url": "https://youtu.be/tvI8eFfm6Bk"}
    )
    assert added.status_code == 201
    result = client.post("/api/pack/apply").json()
    assert result["videos_added"] == 0
    assert len(client.get(f"/api/games/{game['id']}").json()["videos"]) == 1


def test_matching_ignores_accents_case_and_uses_aliases_and_original_name(client):
    pandemic = make(client, "PANDEMIE")  # sans accent, en majuscules
    colons = make(client, "Les Colons de Catane")  # alias de Catan
    bgg = make(client, "Mon jeu", name_original="Ticket to Ride")  # nom d'origine
    sold = make(client, "Azul", status="sold")  # vendu : ignoré
    client.post("/api/pack/apply")
    for game, expected in ((pandemic, 1), (colons, 1), (bgg, 1), (sold, 0)):
        assert len(client.get(f"/api/games/{game['id']}").json()["videos"]) == expected, game[
            "name_fr"
        ]


def test_wishlist_games_are_completed_too(client):
    game = make(client, "Dixit", status="wishlist")
    client.post("/api/pack/apply")
    assert len(client.get(f"/api/games/{game['id']}").json()["videos"]) == 1


def test_pack_routes_need_login(make_client):
    client = make_client("secret")
    assert client.get("/api/pack").status_code == 401
    assert client.post("/api/pack/apply").status_code == 401


def test_missing_lists_games_the_pack_does_not_cover(client):
    make(client, "Catan")  # couvert par le paquet
    make(client, "Le jeu de Paul", year=2021, min_players=2, max_players=5)
    make(client, "Déjà complet")
    done = client.get("/api/games").json()
    complete = next(g for g in done if g["name_fr"] == "Déjà complet")
    for kind in ("summary", "beginner_guide"):
        client.put(f"/api/games/{complete['id']}/rules/{kind}", json={"content_md": "Texte"})
    app.dependency_overrides[get_optional_youtube_client] = lambda: None
    client.post(f"/api/games/{complete['id']}/videos", json={"url": "https://youtu.be/AAAAAAAAAAA"})

    missing = client.get("/api/pack/missing").json()
    assert [g["name"] for g in missing] == ["Le jeu de Paul"]
    paul = missing[0]
    assert (paul["year"], paul["min_players"], paul["max_players"]) == (2021, 2, 5)
    assert paul["lacks"] == ["vidéo", "règles simplifiées", "fiche débutants"]


def test_missing_shrinks_as_the_user_writes_content(client):
    game = make(client, "Le jeu de Paul")
    client.put(f"/api/games/{game['id']}/rules/summary", json={"content_md": "Résumé"})
    assert client.get("/api/pack/missing").json()[0]["lacks"] == ["vidéo", "fiche débutants"]


def test_missing_ignores_sold_games_and_needs_login(client, make_client):
    make(client, "Vendu", status="sold")
    assert client.get("/api/pack/missing").json() == []
    secured = make_client("secret")
    assert secured.get("/api/pack/missing").status_code == 401
