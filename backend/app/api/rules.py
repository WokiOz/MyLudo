from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import get_settings
from app.db import get_db
from app.integrations import claude
from app.models import RuleSheet
from app.schemas import RuleDraftOut, RuleKind, RuleSheetIn, RuleSheetOut
from app.services import games as service
from app.services.rule_templates import TEMPLATES

router = APIRouter(prefix="/api", tags=["règles"], dependencies=[Depends(require_auth)])
Db = Annotated[Session, Depends(get_db)]


def get_claude_client() -> anthropic.Anthropic:
    key = get_settings().anthropic_api_key
    if not key:
        raise HTTPException(
            503,
            "Claude n'est pas configuré. Ajoute ANTHROPIC_API_KEY ou rédige la fiche à la main.",
        )
    return anthropic.Anthropic(api_key=key, timeout=90)


@router.get("/rules/templates")
def templates() -> dict[str, str]:
    return TEMPLATES


@router.get("/games/{game_id}/rules")
def list_rules(game_id: int, db: Db) -> list[RuleSheetOut]:
    game = service.get_game_or_404(db, game_id)
    return [
        RuleSheetOut(
            kind=s.kind,
            content_md=s.content_md,
            origin=s.origin,
            reviewed=s.reviewed,
            updated_at=s.updated_at,
        )
        for s in game.rule_sheets
    ]


@router.put("/games/{game_id}/rules/{kind}")
def save_rule(game_id: int, kind: RuleKind, body: RuleSheetIn, db: Db) -> Response:
    """Crée ou remplace la fiche. Un contenu vide la supprime."""
    game = service.get_game_or_404(db, game_id)
    sheet = next((s for s in game.rule_sheets if s.kind == kind), None)
    content = body.content_md.strip()
    if not content:
        if sheet is not None:
            game.rule_sheets.remove(sheet)
            db.commit()
        return Response(status_code=204)
    if sheet is None:
        sheet = RuleSheet(game_id=game.id, kind=kind)
        game.rule_sheets.append(sheet)
    sheet.content_md = content
    sheet.origin = body.origin
    # Un brouillon généré ne passe en « relu » que si l'utilisateur le demande.
    sheet.reviewed = body.reviewed if body.origin == "ai_draft" else True
    db.commit()
    return Response(status_code=204)


@router.post("/games/{game_id}/rules/{kind}/draft")
def draft_rule(
    game_id: int,
    kind: RuleKind,
    db: Db,
    client: Annotated[anthropic.Anthropic, Depends(get_claude_client)],
) -> RuleDraftOut:
    """Génère un brouillon, sans l'enregistrer : l'utilisateur le relit avant de le sauvegarder."""
    from app.services.games import detail

    game = service.get_game_or_404(db, game_id)
    info = detail(db, game)
    facts = {
        "name_fr": info.name_fr,
        "name_original": info.name_original,
        "year": info.year,
        "publisher": info.publisher,
        "min_age": info.min_age,
        "players": _range(info.min_players, info.max_players, "joueurs"),
        "duration": _range(info.min_time, info.max_time, "min"),
    }
    notes = [n.text for n in info.notes]
    try:
        text = claude.draft(facts, notes, kind, client)
    except claude.ClaudeError as error:
        raise HTTPException(502, str(error)) from error
    return RuleDraftOut(content_md=text)


def _range(low: int | None, high: int | None, unit: str) -> str:
    if not low and not high:
        return ""
    if not low or not high or low == high:
        return f"{low or high} {unit}"
    return f"{low}–{high} {unit}"
