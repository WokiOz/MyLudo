from app.models import Game
from app.services.tags import bgg_tags, derive_tags, difficulty_label, duration_label


def labels(game: Game) -> set[tuple[str, str]]:
    return set(derive_tags(game))


def test_difficulty_levels():
    assert [difficulty_label(w) for w in (1.0, 1.8, 2.6, 3.8)] == [
        "Très facile",
        "Facile",
        "Moyen",
        "Expert",
    ]


def test_duration_levels():
    assert [duration_label(m) for m in (15, 30, 60, 90, 180)] == [
        "Moins de 30 min",
        "30–60 min",
        "30–60 min",
        "1–2 h",
        "Plus de 2 h",
    ]


def test_players_tags():
    game = Game(min_players=1, max_players=5, best_players="2,4")
    tags = labels(game)
    assert ("players", "Solo") in tags
    assert ("players", "2 joueurs") in tags
    assert ("players", "3–4 joueurs") in tags
    assert ("players", "5 joueurs et plus") in tags
    assert ("players", "Idéal à 4") in tags


def test_two_players_only_game():
    tags = labels(Game(min_players=2, max_players=2))
    assert ("players", "2 joueurs") in tags
    assert not any(label == "3–4 joueurs" for _, label in tags)


def test_audience_tags():
    kids = labels(Game(weight=1.2, min_age=6))
    assert ("audience", "Enfants") in kids and ("audience", "Famille") in kids
    assert ("audience", "Joueurs experts") in labels(Game(weight=4.1, min_age=14))
    assert ("audience", "Joueurs initiés") in labels(Game(weight=3.0, min_age=12))


def test_unknown_data_gives_no_tags():
    assert derive_tags(Game()) == []


def test_bgg_mapping_in_french():
    tags = bgg_tags(["Negotiation", "Truc inconnu"], ["Cooperative Game", "Trading", "Autre"])
    assert tags == [
        ("style", "Négociation"),
        ("style", "Coopératif"),
        ("mechanic", "Échanges"),
    ]
