"""Vérifie que chaque vidéo du paquet existe encore et porte le titre enregistré.

À lancer à la main, avec un accès à Internet :
    python scripts/check_pack_videos.py
Le code de sortie est 1 si une vidéo a disparu ou changé de titre.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "app" / "content" / "rules_pack.json"


def check(youtube_id: str) -> tuple[str, str] | None:
    watch = urllib.parse.quote(f"https://www.youtube.com/watch?v={youtube_id}", safe="")
    url = f"https://www.youtube.com/oembed?format=json&url={watch}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.load(response)
    except urllib.error.URLError:
        return None
    return data["title"], data["author_name"]


def main() -> int:
    problems = 0
    for game in json.loads(PACK.read_text(encoding="utf-8"))["games"]:
        for video in game["videos"]:
            found = check(video["youtube_id"])
            if found is None:
                print(f"INTROUVABLE  {game['name']} : {video['youtube_id']}")
                problems += 1
            elif found[0] != video["title"]:
                print(f"TITRE CHANGÉ {game['name']} : « {video['title']} » devenu « {found[0]} »")
                problems += 1
    print("Tout est en ordre." if not problems else f"{problems} problème(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
