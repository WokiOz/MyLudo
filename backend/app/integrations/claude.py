"""Brouillons de règles simplifiées et de fiches débutants via l'API Claude."""

import anthropic

from app.config import get_settings

MAX_TOKENS = 4000

SYSTEM = """Tu aides un joueur à préparer des aide-mémoire pour ses parties de jeux de société.

Règles absolues :
- Écris en français, en Markdown, avec des titres de niveau 2 (##), des listes courtes et des phrases simples.
- Rédige avec tes propres mots. Ne recopie jamais le livret de règles ni aucun texte protégé.
- N'invente rien. Si tu ne connais pas précisément ce jeu, ou si un point de règle est incertain, écris « À vérifier dans le livret » à cet endroit plutôt que de deviner.
- Réponds uniquement avec le document Markdown, sans introduction ni conclusion."""

KIND_INSTRUCTIONS = {
    "summary": """Rédige les règles simplifiées du jeu, lisibles en deux minutes, avec ces sections dans cet ordre :
## But du jeu
## Mise en place
## Déroulement d'un tour
## Fin de partie et décompte
## À retenir""",
    "beginner_guide": """Rédige une fiche méthodologique pour expliquer le jeu à de nouveaux joueurs, avec ces sections dans cet ordre :
## Avant de commencer (durée d'explication estimée, matériel à sortir)
## Expliquer en 5 minutes (4 à 6 étapes numérotées, de la plus importante à la moins importante)
## Aide-mémoire du tour (liste à cocher avec - [ ])
## Erreurs classiques des nouveaux joueurs
## Partie d'essai conseillée
## Pour que ça se passe bien""",
}


class ClaudeError(Exception):
    """Erreur de l'API Claude, avec un message prêt à afficher."""


def build_prompt(game: dict, notes: list[str], kind: str) -> str:
    facts = [
        f"Nom : {game['name_fr']}",
        f"Nom d'origine : {game['name_original']}" if game.get("name_original") else "",
        f"Année : {game['year']}" if game.get("year") else "",
        f"Éditeur : {game['publisher']}" if game.get("publisher") else "",
        f"Joueurs : {game['players']}" if game.get("players") else "",
        f"Durée : {game['duration']}" if game.get("duration") else "",
        f"Âge : {game['min_age']} ans et plus" if game.get("min_age") else "",
    ]
    text = "Voici le jeu :\n" + "\n".join(f for f in facts if f)
    if notes:
        text += "\n\nNotes personnelles du propriétaire, à intégrer si elles sont pertinentes :\n"
        text += "\n".join(f"- {n}" for n in notes)
    return f"{text}\n\n{KIND_INSTRUCTIONS[kind]}"


def draft(
    game: dict, notes: list[str], kind: str, client: anthropic.Anthropic | None = None
) -> str:
    settings = get_settings()
    client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=90)
    try:
        response = client.beta.messages.create(
            model=settings.anthropic_model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": build_prompt(game, notes, kind)}],
            output_config={"effort": "medium"},
            # Si les filtres de sécurité refusent la demande, l'API la rejoue sur un autre modèle.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as error:
        raise ClaudeError("Claude refuse la clé : vérifie ANTHROPIC_API_KEY.") from error
    except anthropic.RateLimitError as error:
        raise ClaudeError("Trop de demandes à Claude, réessaie dans une minute.") from error
    except anthropic.APIStatusError as error:
        raise ClaudeError(f"Claude a répondu une erreur ({error.status_code}).") from error
    except anthropic.APIConnectionError as error:
        raise ClaudeError("Claude ne répond pas, réessaie plus tard.") from error

    if response.stop_reason == "refusal":
        raise ClaudeError("Claude a refusé cette demande. Rédige la fiche à la main.")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise ClaudeError("Claude n'a rien renvoyé, réessaie.")
    if response.stop_reason == "max_tokens":
        text += "\n\n> Le brouillon a été coupé : à compléter.\n"
    return text
