"""Import et export de la collection (JSON complet, CSV simplifié)."""

import csv
import io
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Game
from app.schemas import GameBase, NoteIn
from app.services import games as service

EXPORTED_TAG_KINDS = ("style", "mechanic", "custom")

CSV_COLUMNS = [
    "name_fr", "name_original", "year", "publisher", "ean", "min_players", "max_players",
    "min_time", "max_time", "min_age", "weight", "status", "condition", "purchase_price_eur",
    "purchase_date", "purchase_place", "storage_location", "rating", "comment", "tags",
]  # fmt: skip
CSV_ALIASES = {
    "nom": "name_fr",
    "name": "name_fr",
    "titre": "name_fr",
    "prix": "purchase_price_eur",
}
INT_FIELDS = {"year", "min_players", "max_players", "min_time", "max_time", "min_age", "rating"}


class ImportTag(BaseModel):
    kind: str
    label: str
    source: str = "user"


class ImportGame(GameBase):
    base_game_name: str | None = None
    tags: list[ImportTag] = Field(default_factory=list)
    notes: list[NoteIn] = Field(default_factory=list)


class ImportFile(BaseModel):
    version: int = 1
    games: list[ImportGame]


def export_json(db: Session) -> dict:
    games = service.search_games(db)
    names = {g.id: g.name_fr for g in games}
    out = []
    for game in games:
        data = GameBase.model_validate(game, from_attributes=True).model_dump(mode="json")
        data.pop("base_game_id")
        data["base_game_name"] = names.get(game.base_game_id)
        data["tags"] = [
            {"kind": link.tag.kind, "label": link.tag.label, "source": link.source}
            for link in game.tag_links
            if link.tag.kind in EXPORTED_TAG_KINDS
        ]
        data["notes"] = [{"kind": n.kind, "text": n.text} for n in game.notes]
        out.append(data)
    return {"version": 1, "games": out}


def export_csv(db: Session) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for game in service.search_games(db):
        cents = game.purchase_price_cents
        values = {
            "purchase_price_eur": f"{cents / 100:.2f}".replace(".", ",")
            if cents is not None
            else "",
            "tags": "|".join(
                link.tag.label for link in game.tag_links if link.tag.kind == "custom"
            ),
        }
        row = []
        for column in CSV_COLUMNS:
            value = values.get(column, getattr(game, column, None))
            row.append(
                ""
                if value is None
                else str(value).replace(".", ",")
                if column == "weight"
                else value
            )
        writer.writerow(row)
    return buffer.getvalue()


def _find_existing(db: Session, data: GameBase) -> Game | None:
    if data.bgg_id is not None:
        found = db.scalar(select(Game).where(Game.bgg_id == data.bgg_id))
        if found:
            return found
    return service.find_by_name(db, data.name_fr)


def import_json(db: Session, payload: ImportFile) -> dict:
    created, skipped = 0, 0
    pending_bases: list[tuple[Game, str]] = []
    for item in payload.games:
        fields = item.model_dump(include=set(GameBase.model_fields))
        fields["base_game_id"] = None
        data = GameBase(**fields)
        if _find_existing(db, data) is not None:
            skipped += 1
            continue
        auto = [(t.kind, t.label) for t in item.tags if t.kind in ("style", "mechanic")]
        game = service.create_game(db, data, auto or None)
        for tag in item.tags:
            if tag.kind == "custom":
                service.add_custom_tag(db, game, tag.label)
        for note in item.notes:
            service.add_note(db, game, note.kind, note.text)
        if item.base_game_name:
            pending_bases.append((game, item.base_game_name))
        created += 1
    for game, base_name in pending_bases:
        base = service.find_by_name(db, base_name)
        if base is not None and base.id != game.id:
            game.base_game_id = base.id
    db.commit()
    return {"created": created, "skipped": skipped, "errors": []}


def _convert(field: str, raw: str):
    raw = raw.strip()
    if field in INT_FIELDS:
        return int(float(raw.replace(",", ".")))
    if field == "weight":
        return float(raw.replace(",", "."))
    if field == "purchase_price_eur":
        return int(
            (Decimal(raw.replace(",", ".").replace("€", "").strip()) * 100).to_integral_value()
        )
    return raw


def _csv_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        first = error.errors()[0]
        if first["loc"]:
            return f"Valeur invalide ({first['loc'][0]})."
        return first["msg"].removeprefix("Value error, ")
    return "Valeur invalide."


def import_csv(db: Session, text: str) -> dict:
    text = text.lstrip("﻿")
    header = text.splitlines()[0] if text.strip() else ""
    delimiter = ";" if header.count(";") >= header.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        return {"created": 0, "skipped": 0, "errors": [{"line": 1, "message": "Fichier vide."}]}
    columns = {
        name: CSV_ALIASES.get(name.strip().lower(), name.strip().lower())
        for name in reader.fieldnames
        if name
    }
    if "name_fr" not in columns.values():
        message = "Colonne « name_fr » (ou « nom ») manquante."
        return {"created": 0, "skipped": 0, "errors": [{"line": 1, "message": message}]}

    created, skipped, errors = 0, 0, []
    for row in reader:
        line = reader.line_num
        values = {columns[k]: v for k, v in row.items() if k in columns and v and v.strip()}
        if not values:
            continue
        tags = values.pop("tags", "")
        try:
            fields = {}
            for name, raw in values.items():
                if name not in CSV_COLUMNS:
                    continue
                key = "purchase_price_cents" if name == "purchase_price_eur" else name
                fields[key] = _convert(name, raw)
            data = GameBase(**fields)
        except (ValueError, InvalidOperation, ValidationError) as error:
            errors.append({"line": line, "message": _csv_error(error)})
            continue
        if _find_existing(db, data) is not None:
            skipped += 1
            continue
        game = service.create_game(db, data)
        for label in tags.split("|"):
            if label.strip():
                service.add_custom_tag(db, game, label)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
