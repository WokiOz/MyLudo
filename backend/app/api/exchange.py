import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.services import exchange

router = APIRouter(prefix="/api", tags=["import et export"], dependencies=[Depends(require_auth)])
Db = Annotated[Session, Depends(get_db)]
MAX_BODY = 5_000_000


async def _body_text(request: Request) -> str:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "Fichier trop volumineux (5 Mo maximum).")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(422, "Le fichier doit être encodé en UTF-8.") from error


@router.get("/export/games.json")
def export_json(db: Db) -> Response:
    content = json.dumps(exchange.export_json(db), ensure_ascii=False, indent=2)
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="myludo.json"'},
    )


@router.get("/export/games.csv")
def export_csv(db: Db) -> Response:
    return Response(
        "﻿" + exchange.export_csv(db),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="myludo.csv"'},
    )


@router.post("/import/json")
async def import_json(request: Request, db: Db) -> dict:
    text = await _body_text(request)
    try:
        payload = exchange.ImportFile.model_validate_json(text)
    except ValidationError as error:
        raise HTTPException(422, "Fichier JSON invalide : format MyLudo attendu.") from error
    return exchange.import_json(db, payload)


@router.post("/import/csv")
async def import_csv(request: Request, db: Db) -> dict:
    return exchange.import_csv(db, await _body_text(request))
