"""Client minimal de l'API XML 2 de BoardGameGeek."""

import time
from dataclasses import dataclass, field

import httpx
from defusedxml import ElementTree

BASE_URL = "https://boardgamegeek.com/xmlapi2"


class BggError(Exception):
    """Erreur de BoardGameGeek, avec un message prêt à afficher."""


@dataclass
class BggHit:
    bgg_id: int
    name: str
    year: int | None
    is_expansion: bool


@dataclass
class BggGame:
    bgg_id: int
    name: str
    year: int | None = None
    image_url: str | None = None
    publisher: str | None = None
    min_players: int | None = None
    max_players: int | None = None
    best_players: str | None = None
    min_time: int | None = None
    max_time: int | None = None
    min_age: int | None = None
    weight: float | None = None
    rating: float | None = None
    is_expansion: bool = False
    base_bgg_ids: list[int] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    mechanics: list[str] = field(default_factory=list)


def _int(value: str | None) -> int | None:
    try:
        number = int(float(value or ""))
    except ValueError:
        return None
    return number or None


def _float(value: str | None) -> float | None:
    try:
        number = float(value or "")
    except ValueError:
        return None
    return round(number, 2) or None


def _value(item, tag: str) -> str | None:
    node = item.find(tag)
    return node.get("value") if node is not None else None


def parse_search(xml: str) -> list[BggHit]:
    hits = []
    for item in ElementTree.fromstring(xml).findall("item"):
        name = item.find("name")
        if name is None or not item.get("id"):
            continue
        hits.append(
            BggHit(
                bgg_id=int(item.get("id")),
                name=name.get("value", ""),
                year=_int(_value(item, "yearpublished")),
                is_expansion=item.get("type") == "boardgameexpansion",
            )
        )
    return hits


def _best_players(item) -> str | None:
    poll = next((p for p in item.findall("poll") if p.get("name") == "suggested_numplayers"), None)
    if poll is None:
        return None
    best: list[str] = []
    for block in poll.findall("results"):
        count = block.get("numplayers", "")
        if not count.isdigit():
            continue
        votes = {r.get("value"): int(r.get("numvotes", "0")) for r in block.findall("result")}
        if votes.get("Best", 0) > max(votes.get("Recommended", 0), votes.get("Not Recommended", 0)):
            best.append(count)
    return ",".join(best) or None


def parse_thing(xml: str) -> BggGame:
    item = ElementTree.fromstring(xml).find("item")
    if item is None:
        raise BggError("Jeu introuvable sur BoardGameGeek.")
    names = item.findall("name")
    primary = next((n for n in names if n.get("type") == "primary"), names[0] if names else None)
    if primary is None:
        raise BggError("Fiche BoardGameGeek sans nom.")

    game = BggGame(
        bgg_id=int(item.get("id")),
        name=primary.get("value", ""),
        year=_int(_value(item, "yearpublished")),
        image_url=(item.findtext("image") or "").strip() or None,
        min_players=_int(_value(item, "minplayers")),
        max_players=_int(_value(item, "maxplayers")),
        best_players=_best_players(item),
        min_time=_int(_value(item, "minplaytime")) or _int(_value(item, "playingtime")),
        max_time=_int(_value(item, "maxplaytime")) or _int(_value(item, "playingtime")),
        min_age=_int(_value(item, "minage")),
        weight=_float(_value(item.find("statistics/ratings"), "averageweight"))
        if item.find("statistics/ratings") is not None
        else None,
        rating=_float(_value(item.find("statistics/ratings"), "average"))
        if item.find("statistics/ratings") is not None
        else None,
        is_expansion=item.get("type") == "boardgameexpansion",
    )
    for link in item.findall("link"):
        kind, value = link.get("type"), link.get("value", "")
        if kind == "boardgamecategory":
            game.categories.append(value)
        elif kind == "boardgamemechanic":
            game.mechanics.append(value)
        elif kind == "boardgamepublisher" and game.publisher is None:
            game.publisher = value
        elif kind == "boardgameexpansion" and link.get("inbound") == "true":
            game.base_bgg_ids.append(int(link.get("id")))
    return game


class BggClient:
    def __init__(
        self,
        token: str,
        transport: httpx.BaseTransport | None = None,
        retry_delay: float = 1.5,
    ):
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
            transport=transport,
        )
        self._retry_delay = retry_delay

    def _get(self, path: str, params: dict) -> str:
        for attempt in range(4):
            try:
                response = self._client.get(path, params=params)
            except httpx.HTTPError as error:
                raise BggError("BoardGameGeek ne répond pas, réessaie plus tard.") from error
            if response.status_code == 202 and attempt < 3:
                time.sleep(self._retry_delay)  # BGG prépare la réponse
                continue
            if response.status_code in (401, 403):
                raise BggError("BoardGameGeek refuse le jeton : vérifie BGG_TOKEN.")
            if response.status_code == 429:
                raise BggError("BoardGameGeek limite les requêtes, réessaie dans une minute.")
            if response.status_code != 200:
                raise BggError(f"BoardGameGeek a répondu une erreur ({response.status_code}).")
            return response.text
        raise BggError("BoardGameGeek met trop de temps à répondre.")

    def search(self, query: str) -> list[BggHit]:
        xml = self._get("/search", {"query": query, "type": "boardgame,boardgameexpansion"})
        hits = parse_search(xml)
        query_lower = query.casefold()
        hits.sort(key=lambda h: (h.name.casefold() != query_lower, h.is_expansion))
        return hits[:25]

    def fetch(self, bgg_id: int) -> BggGame:
        xml = self._get("/thing", {"id": bgg_id, "stats": 1})
        return parse_thing(xml)
