"""Tags automatiques calculés à partir des données d'un jeu."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Game, GameTag, Tag

DERIVED_KINDS = ("difficulty", "players", "duration", "audience")
KIND_ORDER = ["difficulty", "players", "duration", "audience", "style", "mechanic", "custom"]

# Libellés français des catégories et mécaniques BoardGameGeek.
CATEGORY_STYLE = {
    "Abstract Strategy": "Abstrait",
    "Adventure": "Aventure",
    "Ancient": "Antiquité",
    "Animals": "Animaux",
    "Bluffing": "Bluff",
    "City Building": "Construction de ville",
    "Civilization": "Civilisation",
    "Deduction": "Déduction",
    "Dice": "Dés",
    "Economic": "Économie",
    "Educational": "Éducatif",
    "Exploration": "Exploration",
    "Fantasy": "Fantasy",
    "Farming": "Agriculture",
    "Horror": "Horreur",
    "Humor": "Humour",
    "Industry / Manufacturing": "Industrie",
    "Medieval": "Médiéval",
    "Memory": "Mémoire",
    "Miniatures": "Figurines",
    "Murder/Mystery": "Enquête",
    "Mythology": "Mythologie",
    "Nautical": "Maritime",
    "Negotiation": "Négociation",
    "Party Game": "Ambiance",
    "Pirates": "Pirates",
    "Political": "Politique",
    "Puzzle": "Casse-tête",
    "Real-time": "Temps réel",
    "Renaissance": "Renaissance",
    "Science Fiction": "Science-fiction",
    "Space Exploration": "Exploration spatiale",
    "Spies/Secret Agents": "Espionnage",
    "Territory Building": "Construction de territoire",
    "Trains": "Trains",
    "Transportation": "Transport",
    "Trivia": "Quiz",
    "Wargame": "Wargame",
    "Word Game": "Jeu de mots",
}
# Mécaniques mises en avant dans le style du jeu.
MECHANIC_STYLE = {
    "Cooperative Game": "Coopératif",
    "Semi-Cooperative Game": "Semi-coopératif",
    "Team-Based Game": "Par équipes",
    "Worker Placement": "Placement d'ouvriers",
    "Deck, Bag, and Pool Building": "Deck-building",
    "Hidden Roles": "Rôles cachés",
}
MECHANICS = {
    "Action Points": "Points d'action",
    "Area Majority / Influence": "Majorité",
    "Auction/Bidding": "Enchères",
    "Betting and Bluffing": "Paris et bluff",
    "Card Drafting": "Draft",
    "Dice Rolling": "Lancer de dés",
    "Drafting": "Draft",
    "Engine Building": "Construction de moteur",
    "Hand Management": "Gestion de main",
    "Memory": "Mémoire",
    "Modular Board": "Plateau modulaire",
    "Network and Route Building": "Réseau et routes",
    "Open Drafting": "Draft",
    "Pattern Building": "Construction de motifs",
    "Programmed Movement": "Programmation",
    "Push Your Luck": "Prise de risque",
    "Role Playing": "Jeu de rôle",
    "Roll / Spin and Move": "Lancer et avancer",
    "Set Collection": "Collection de sets",
    "Tech Trees / Tech Tracks": "Arbre technologique",
    "Tile Placement": "Placement de tuiles",
    "Trading": "Échanges",
    "Trick-taking": "Plis",
    "Variable Player Powers": "Pouvoirs asymétriques",
    "Variable Setup": "Mise en place variable",
    "Voting": "Vote",
}


def bgg_tags(categories: list[str], mechanics: list[str]) -> list[tuple[str, str]]:
    """Convertit les catégories et mécaniques BoardGameGeek en tags français."""
    wanted: list[tuple[str, str]] = []
    for name in categories:
        if name in CATEGORY_STYLE:
            wanted.append(("style", CATEGORY_STYLE[name]))
    for name in mechanics:
        if name in MECHANIC_STYLE:
            wanted.append(("style", MECHANIC_STYLE[name]))
        elif name in MECHANICS:
            wanted.append(("mechanic", MECHANICS[name]))
    return list(dict.fromkeys(wanted))


def difficulty_label(weight: float) -> str:
    if weight < 1.5:
        return "Très facile"
    if weight < 2.25:
        return "Facile"
    if weight < 3.25:
        return "Moyen"
    return "Expert"


def duration_label(minutes: int) -> str:
    if minutes < 30:
        return "Moins de 30 min"
    if minutes <= 60:
        return "30–60 min"
    if minutes <= 120:
        return "1–2 h"
    return "Plus de 2 h"


def derive_tags(game: Game) -> list[tuple[str, str]]:
    """Tags déduits des champs numériques du jeu."""
    wanted: list[tuple[str, str]] = []

    if game.weight:
        wanted.append(("difficulty", difficulty_label(game.weight)))

    low, high = game.min_players, game.max_players
    if low or high:
        low, high = low or high, high or low
        if low == 1:
            wanted.append(("players", "Solo"))
        if low <= 2 <= high:
            wanted.append(("players", "2 joueurs"))
        if low <= 4 and high >= 3:
            wanted.append(("players", "3–4 joueurs"))
        if high >= 5:
            wanted.append(("players", "5 joueurs et plus"))
    for part in (game.best_players or "").split(","):
        if part.strip().isdigit():
            wanted.append(("players", f"Idéal à {part.strip()}"))

    minutes = game.max_time or game.min_time
    if minutes:
        wanted.append(("duration", duration_label(minutes)))

    if game.weight and game.min_age is not None and game.min_age <= 7 and game.weight < 1.5:
        wanted.append(("audience", "Enfants"))
    if game.weight and game.weight < 2.5 and (game.min_age is None or game.min_age <= 10):
        wanted.append(("audience", "Famille"))
    if game.weight and game.weight >= 2.5:
        wanted.append(("audience", "Joueurs initiés" if game.weight < 3.4 else "Joueurs experts"))

    return list(dict.fromkeys(wanted))


def get_or_create_tag(db: Session, kind: str, label: str) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.kind == kind, Tag.label == label))
    if tag is None:
        tag = Tag(kind=kind, label=label)
        db.add(tag)
        db.flush()
    return tag


def sync_auto_tags(
    db: Session,
    game: Game,
    wanted: list[tuple[str, str]],
    kinds: tuple[str, ...] = DERIVED_KINDS,
) -> None:
    """Remplace les tags automatiques des types donnés. Les tags posés à la main restent."""
    wanted_set = set(wanted)
    current: dict[tuple[str, str], GameTag] = {
        (link.tag.kind, link.tag.label): link for link in game.tag_links
    }

    for key, link in current.items():
        if link.source == "auto" and key[0] in kinds and key not in wanted_set:
            game.tag_links.remove(link)
    for key in wanted:
        if key in current:
            continue
        tag = get_or_create_tag(db, *key)
        game.tag_links.append(GameTag(tag=tag, source="auto"))
    db.flush()
