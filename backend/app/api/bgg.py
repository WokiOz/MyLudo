from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import get_settings
from app.db import get_db
from app.integrations.bgg import BggClient, BggError
from app.models import Game
from app.schemas import BggImportIn, BggSearchHit, GameBase, GameDetail
from app.services import games as service
from app.services.tags import bgg_tags

router = APIRouter(prefix="/api/bgg", tags=["BoardGameGeek"], dependencies=[Depends(require_auth)])
Db = Annotated[Session, Depends(get_db)]


def get_bgg_client() -> BggClient:
    token = get_settings().bgg_token
    if not token:
        raise HTTPException(
            503, "BoardGameGeek n'est pas configuré. Ajoute BGG_TOKEN ou saisis le jeu à la main."
        )
    return BggClient(token)


Client = Annotated[BggClient, Depends(get_bgg_client)]


def _bgg_call(func, *args):
    try:
        return func(*args)
    except BggError as error:
        raise HTTPException(502, str(error)) from error


@router.get("/search")
def search(client: Client, db: Db, q: Annotated[str, Query(min_length=2)]) -> list[BggSearchHit]:
    hits = _bgg_call(client.search, q)
    known = dict(db.execute(select(Game.bgg_id, Game.id).where(Game.bgg_id.is_not(None))).all())
    return [
        BggSearchHit(
            bgg_id=h.bgg_id,
            name=h.name,
            year=h.year,
            is_expansion=h.is_expansion,
            game_id=known.get(h.bgg_id),
        )
        for h in hits
    ]


@router.post("/import", status_code=201)
def import_game(body: BggImportIn, client: Client, db: Db) -> GameDetail:
    existing = db.scalar(select(Game).where(Game.bgg_id == body.bgg_id))
    if existing is not None:
        raise HTTPException(409, f"« {existing.name_fr} » est déjà dans la ludothèque.")
    found = _bgg_call(client.fetch, body.bgg_id)

    base_id = None
    if found.base_bgg_ids:
        base_id = db.scalar(select(Game.id).where(Game.bgg_id.in_(found.base_bgg_ids)))

    min_players, max_players = sorted(
        (found.min_players or found.max_players or 0, found.max_players or found.min_players or 0)
    )
    min_time, max_time = sorted(
        (found.min_time or found.max_time or 0, found.max_time or found.min_time or 0)
    )
    data = GameBase(
        name_fr=found.name,
        name_original=found.name,
        bgg_id=found.bgg_id,
        year=found.year,
        publisher=found.publisher,
        image_url=found.image_url,
        min_players=min_players or None,
        max_players=max_players or None,
        best_players=found.best_players,
        min_time=min_time or None,
        max_time=max_time or None,
        min_age=found.min_age,
        weight=found.weight,
        bgg_rating=found.rating,
        base_game_id=base_id,
        status=body.status,
    )
    game = service.create_game(db, data, bgg_tags(found.categories, found.mechanics))
    db.commit()
    return service.detail(db, game)
