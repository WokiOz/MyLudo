def make(client, **fields):
    body = {"name_fr": "Jeu", **fields}
    response = client.post("/api/games", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def tag_labels(game):
    return {t["label"] for t in game["tags"]}


def test_create_computes_automatic_tags(client):
    game = make(
        client,
        name_fr="Les Aventuriers du Rail",
        min_players=2,
        max_players=5,
        max_time=60,
        weight=1.9,
        min_age=8,
    )
    assert {"Facile", "2 joueurs", "5 joueurs et plus", "30–60 min", "Famille"} <= tag_labels(game)
    assert all(t["source"] == "auto" for t in game["tags"])


def test_update_recomputes_tags_and_keeps_user_tags(client):
    game = make(client, max_time=20, weight=1.0)
    client.post(f"/api/games/{game['id']}/tags", json={"label": "  Avec  papa "})
    updated = client.patch(f"/api/games/{game['id']}", json={"max_time": 90, "weight": 3.8}).json()
    labels = tag_labels(updated)
    assert {"1–2 h", "Expert", "Avec papa"} <= labels
    assert not {"Moins de 30 min", "Très facile"} & labels


def test_update_validates_full_record(client):
    game = make(client, min_players=2, max_players=4)
    response = client.patch(f"/api/games/{game['id']}", json={"min_players": 6})
    assert response.status_code == 422
    assert client.patch(f"/api/games/{game['id']}", json={"rating": 11}).status_code == 422
    assert client.patch(f"/api/games/{game['id']}", json={"inconnu": 1}).status_code == 422
    assert client.get(f"/api/games/{game['id']}").json()["min_players"] == 2


def test_rating_comment_and_purchase(client):
    game = make(client)
    patch = {
        "rating": 8,
        "comment": "Super à 4",
        "purchase_price_cents": 3990,
        "purchase_date": "2025-12-24",
        "status": "lent",
        "lent_to": "Paul",
    }
    data = client.patch(f"/api/games/{game['id']}", json=patch).json()
    assert data["rating"] == 8 and data["purchase_price_cents"] == 3990
    assert data["status"] == "lent" and data["lent_to"] == "Paul"


def test_custom_tags_are_reused_and_unused_ones_cleaned(client):
    a, b = make(client, name_fr="A"), make(client, name_fr="B")
    client.post(f"/api/games/{a['id']}/tags", json={"label": "Soirée"})
    client.post(f"/api/games/{b['id']}/tags", json={"label": "soirée"})
    tags = client.get("/api/tags").json()
    assert [(t["label"], t["count"]) for t in tags if t["kind"] == "custom"] == [("Soirée", 2)]

    tag_id = next(t["id"] for t in tags if t["kind"] == "custom")
    assert client.delete(f"/api/games/{a['id']}/tags/{tag_id}").status_code == 200
    client.delete(f"/api/games/{b['id']}/tags/{tag_id}")
    assert not [t for t in client.get("/api/tags").json() if t["kind"] == "custom"]


def test_auto_tag_cannot_be_removed_by_hand(client):
    game = make(client, max_time=20)
    tag = game["tags"][0]
    assert client.delete(f"/api/games/{game['id']}/tags/{tag['id']}").status_code == 409


def test_search_ignores_accents_and_case(client):
    make(client, name_fr="Les Aventuriers du Rail : Europe")
    make(client, name_fr="Échecs")
    make(client, name_fr="7 Wonders")

    def names(q):
        return [g["name_fr"] for g in client.get("/api/games", params={"q": q}).json()]

    assert names("echecs") == ["Échecs"]
    assert names("AVENTURIERS rail") == ["Les Aventuriers du Rail : Europe"]
    assert names("wonders 7") == ["7 Wonders"]
    assert names("a_b") == []
    assert len(names("")) == 3


def test_filters_combine(client):
    make(client, name_fr="Rapide", min_players=2, max_players=6, max_time=20, weight=1.2)
    make(client, name_fr="Long", min_players=2, max_players=4, max_time=180, weight=3.9)
    make(client, name_fr="Solo", min_players=1, max_players=1, max_time=45, weight=2.0)
    make(client, name_fr="Souhait", min_players=2, max_players=4, status="wishlist")

    def find(**params):
        return [g["name_fr"] for g in client.get("/api/games", params=params).json()]

    assert find(players=5) == ["Rapide"]
    assert find(players=1) == ["Solo"]
    assert find(max_time=60) == ["Rapide", "Solo"]
    assert find(status="wishlist") == ["Souhait"]
    # Une durée inconnue n'est pas retenue par le filtre de durée.
    assert find(status=["owned", "wishlist"], players=4, max_time=200) == ["Long", "Rapide"]
    assert find(status=["owned", "wishlist"], players=4) == ["Long", "Rapide", "Souhait"]

    tags = {t["label"]: t["id"] for t in client.get("/api/tags").json()}
    assert find(tag_ids=[tags["Expert"]]) == ["Long"]
    assert find(tag_ids=[tags["2 joueurs"], tags["Facile"]]) == []
    assert find(tag_ids=[tags["2 joueurs"], tags["Moins de 30 min"]]) == ["Rapide"]


def test_sorting(client):
    make(client, name_fr="Bravo", rating=5, purchase_price_cents=1000)
    make(client, name_fr="Alpha", rating=9, purchase_price_cents=500)
    make(client, name_fr="Charlie")

    def order(sort):
        return [g["name_fr"] for g in client.get("/api/games", params={"sort": sort}).json()]

    assert order("name") == ["Alpha", "Bravo", "Charlie"]
    assert order("rating") == ["Alpha", "Bravo", "Charlie"]
    assert order("price") == ["Bravo", "Alpha", "Charlie"]
    assert order("recent") == ["Charlie", "Alpha", "Bravo"]


def test_notes_crud(client):
    game = make(client)
    url = f"/api/games/{game['id']}/notes"
    note = client.post(
        url, json={"kind": "forgotten_rule", "text": " On pioche en fin de tour "}
    ).json()
    assert note["text"] == "On pioche en fin de tour"
    assert client.post(url, json={"kind": "autre", "text": "x"}).status_code == 422
    assert client.post(url, json={"kind": "strategy", "text": ""}).status_code == 422

    client.patch(f"/api/notes/{note['id']}", json={"kind": "common_mistake", "text": "Erreur"})
    notes = client.get(f"/api/games/{game['id']}").json()["notes"]
    assert [(n["kind"], n["text"]) for n in notes] == [("common_mistake", "Erreur")]

    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.get(f"/api/games/{game['id']}").json()["notes"] == []


def test_delete_game_removes_notes_and_tags(client):
    game = make(client, max_time=20)
    client.post(f"/api/games/{game['id']}/notes", json={"kind": "strategy", "text": "x"})
    assert client.delete(f"/api/games/{game['id']}").status_code == 204
    assert client.get(f"/api/games/{game['id']}").status_code == 404
    assert client.get("/api/tags").json() == []


def test_expansions(client):
    base = make(client, name_fr="Base")
    ext = make(client, name_fr="Extension", base_game_id=base["id"])
    assert client.get(f"/api/games/{base['id']}").json()["extensions"] == [
        {"id": ext["id"], "name_fr": "Extension"}
    ]
    assert client.post("/api/games", json={"name_fr": "X", "base_game_id": 999}).status_code == 422
    assert (
        client.patch(f"/api/games/{base['id']}", json={"base_game_id": base["id"]}).status_code
        == 422
    )
    client.delete(f"/api/games/{base['id']}")
    assert client.get(f"/api/games/{ext['id']}").json()["base_game_id"] is None


def test_unknown_game_is_404(client):
    assert client.get("/api/games/42").status_code == 404
    assert client.patch("/api/games/42", json={}).status_code == 404
