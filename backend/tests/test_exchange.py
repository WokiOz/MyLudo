import json


def seed(client):
    client.post("/api/bgg/import", json={"bgg_id": 13})
    game = client.post(
        "/api/games",
        json={
            "name_fr": "Dixit",
            "min_players": 3,
            "max_players": 6,
            "weight": 1.2,
            "purchase_price_cents": 2490,
            "rating": 9,
            "comment": "Génial; vraiment",
        },
    ).json()
    client.post(f"/api/games/{game['id']}/tags", json={"label": "Soirée"})
    client.post(f"/api/games/{game['id']}/notes", json={"kind": "strategy", "text": "Sois vague"})
    client.post("/api/bgg/import", json={"bgg_id": 200})
    return game


def test_json_roundtrip(make_client):
    source = make_client()
    seed(source)
    exported = source.get("/api/export/games.json")
    assert "attachment" in exported.headers["content-disposition"]
    payload = exported.json()
    assert [g["name_fr"] for g in payload["games"]] == ["Catan", "Catan : Marins", "Dixit"]

    target = make_client()
    result = target.post("/api/import/json", content=exported.content).json()
    assert result == {"created": 3, "skipped": 0, "errors": []}

    games = {g["name_fr"]: g for g in target.get("/api/games").json()}
    dixit = target.get(f"/api/games/{games['Dixit']['id']}").json()
    assert dixit["rating"] == 9 and dixit["purchase_price_cents"] == 2490
    assert [n["text"] for n in dixit["notes"]] == ["Sois vague"]
    assert {"Soirée", "Famille", "3–4 joueurs"} <= {t["label"] for t in dixit["tags"]}
    catan = games["Catan"]
    assert "Négociation" in {t["label"] for t in catan["tags"]}
    extension = target.get(f"/api/games/{games['Catan : Marins']['id']}").json()
    assert extension["base_game_id"] == catan["id"]

    again = target.post("/api/import/json", content=exported.content).json()
    assert again["created"] == 0 and again["skipped"] == 3


def test_json_import_rejects_garbage(client):
    assert client.post("/api/import/json", content=b"pas du json").status_code == 422
    assert client.post("/api/import/json", content=json.dumps({"games": [{}]})).status_code == 422
    assert client.post("/api/import/json", content=b"\xff\xfe").status_code == 422


def test_csv_export_format(client):
    seed(client)
    response = client.get("/api/export/games.csv")
    assert response.content.startswith(b"\xef\xbb\xbf")
    lines = response.content.decode("utf-8-sig").splitlines()
    assert lines[0].startswith("name_fr;name_original;year")
    dixit = next(line for line in lines if line.startswith("Dixit"))
    assert "24,90" in dixit and "Soirée" in dixit


def test_csv_roundtrip(make_client):
    source = make_client()
    seed(source)
    exported = source.get("/api/export/games.csv").content

    target = make_client()
    result = target.post("/api/import/csv", content=exported).json()
    assert result == {"created": 3, "skipped": 0, "errors": []}
    dixit = next(g for g in target.get("/api/games").json() if g["name_fr"] == "Dixit")
    detail = target.get(f"/api/games/{dixit['id']}").json()
    assert detail["purchase_price_cents"] == 2490
    assert detail["comment"] == "Génial; vraiment"
    assert "Soirée" in {t["label"] for t in detail["tags"]}


def test_csv_import_handles_french_excel_and_errors(client):
    text = (
        "Nom;Joueurs mini;min_players;max_players;prix;weight;status\n"
        "Carcassonne;x;2;5;19,90 €;1,9;owned\n"
        ";;;;;;\n"
        "Cassé;;abc;;;;\n"
        "Trop;;5;2;;;\n"
        "Statut;;;;;;perdu\n"
    )
    result = client.post("/api/import/csv", content=text.encode()).json()
    assert result["created"] == 1
    assert [e["line"] for e in result["errors"]] == [4, 5, 6]
    game = client.get("/api/games").json()[0]
    detail = client.get(f"/api/games/{game['id']}").json()
    assert detail["purchase_price_cents"] == 1990 and detail["weight"] == 1.9


def test_csv_without_name_column(client):
    result = client.post("/api/import/csv", content=b"year;comment\n2020;x\n").json()
    assert result["created"] == 0 and "name_fr" in result["errors"][0]["message"]


def test_csv_with_comma_delimiter(client):
    result = client.post("/api/import/csv", content=b"name_fr,year\nTakenoko,2011\n").json()
    assert result["created"] == 1


def test_csv_duplicate_of_imported_game_is_skipped(client):
    client.post("/api/bgg/import", json={"bgg_id": 13})
    result = client.post("/api/import/csv", content=b"name_fr\ncatan\n").json()
    assert result["created"] == 0 and result["skipped"] == 1
