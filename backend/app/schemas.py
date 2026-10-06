from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Status = Literal["owned", "lent", "wishlist", "sold"]
Condition = Literal["new", "very_good", "good", "worn"]
NoteKind = Literal["forgotten_rule", "common_mistake", "strategy", "house_rule"]
RuleKind = Literal["summary", "beginner_guide"]


class GameBase(BaseModel):
    """Champs modifiables d'un jeu."""

    name_fr: str = Field(min_length=1, max_length=200)
    name_original: str | None = Field(default=None, max_length=200)
    bgg_id: int | None = None
    year: int | None = Field(default=None, ge=1, le=2100)
    publisher: str | None = Field(default=None, max_length=200)
    description: str | None = None
    image_url: str | None = None
    ean: str | None = Field(default=None, max_length=32)
    min_players: int | None = Field(default=None, ge=1, le=99)
    max_players: int | None = Field(default=None, ge=1, le=99)
    best_players: str | None = Field(default=None, max_length=40)
    min_time: int | None = Field(default=None, ge=1, le=10000)
    max_time: int | None = Field(default=None, ge=1, le=10000)
    min_age: int | None = Field(default=None, ge=0, le=99)
    weight: float | None = Field(default=None, ge=0, le=5)
    bgg_rating: float | None = Field(default=None, ge=0, le=10)
    base_game_id: int | None = None
    status: Status = "owned"
    lent_to: str | None = Field(default=None, max_length=100)
    lent_since: date | None = None
    condition: Condition | None = None
    purchase_price_cents: int | None = Field(default=None, ge=0)
    purchase_date: date | None = None
    purchase_place: str | None = Field(default=None, max_length=100)
    storage_location: str | None = Field(default=None, max_length=100)
    rating: int | None = Field(default=None, ge=1, le=10)
    comment: str | None = None

    @model_validator(mode="after")
    def _ranges(self):
        if self.min_players and self.max_players and self.min_players > self.max_players:
            raise ValueError("Le nombre minimum de joueurs dépasse le maximum.")
        if self.min_time and self.max_time and self.min_time > self.max_time:
            raise ValueError("La durée minimale dépasse la durée maximale.")
        return self


class TagOut(BaseModel):
    id: int
    kind: str
    label: str
    source: str | None = None


class TagCount(TagOut):
    count: int


class GameSummary(BaseModel):
    id: int
    name_fr: str
    year: int | None
    image_url: str | None
    min_players: int | None
    max_players: int | None
    min_time: int | None
    max_time: int | None
    weight: float | None
    rating: int | None
    status: str
    base_game_id: int | None
    tags: list[TagOut]


class NoteOut(BaseModel):
    id: int
    game_id: int
    kind: str
    text: str
    created_at: datetime


class NoteIn(BaseModel):
    kind: NoteKind
    text: str = Field(min_length=1, max_length=5000)


class ExtensionOut(BaseModel):
    id: int
    name_fr: str


class VideoOut(BaseModel):
    id: int
    youtube_id: str
    title: str
    channel: str | None
    language: str | None
    source: str
    added_at: datetime


class VideoAddIn(BaseModel):
    url: str = Field(min_length=1, max_length=300)
    title: str | None = Field(default=None, max_length=300)


class VideoPickIn(BaseModel):
    youtube_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    title: str = Field(min_length=1, max_length=300)
    channel: str | None = Field(default=None, max_length=200)
    language: str | None = Field(default=None, max_length=8)


class VideoSuggestion(BaseModel):
    youtube_id: str
    title: str
    channel: str | None
    language: str | None
    duration_seconds: int | None
    priority: bool
    already_added: bool


class RuleSheetIn(BaseModel):
    content_md: str = Field(max_length=20000)
    origin: Literal["manual", "ai_draft"] = "manual"
    reviewed: bool = True


class RuleSheetOut(BaseModel):
    kind: RuleKind
    content_md: str
    origin: str
    reviewed: bool
    updated_at: datetime


class RuleSheetMeta(BaseModel):
    kind: RuleKind
    origin: str
    reviewed: bool


class RuleDraftOut(BaseModel):
    content_md: str


class GameDetail(GameBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut]
    notes: list[NoteOut]
    extensions: list[ExtensionOut]
    videos: list[VideoOut]
    rules: list[RuleSheetMeta]


class CustomTagIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)


class BggImportIn(BaseModel):
    bgg_id: int
    status: Status = "owned"


class BggSearchHit(BaseModel):
    bgg_id: int
    name: str
    year: int | None
    is_expansion: bool
    game_id: int | None = None
