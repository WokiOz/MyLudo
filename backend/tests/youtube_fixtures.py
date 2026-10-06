"""Réponses YouTube simulées : aucun appel réseau dans les tests."""

import httpx

LUDO = "AAAAAAAAAAA"  # Ludovox (publie les LudoChrono)
OTHER = "BBBBBBBBBBB"  # autre chaîne française
ENGLISH = "CCCCCCCCCCC"  # vidéo en anglais
OFFTOPIC = "DDDDDDDDDDD"  # sans rapport avec le jeu

VIDEOS = {
    LUDO: ("Catan - Règles du jeu", "Ludovox", "fr", "PT12M30S"),
    OTHER: ("Les Colons de Catan : comment jouer", "Une autre chaîne", None, "PT1H2M"),
    ENGLISH: ("Catan how to play", "Board Game Channel", "en", "PT9M"),
    OFFTOPIC: ("Recette de crêpes", "Cuisine", "fr", "PT5M"),
}


def youtube_transport(error_reason: str | None = None, status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        assert params["key"] == "cle-secrete"
        if error_reason:
            body = {"error": {"errors": [{"reason": error_reason}]}}
            return httpx.Response(status, json=body)
        path = request.url.path
        if path.endswith("/search") and params["type"] == "channel":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": {"channelId": "UC-autre"},
                            "snippet": {"channelTitle": "Ludovox Fan Club"},
                        },
                        {
                            "id": {"channelId": "UC-ludo"},
                            "snippet": {"channelTitle": "Ludovox"},
                        },
                    ]
                },
            )
        if path.endswith("/search"):
            ids = (
                [LUDO] if params.get("channelId") == "UC-ludo" else [ENGLISH, OTHER, LUDO, OFFTOPIC]
            )
            return httpx.Response(200, json={"items": [{"id": {"videoId": i}} for i in ids]})
        wanted = params["id"].split(",")
        items = [
            {
                "id": i,
                "snippet": {
                    "title": VIDEOS[i][0],
                    "channelTitle": VIDEOS[i][1],
                    **({"defaultAudioLanguage": VIDEOS[i][2]} if VIDEOS[i][2] else {}),
                },
                "contentDetails": {"duration": VIDEOS[i][3]},
            }
            for i in wanted
            if i in VIDEOS
        ]
        return httpx.Response(200, json={"items": items})

    return httpx.MockTransport(handler)


PRIVATE = "PPPPPPPPPPP"  # vidéo privée ou supprimée
UNKNOWN = "UUUUUUUUUUU"  # identifiant inexistant
DOWN = OTHER  # YouTube répond une erreur pour celle-ci


def oembed_transport() -> httpx.MockTransport:
    """Adresse publique d'intégration : aucune clé n'est envoyée ni attendue."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "key" not in request.url.params
        video_id = request.url.params["url"].rsplit("=", 1)[-1]
        if video_id == PRIVATE:
            return httpx.Response(404)
        if video_id == UNKNOWN:
            return httpx.Response(400)  # identifiant qui n'existe pas
        if video_id == DOWN:
            return httpx.Response(500)
        return httpx.Response(
            200, json={"title": "Catan - Règles du jeu", "author_name": "Ludovox"}
        )

    return httpx.MockTransport(handler)
