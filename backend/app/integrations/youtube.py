"""Client minimal de l'API YouTube Data v3 : recherche de vidéos de règles en français."""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx

from app.services.games import normalize

BASE_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtube-nocookie.com",
    "youtube-nocookie.com",
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
STOP_WORDS = {"les", "des", "the", "and", "pour", "avec", "dans", "une", "jeu", "regles"}

# Identifiants de chaînes déjà résolus, pour ne pas payer deux fois la recherche.
_channel_ids: dict[str, str] = {}


class YouTubeError(Exception):
    """Erreur YouTube, avec un message prêt à afficher."""


@dataclass
class VideoInfo:
    youtube_id: str
    title: str
    channel: str | None
    language: str | None = None
    duration_seconds: int | None = None
    priority: bool = False


def parse_video_id(value: str) -> str | None:
    """Extrait l'identifiant d'une adresse YouTube (watch, youtu.be, embed, shorts, live)."""
    value = value.strip()
    if ID_PATTERN.match(value):
        return value
    if "://" not in value:
        value = "https://" + value
    url = urlparse(value)
    host = (url.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        candidate = url.path.strip("/").split("/")[0]
    else:
        parts = [p for p in url.path.split("/") if p]
        if parts[:1] in (["embed"], ["shorts"], ["live"], ["v"]) and len(parts) > 1:
            candidate = parts[1]
        else:
            candidate = parse_qs(url.query).get("v", [""])[0]
    return candidate if ID_PATTERN.match(candidate) else None


def parse_duration(iso: str | None) -> int | None:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def _is_french(language: str | None) -> bool:
    return language is None or language.lower().startswith("fr")


def _matches_game(title: str, game_name: str) -> bool:
    """Au moins la moitié des mots significatifs du jeu apparaissent dans le titre."""
    words = [w for w in normalize(game_name).split() if len(w) >= 3 and w not in STOP_WORDS]
    if not words:
        return True
    haystack = normalize(title)
    found = sum(1 for w in words if w in haystack)
    return found * 2 >= len(words)


class VideoNotFoundError(YouTubeError):
    """La vidéo n'existe pas ou est privée."""


class OEmbedClient:
    """Titre et chaîne d'une vidéo publique, sans clé (adresse d'intégration de YouTube)."""

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(timeout=5, transport=transport)

    def info(self, youtube_id: str) -> VideoInfo | None:
        """Renvoie None si YouTube ne répond pas : le lien reste utilisable sans ses détails."""
        watch_url = f"https://www.youtube.com/watch?v={youtube_id}"
        try:
            response = self._client.get(
                "https://www.youtube.com/oembed", params={"url": watch_url, "format": "json"}
            )
        except httpx.HTTPError:
            return None
        if response.status_code == 404:
            raise VideoNotFoundError("Cette vidéo est introuvable ou privée.")
        if response.status_code != 200:
            return None
        try:
            data = response.json()
            return VideoInfo(
                youtube_id=youtube_id, title=str(data["title"]), channel=data.get("author_name")
            )
        except (ValueError, KeyError):
            return None


class YouTubeClient:
    def __init__(self, api_key: str, transport: httpx.BaseTransport | None = None):
        self._key = api_key
        self._client = httpx.Client(base_url=BASE_URL, timeout=10, transport=transport)

    def _get(self, path: str, params: dict) -> dict:
        try:
            response = self._client.get(path, params={**params, "key": self._key})
        except httpx.HTTPError as error:
            # Le message d'origine contient l'adresse, donc la clé : on ne le relaie pas.
            raise YouTubeError("YouTube ne répond pas, réessaie plus tard.") from error
        if response.status_code == 200:
            return response.json()
        try:
            reason = response.json()["error"]["errors"][0]["reason"]
        except (ValueError, KeyError, IndexError, TypeError):
            reason = ""
        if reason in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
            raise YouTubeError(
                "Le quota YouTube du jour est épuisé. Réessaie demain ou colle le lien à la main."
            )
        if reason in ("keyInvalid", "accessNotConfigured", "ipRefererBlocked") or (
            response.status_code in (400, 403)
        ):
            raise YouTubeError("YouTube refuse la clé : vérifie YOUTUBE_API_KEY.")
        raise YouTubeError(f"YouTube a répondu une erreur ({response.status_code}).")

    def find_channel(self, name: str) -> str | None:
        wanted = name.casefold()
        if wanted in _channel_ids:
            return _channel_ids[wanted]
        data = self._get(
            "/search", {"part": "snippet", "type": "channel", "q": name, "maxResults": 5}
        )
        items = data.get("items", [])
        exact = [i for i in items if i["snippet"]["channelTitle"].casefold() == wanted]
        close = [i for i in items if wanted in i["snippet"]["channelTitle"].casefold()]
        for item in exact or close:
            _channel_ids[wanted] = item["id"]["channelId"]
            return _channel_ids[wanted]
        return None

    def _search_ids(self, query: str, channel_id: str | None, limit: int) -> list[str]:
        params = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": limit,
            "relevanceLanguage": "fr",
            "regionCode": "FR",
        }
        if channel_id:
            params["channelId"] = channel_id
        data = self._get("/search", params)
        return [i["id"]["videoId"] for i in data.get("items", []) if i.get("id", {}).get("videoId")]

    def details(self, ids: list[str]) -> list[VideoInfo]:
        if not ids:
            return []
        data = self._get(
            "/videos", {"part": "snippet,contentDetails", "id": ",".join(ids), "maxResults": 50}
        )
        videos = []
        for item in data.get("items", []):
            snippet = item["snippet"]
            videos.append(
                VideoInfo(
                    youtube_id=item["id"],
                    title=snippet["title"],
                    channel=snippet.get("channelTitle"),
                    language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                    duration_seconds=parse_duration(item.get("contentDetails", {}).get("duration")),
                )
            )
        return videos

    def suggest(self, game_name: str, channels: list[str], limit: int = 8) -> list[VideoInfo]:
        """Vidéos de règles en français : chaînes prioritaires d'abord, puis recherche libre."""
        ordered: list[tuple[str, bool]] = []
        for channel in channels:
            channel_id = self.find_channel(channel)
            if channel_id:
                ordered += [
                    (i, True) for i in self._search_ids(f"{game_name} règles", channel_id, 3)
                ]
        ordered += [(i, False) for i in self._search_ids(f"{game_name} règles du jeu", None, 8)]

        priority = {}
        for youtube_id, is_priority in ordered:
            priority[youtube_id] = priority.get(youtube_id, False) or is_priority
        by_id = {v.youtube_id: v for v in self.details(list(priority))}

        result = []
        for youtube_id, is_priority in priority.items():  # ordre de recherche conservé
            video = by_id.get(youtube_id)
            if video is None or not _is_french(video.language):
                continue
            if not _matches_game(video.title, game_name):
                continue
            video.priority = is_priority
            result.append(video)
        result.sort(key=lambda v: not v.priority)  # tri stable : prioritaires en tête
        return result[:limit]
