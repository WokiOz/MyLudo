import re
import unicodedata
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Game, GameTag, NoteEntry, Tag
from app.schemas import (
    ExtensionOut,
    GameBase,
    GameDetail,
    GameSummary,
    NoteOut,
    RuleSheetMeta,
    TagOut,
    VideoOut,
)
from app.services.tags import KIND_ORDER, derive_tags, get_or_create_tag, sync_auto_tags

GAME_FIELDS = tuple(GameBase.model_fields)


def normalize(text: str) -> str:
    """Minuscules, sans accents ni ponctuation : sert à la recherche et au tri."""
    text = unicodedata.normalize("NFKD", text.replace("’", "'"))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = text.replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _check_base_game(db: Session, base_game_id: int | None, own_id: int | None) -> None:
    if base_game_id is None:
        return
    if base_game_id == own_id:
        raise HTTPException(422, "Un jeu ne peut pas être sa propre extension.")
    if db.get(Game, base_game_id) is None:
        raise HTTPException(422, "Le jeu de base indiqué n'existe pas.")


def _check_unique_bgg(db: Session, bgg_id: int | None, own_id: int | None) -> None:
    if bgg_id is None:
        return
    other = db.scalar(select(Game.id).where(Game.bgg_id == bgg_id))
    if other is not None and other != own_id:
        raise HTTPException(409, "Ce jeu BoardGameGeek est déjà dans la ludothèque.")


def _refresh(game: Game, db: Session, bgg_tags: list[tuple[str, str]] | None) -> None:
    game.search_text = normalize(f"{game.name_fr} {game.name_original or ''}")
    db.flush()
    sync_auto_tags(db, game, derive_tags(game))
    if bgg_tags is not None:
        sync_auto_tags(db, game, bgg_tags, kinds=("style", "mechanic"))


def create_game(db: Session, data: GameBase, bgg_tags: list[tuple[str, str]] | None = None) -> Game:
    _check_base_game(db, data.base_game_id, None)
    _check_unique_bgg(db, data.bgg_id, None)
    game = Game(**data.model_dump())
    db.add(game)
    _refresh(game, db, bgg_tags)
    return game


def update_game(db: Session, game: Game, patch: dict[str, Any]) -> Game:
    """Applique une modification partielle, validée sur la fiche complète."""
    unknown = set(patch) - set(GAME_FIELDS)
    if unknown:
        raise HTTPException(422, f"Champs inconnus : {', '.join(sorted(unknown))}.")
    merged = {name: getattr(game, name) for name in GAME_FIELDS} | patch
    from pydantic import ValidationError

    try:
        data = GameBase(**merged)
    except ValidationError as error:
        first = error.errors()[0]
        field = ".".join(str(p) for p in first["loc"]) or "fiche"
        raise HTTPException(422, f"Valeur invalide pour « {field} » : {first['msg']}") from error
    _check_base_game(db, data.base_game_id, game.id)
    _check_unique_bgg(db, data.bgg_id, game.id)
    for name in GAME_FIELDS:
        setattr(game, name, getattr(data, name))
    _refresh(game, db, None)
    return game


def tag_out(link: GameTag) -> TagOut:
    return TagOut(id=link.tag.id, kind=link.tag.kind, label=link.tag.label, source=link.source)


def _sorted_tags(game: Game) -> list[TagOut]:
    links = sorted(
        game.tag_links,
        key=lambda link: (KIND_ORDER.index(link.tag.kind), link.tag.label),
    )
    return [tag_out(link) for link in links]


def summary(game: Game) -> GameSummary:
    return GameSummary(
        id=game.id,
        name_fr=game.name_fr,
        year=game.year,
        image_url=game.image_url,
        min_players=game.min_players,
        max_players=game.max_players,
        min_time=game.min_time,
        max_time=game.max_time,
        weight=game.weight,
        rating=game.rating,
        status=game.status,
        base_game_id=game.base_game_id,
        tags=_sorted_tags(game),
    )


def detail(db: Session, game: Game) -> GameDetail:
    extensions = db.execute(
        select(Game.id, Game.name_fr).where(Game.base_game_id == game.id).order_by(Game.search_text)
    ).all()
    fields = {name: getattr(game, name) for name in GAME_FIELDS}
    return GameDetail(
        **fields,
        id=game.id,
        created_at=game.created_at,
        updated_at=game.updated_at,
        tags=_sorted_tags(game),
        notes=[NoteOut.model_validate(n, from_attributes=True) for n in game.notes],
        extensions=[ExtensionOut(id=i, name_fr=n) for i, n in extensions],
        videos=[VideoOut.model_validate(v, from_attributes=True) for v in game.videos],
        rules=[
            RuleSheetMeta(kind=r.kind, origin=r.origin, reviewed=r.reviewed)
            for r in game.rule_sheets
        ],
    )


def search_games(
    db: Session,
    *,
    q: str | None = None,
    status: list[str] | None = None,
    players: int | None = None,
    max_time: int | None = None,
    tag_ids: list[int] | None = None,
    min_rating: int | None = None,
    sort: str = "name",
) -> list[Game]:
    stmt = select(Game).options(selectinload(Game.tag_links).joinedload(GameTag.tag))
    for token in normalize(q or "").split():
        stmt = stmt.where(Game.search_text.contains(token, autoescape=True))
    if status:
        stmt = stmt.where(Game.status.in_(status))
    if players:
        stmt = stmt.where(
            func.coalesce(Game.min_players, Game.max_players) <= players,
            func.coalesce(Game.max_players, Game.min_players) >= players,
        )
    if max_time:
        stmt = stmt.where(func.coalesce(Game.max_time, Game.min_time) <= max_time)
    for tag_id in tag_ids or []:
        stmt = stmt.where(Game.tag_links.any(GameTag.tag_id == tag_id))
    if min_rating:
        stmt = stmt.where(Game.rating >= min_rating)

    order = {
        "name": [Game.search_text],
        "rating": [Game.rating.desc().nulls_last(), Game.search_text],
        "recent": [Game.id.desc()],
        "price": [Game.purchase_price_cents.desc().nulls_last(), Game.search_text],
    }.get(sort, [Game.search_text])
    return list(db.scalars(stmt.order_by(*order)))


def find_by_name(db: Session, name: str) -> Game | None:
    """Jeu dont le nom français est identique, sans tenir compte des accents ni de la casse."""
    wanted = normalize(name)
    for game in db.scalars(select(Game).order_by(Game.id)):
        if normalize(game.name_fr) == wanted:
            return game
    return None


def get_game_or_404(db: Session, game_id: int) -> Game:
    game = db.get(Game, game_id)
    if game is None:
        raise HTTPException(404, "Jeu introuvable.")
    return game


def add_custom_tag(db: Session, game: Game, label: str) -> None:
    label = " ".join(label.split())
    if not label:
        raise HTTPException(422, "Le tag est vide.")
    existing = db.scalar(
        select(Tag).where(Tag.kind == "custom", func.lower(Tag.label) == label.lower())
    )
    tag = existing or get_or_create_tag(db, "custom", label)
    if any(link.tag_id == tag.id for link in game.tag_links):
        return
    game.tag_links.append(GameTag(tag=tag, source="user"))
    db.flush()


def remove_tag(db: Session, game: Game, tag_id: int) -> None:
    link = next((link for link in game.tag_links if link.tag_id == tag_id), None)
    if link is None:
        raise HTTPException(404, "Tag introuvable sur ce jeu.")
    if link.source == "auto":
        raise HTTPException(
            409, "Ce tag est calculé automatiquement, modifie plutôt la fiche du jeu."
        )
    game.tag_links.remove(link)
    db.flush()


def delete_unused_tags(db: Session) -> None:
    used = select(GameTag.tag_id)
    for tag in db.scalars(select(Tag).where(Tag.id.not_in(used))):
        db.delete(tag)


def add_note(db: Session, game: Game, kind: str, text: str) -> NoteEntry:
    note = NoteEntry(game_id=game.id, kind=kind, text=text.strip())
    db.add(note)
    db.flush()
    return note
