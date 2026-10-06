import re

import pytest

from app.services.packs import load_pack

REQUIRED_SUMMARY = [
    "## But du jeu",
    "## Mise en place",
    "## Fin de partie et décompte",
    "## À retenir",
]
REQUIRED_GUIDE = [
    "## Avant de commencer",
    "## Expliquer en 5 minutes",
    "## Aide-mémoire du tour",
    "## Erreurs classiques des nouveaux joueurs",
    "## Partie d'essai conseillée",
]


def test_pack_is_well_formed():
    pack = load_pack()
    assert len(pack.games) >= 25
    names = [g.name for g in pack.games]
    assert len(names) == len(set(names)), "nom en double"
    for game in pack.games:
        assert game.videos, f"{game.name} : aucune vidéo"
        assert len({v.youtube_id for v in game.videos}) == len(game.videos)
        assert game.summary and game.beginner_guide, f"{game.name} : fiche manquante"


@pytest.mark.parametrize("kind", ["summary", "beginner_guide"])
def test_every_sheet_has_its_sections_and_no_placeholder(kind):
    required = REQUIRED_SUMMARY if kind == "summary" else REQUIRED_GUIDE
    for game in load_pack().games:
        text = getattr(game, kind)
        for heading in required:
            assert heading in text, f"{game.name} ({kind}) : {heading} manquant"
        assert "…" not in text, f"{game.name} : texte à trous"
        assert "TODO" not in text.upper(), f"{game.name} : TODO"
        assert len(text) < 20000


def test_all_videos_come_from_ludovox_and_are_ludochrono():
    for game in load_pack().games:
        for video in game.videos:
            assert video.channel == "Ludovox", f"{game.name} : {video.channel}"
            assert re.search(r"ludochrono", video.title, re.IGNORECASE), (
                f"{game.name} : {video.title}"
            )


def test_pack_names_do_not_collide_after_normalization():
    from app.services.games import normalize

    seen: dict[str, str] = {}
    for game in load_pack().games:
        for name in (game.name, *game.aliases):
            key = normalize(name)
            assert seen.setdefault(key, game.name) == game.name, f"« {name} » vise deux jeux"
