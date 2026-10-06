"""Réponses YouTube simulées : aucun appel réseau dans les tests."""

import httpx

LUDO = "AAAAAAAAAAA"  # Ludochrono
OTHER = "BBBBBBBBBBB"  # autre chaîne française
ENGLISH = "CCCCCCCCCCC"  # vidéo en anglais
OFFTOPIC = "DDDDDDDDDDD"  # sans rapport avec le jeu

VIDEOS = {
    LUDO: ("Catan - Règles du jeu", "Ludochrono", "fr", "PT12M30S"),
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
                            "snippet": {"channelTitle": "Ludochrono Fan Club"},
                        },
                        {
                            "id": {"channelId": "UC-ludo"},
                            "snippet": {"channelTitle": "Ludochrono"},
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
