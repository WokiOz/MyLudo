from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import get_settings
from app.db import get_db
from app.integrations.youtube import YouTubeClient, YouTubeError, parse_video_id
from app.models import Game, Video
from app.schemas import VideoAddIn, VideoOut, VideoPickIn, VideoSuggestion
from app.services import games as service

router = APIRouter(prefix="/api", tags=["vidéos"], dependencies=[Depends(require_auth)])
Db = Annotated[Session, Depends(get_db)]


def get_youtube_client() -> YouTubeClient:
    key = get_settings().youtube_api_key
    if not key:
        raise HTTPException(
            503, "YouTube n'est pas configuré. Ajoute YOUTUBE_API_KEY ou colle le lien à la main."
        )
    return YouTubeClient(key)


def get_optional_youtube_client() -> YouTubeClient | None:
    key = get_settings().youtube_api_key
    return YouTubeClient(key) if key else None


def _store(db: Session, game: Game, **fields) -> VideoOut:
    if any(v.youtube_id == fields["youtube_id"] for v in game.videos):
        raise HTTPException(409, "Cette vidéo est déjà sur la fiche.")
    video = Video(game_id=game.id, **fields)
    db.add(video)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Cette vidéo est déjà sur la fiche.") from error
    return VideoOut.model_validate(video, from_attributes=True)


@router.get("/games/{game_id}/videos/suggestions")
def suggestions(
    game_id: int, db: Db, client: Annotated[YouTubeClient, Depends(get_youtube_client)]
) -> list[VideoSuggestion]:
    game = service.get_game_or_404(db, game_id)
    try:
        found = client.suggest(game.name_fr, get_settings().youtube_channel_names)
    except YouTubeError as error:
        raise HTTPException(502, str(error)) from error
    known = {v.youtube_id for v in game.videos}
    return [
        VideoSuggestion(
            youtube_id=v.youtube_id,
            title=v.title,
            channel=v.channel,
            language=v.language,
            duration_seconds=v.duration_seconds,
            priority=v.priority,
            already_added=v.youtube_id in known,
        )
        for v in found
    ]


@router.post("/games/{game_id}/videos", status_code=201)
def add_video(
    game_id: int,
    body: VideoAddIn,
    db: Db,
    client: Annotated[YouTubeClient | None, Depends(get_optional_youtube_client)],
) -> VideoOut:
    """Ajoute un lien collé à la main. Titre et chaîne sont complétés si YouTube est configuré."""
    game = service.get_game_or_404(db, game_id)
    youtube_id = parse_video_id(body.url)
    if youtube_id is None:
        raise HTTPException(422, "Ce lien n'est pas une adresse de vidéo YouTube.")
    title, channel, language = (body.title or "").strip() or None, None, None
    if client is not None:
        try:
            info = next(iter(client.details([youtube_id])), None)
        except YouTubeError:
            info = None  # le lien reste utilisable sans ses informations
        if info is None and title is None:
            raise HTTPException(422, "YouTube ne connaît pas cette vidéo.")
        if info is not None:
            title, channel, language = title or info.title, info.channel, info.language
    return _store(
        db,
        game,
        youtube_id=youtube_id,
        title=title or "Vidéo YouTube",
        channel=channel,
        language=language,
        source="manual",
    )


@router.post("/games/{game_id}/videos/pick", status_code=201)
def pick_video(game_id: int, body: VideoPickIn, db: Db) -> VideoOut:
    """Valide une vidéo proposée par la recherche automatique."""
    game = service.get_game_or_404(db, game_id)
    return _store(
        db,
        game,
        youtube_id=body.youtube_id,
        title=body.title,
        channel=body.channel,
        language=body.language,
        source="auto",
    )


@router.delete("/videos/{video_id}", status_code=204)
def delete_video(video_id: int, db: Db) -> Response:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(404, "Vidéo introuvable.")
    db.delete(video)
    db.commit()
    return Response(status_code=204)
