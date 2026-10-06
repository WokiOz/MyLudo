from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Game(Base):
    __tablename__ = "game"

    id: Mapped[int] = mapped_column(primary_key=True)
    bgg_id: Mapped[int | None] = mapped_column(unique=True)
    name_fr: Mapped[str] = mapped_column(String(200))
    name_original: Mapped[str | None] = mapped_column(String(200))
    # Noms normalisés (sans accents ni majuscules) pour la recherche et le tri.
    search_text: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None]
    publisher: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    ean: Mapped[str | None] = mapped_column(String(32), index=True)

    min_players: Mapped[int | None]
    max_players: Mapped[int | None]
    best_players: Mapped[str | None] = mapped_column(String(40))
    min_time: Mapped[int | None]
    max_time: Mapped[int | None]
    min_age: Mapped[int | None]
    weight: Mapped[float | None]
    bgg_rating: Mapped[float | None]

    base_game_id: Mapped[int | None] = mapped_column(ForeignKey("game.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="owned", index=True)
    lent_to: Mapped[str | None] = mapped_column(String(100))
    lent_since: Mapped[date | None] = mapped_column(Date)
    condition: Mapped[str | None] = mapped_column(String(16))
    purchase_price_cents: Mapped[int | None]
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_place: Mapped[str | None] = mapped_column(String(100))
    storage_location: Mapped[str | None] = mapped_column(String(100))

    rating: Mapped[int | None]
    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    tag_links: Mapped[list["GameTag"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    notes: Mapped[list["NoteEntry"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="NoteEntry.id"
    )
    videos: Mapped[list["Video"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="Video.id"
    )
    rule_sheets: Mapped[list["RuleSheet"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="RuleSheet.id"
    )


class Video(Base):
    __tablename__ = "video"
    __table_args__ = (UniqueConstraint("game_id", "youtube_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"), index=True)
    youtube_id: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(300))
    channel: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(8))
    # manual : lien collé par l'utilisateur, auto : proposition validée
    source: Mapped[str] = mapped_column(String(8), default="manual")
    validated: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    game: Mapped["Game"] = relationship(back_populates="videos")


class RuleSheet(Base):
    __tablename__ = "rule_sheet"
    __table_args__ = (UniqueConstraint("game_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"), index=True)
    # summary : règles simplifiées, beginner_guide : fiche pour débutants
    kind: Mapped[str] = mapped_column(String(16))
    content_md: Mapped[str] = mapped_column(Text)
    # manual : écrit par l'utilisateur, ai_draft : brouillon généré
    origin: Mapped[str] = mapped_column(String(8), default="manual")
    reviewed: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    game: Mapped["Game"] = relationship(back_populates="rule_sheets")


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("kind", "label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # style, difficulty, players, duration, audience, mechanic, custom
    kind: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(60))


class GameTag(Base):
    __tablename__ = "game_tag"
    __table_args__ = (Index("ix_game_tag_tag_id", "tag_id"),)

    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)
    # auto : recalculé automatiquement, user : posé par l'utilisateur
    source: Mapped[str] = mapped_column(String(8), default="user")

    game: Mapped[Game] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship()


class NoteEntry(Base):
    __tablename__ = "note_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"), index=True)
    # forgotten_rule, common_mistake, strategy, house_rule
    kind: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    game: Mapped[Game] = relationship(back_populates="notes")
