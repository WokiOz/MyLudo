"""Paquet de règles et de vidéos livré avec l'appli.

Le paquet ne crée aucun jeu : il complète seulement ceux déjà présents dans la ludothèque,
sans jamais écraser ce que l'utilisateur a écrit.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Game, RuleSheet, Video
from app.schemas import RuleKind
from app.services.games import normalize

PACK_FILE = Path(__file__).resolve().parent.parent / "content" / "rules_pack.json"


class PackVideo(BaseModel):
    youtube_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    title: str = Field(min_length=1, max_length=300)
    channel: str | None = None


class PackGame(BaseModel):
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    videos: list[PackVideo] = Field(default_factory=list)
    summary: str | None = None
    beginner_guide: str | None = None

    def sheets(self) -> dict[RuleKind, str]:
        found = {"summary": self.summary, "beginner_guide": self.beginner_guide}
        return {kind: text for kind, text in found.items() if text}


class Pack(BaseModel):
    version: int = 1
    games: list[PackGame]


@lru_cache
def load_pack() -> Pack:
    return Pack.model_validate(json.loads(PACK_FILE.read_text(encoding="utf-8")))


def _owned_by_name(db: Session) -> dict[str, Game]:
    """Jeux de la ludothèque, retrouvés par nom français ou nom d'origine."""
    index: dict[str, Game] = {}
    for game in db.scalars(select(Game).where(Game.status != "sold").order_by(Game.id)):
        for name in (game.name_fr, game.name_original):
            if name:
                index.setdefault(normalize(name), game)
    return index


def _match(entry: PackGame, index: dict[str, Game]) -> Game | None:
    for name in (entry.name, *entry.aliases):
        game = index.get(normalize(name))
        if game is not None:
            return game
    return None


def _missing(entry: PackGame, game: Game) -> tuple[list[PackVideo], list[RuleKind]]:
    known = {v.youtube_id for v in game.videos}
    have = {s.kind for s in game.rule_sheets}
    videos = [v for v in entry.videos if v.youtube_id not in known]
    kinds = [kind for kind in entry.sheets() if kind not in have]
    return videos, kinds


def preview(db: Session) -> dict:
    pack, index = load_pack(), _owned_by_name(db)
    entries = []
    for entry in pack.games:
        game = _match(entry, index)
        new_videos, new_kinds = _missing(entry, game) if game else ([], [])
        entries.append(
            {
                "name": entry.name,
                "game_id": game.id if game else None,
                "game_name": game.name_fr if game else None,
                "new_videos": len(new_videos),
                "new_sheets": len(new_kinds),
            }
        )
    in_collection = [e for e in entries if e["game_id"] is not None]
    return {
        "total": len(entries),
        "in_collection": len(in_collection),
        "to_add": sum(1 for e in in_collection if e["new_videos"] or e["new_sheets"]),
        "games": entries,
    }


def apply(db: Session) -> dict:
    """Ajoute les vidéos et fiches manquantes. Les fiches arrivent comme brouillons à relire."""
    pack, index = load_pack(), _owned_by_name(db)
    games, videos_added, sheets_added = set(), 0, 0
    for entry in pack.games:
        game = _match(entry, index)
        if game is None:
            continue
        new_videos, new_kinds = _missing(entry, game)
        for video in new_videos:
            game.videos.append(
                Video(
                    youtube_id=video.youtube_id,
                    title=video.title,
                    channel=video.channel,
                    language="fr",
                    source="auto",
                )
            )
        for kind in new_kinds:
            game.rule_sheets.append(
                RuleSheet(
                    kind=kind, content_md=entry.sheets()[kind], origin="ai_draft", reviewed=False
                )
            )
        if new_videos or new_kinds:
            games.add(game.id)
            videos_added += len(new_videos)
            sheets_added += len(new_kinds)
    db.commit()
    return {"games": len(games), "videos_added": videos_added, "sheets_added": sheets_added}
