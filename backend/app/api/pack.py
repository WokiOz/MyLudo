from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.db import get_db
from app.services import packs

router = APIRouter(prefix="/api/pack", tags=["paquet"], dependencies=[Depends(require_auth)])
Db = Annotated[Session, Depends(get_db)]


@router.get("")
def preview(db: Db) -> dict:
    """Jeux du paquet présents dans la ludothèque et ce qui leur serait ajouté."""
    return packs.preview(db)


@router.post("/apply")
def apply(db: Db) -> dict:
    return packs.apply(db)
