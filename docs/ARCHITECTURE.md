# Architecture

```
Navigateur (mobile/PC)
        │  http://<hôte>:6018
        ▼
┌──────────────────────── conteneur myludo ────────────────────────┐
│ FastAPI (uvicorn, port 6018)                                     │
│   /api/*      → routes JSON                                      │
│   /*          → frontend Vue compilé (fichiers statiques)        │
│ APScheduler   → relevé des prix chaque nuit (si activé)          │
│ SQLite        → /data/myludo.db (volume)                         │
└──────────────────────────────────────────────────────────────────┘
        │ appels sortants optionnels
        ├── BoardGameGeek XML API2 (données des jeux)
        ├── YouTube Data API v3 (vidéos de règles)
        ├── API Claude (brouillons de fiches)
        └── Sites de boutiques (modules de prix)
```

## Arborescence cible

```
backend/
  app/
    main.py            # création de l'app, montage du frontend
    config.py          # paramètres lus depuis l'environnement
    db.py              # moteur SQLAlchemy, session
    models/            # modèles SQLAlchemy
    schemas/           # schémas Pydantic
    api/               # une route par ressource (games, tags, prices…)
    services/          # logique métier (tags auto, valorisation, similarité)
    integrations/      # clients BGG, YouTube, Claude
    prices/            # un module par boutique + interface commune
    jobs.py            # tâches planifiées
  migrations/          # Alembic
  tests/
frontend/
  src/
    views/             # Collection, Fiche jeu, Règles, Mode magasin, Valeur…
    components/
    api.ts             # client HTTP typé
```

## Intégrations externes

| Service | Usage | Clé | Sans clé |
|---|---|---|---|
| BoardGameGeek XML API2 | Fiche jeu, mécaniques, poids, recommandations | Jeton BGG (inscription gratuite) | Saisie manuelle |
| YouTube Data API v3 | Recherche de vidéos de règles | Clé Google gratuite, quota journalier | Liens collés à la main |
| API Claude | Brouillons de règles simplifiées et fiches | Clé Anthropic payante | Rédaction manuelle |
| Boutiques | Relevé de prix | Aucune | Prix saisis à la main |

### Vidéos : chaînes cherchées, dans l'ordre

1. Ludochrono
2. Autres chaînes francophones ajoutées dans `YOUTUBE_CHANNELS` (à vérifier avant ajout)
3. Recherche libre « <nom du jeu> règles du jeu » avec `relevanceLanguage=fr`

Les identifiants de chaînes sont stockés en configuration et peuvent être modifiés.

### Prix : interface commune des modules

```python
class PriceSource(Protocol):
    name: str
    def search(self, query: str, ean: str | None) -> list[PriceOffer]: ...
```

Chaque module respecte un délai entre deux requêtes, s'identifie par un User-Agent clair et peut être désactivé dans `.env`.
Un module cassé ne doit jamais faire échouer les autres.

## Points d'attention

- **HTTPS et caméra** : le scan de code-barres demande HTTPS. Prévoir un reverse proxy (Caddy, Traefik, Nginx Proxy Manager) devant le port 6018.
- **Sécurité** : pas d'authentification à l'étape 1 car usage en réseau local. Une variable `APP_PASSWORD` est prévue avant toute exposition sur Internet.
- **Sauvegarde** : le fichier SQLite du volume suffit. Un export JSON complet sera aussi disponible.
