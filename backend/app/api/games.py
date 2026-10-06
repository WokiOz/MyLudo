from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.models import GameTag, NoteEntry, Tag
from app.schemas import (
    CustomTagIn,
    GameBase,
    GameDetail,
    GameSummary,
    NoteIn,
    NoteOut,
    TagCount,
)
from app.services import games as service
from app.services.tags import KIND_ORDER

router = APIRouter(prefix="/api", tags=["jeux"], dependencies=[Depends(require_auth)])
Db = Annotated[Session, Depends(get_db)]


@router.get("/games")
def list_games(
    db: Db,
    q: str | None = None,
    status: Annotated[list[str] | None, Query()] = None,
    players: Annotated[int | None, Query(ge=1)] = None,
    max_time: Annotated[int | None, Query(ge=1)] = None,
    tag_ids: Annotated[list[int] | None, Query()] = None,
    min_rating: Annotated[int | None, Query(ge=1, le=10)] = None,
    sort: str = "name",
) -> list[GameSummary]:
    games = service.search_games(
        db,
        q=q,
        status=status,
        players=players,
        max_time=max_time,
        tag_ids=tag_ids,
        min_rating=min_rating,
        sort=sort,
    )
    return [service.summary(g) for g in games]


@router.post("/games", status_code=201)
def create_game(body: GameBase, db: Db) -> GameDetail:
    game = service.create_game(db, body)
    db.commit()
    return service.detail(db, game)


@router.get("/games/{game_id}")
def read_game(game_id: int, db: Db) -> GameDetail:
    return service.detail(db, service.get_game_or_404(db, game_id))


@router.patch("/games/{game_id}")
def update_game(game_id: int, db: Db, patch: Annotated[dict[str, Any], Body()]) -> GameDetail:
    game = service.update_game(db, service.get_game_or_404(db, game_id), patch)
    db.commit()
    return service.detail(db, game)


@router.delete("/games/{game_id}", status_code=204)
def delete_game(game_id: int, db: Db) -> Response:
    db.delete(service.get_game_or_404(db, game_id))
    db.flush()
    service.delete_unused_tags(db)
    db.commit()
    return Response(status_code=204)


@router.get("/tags")
def list_tags(db: Db) -> list[TagCount]:
    rows = db.execute(
        select(Tag, func.count(GameTag.game_id))
        .join(GameTag, GameTag.tag_id == Tag.id)
        .group_by(Tag.id)
    ).all()
    rows.sort(key=lambda r: (KIND_ORDER.index(r[0].kind), r[0].label))
    return [TagCount(id=t.id, kind=t.kind, label=t.label, count=n) for t, n in rows]


@router.post("/games/{game_id}/tags", status_code=201)
def add_tag(game_id: int, body: CustomTagIn, db: Db) -> GameDetail:
    game = service.get_game_or_404(db, game_id)
    service.add_custom_tag(db, game, body.label)
    db.commit()
    return service.detail(db, game)


@router.delete("/games/{game_id}/tags/{tag_id}")
def remove_tag(game_id: int, tag_id: int, db: Db) -> GameDetail:
    game = service.get_game_or_404(db, game_id)
    service.remove_tag(db, game, tag_id)
    service.delete_unused_tags(db)
    db.commit()
    return service.detail(db, game)


@router.post("/games/{game_id}/notes", status_code=201)
def add_note(game_id: int, body: NoteIn, db: Db) -> NoteOut:
    game = service.get_game_or_404(db, game_id)
    note = service.add_note(db, game, body.kind, body.text)
    db.commit()
    return NoteOut.model_validate(note, from_attributes=True)


def _note_or_404(db: Session, note_id: int) -> NoteEntry:
    note = db.get(NoteEntry, note_id)
    if note is None:
        raise HTTPException(404, "Note introuvable.")
    return note


@router.patch("/notes/{note_id}")
def update_note(note_id: int, body: NoteIn, db: Db) -> NoteOut:
    note = _note_or_404(db, note_id)
    note.kind, note.text = body.kind, body.text.strip()
    db.commit()
    return NoteOut.model_validate(note, from_attributes=True)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Db) -> Response:
    db.delete(_note_or_404(db, note_id))
    db.commit()
    return Response(status_code=204)
