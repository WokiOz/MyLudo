# MyLudo — consignes de développement

Application web personnelle de gestion de ludothèque (jeux de société).
Spécification : `docs/SPEC.md`. Architecture : `docs/ARCHITECTURE.md`.
Modèle de données : `docs/DATA_MODEL.md`. Avancement : `docs/ROADMAP.md`.

## Règles du projet

- **Tout le contenu visible est en français** : interface, règles, fiches, messages d'erreur.
- **Vidéos de règles en français uniquement.** Ludochrono en priorité, puis les chaînes configurées dans `YOUTUBE_CHANNELS`.
- **Ne jamais recopier un livret de règles.** Les résumés et fiches sont des textes rédigés (droit d'auteur).
- **Chaque intégration externe est optionnelle.** Sans clé ou si le service est en panne, l'appli reste utilisable en saisie manuelle.
- **Les scrapers de prix sont désactivés par défaut** et isolés : un module par boutique dans `backend/app/prices/`.
- **Pas de secret dans le dépôt.** Les clés vont dans `.env` (modèle : `.env.example`).
- **Rester simple.** Une seule image Docker, SQLite, pas de service supplémentaire sans besoin démontré.
- **Avancer étape par étape** selon `docs/ROADMAP.md` et cocher ce qui est livré.

## Stack

- Backend : Python 3.12, FastAPI, SQLAlchemy 2, Alembic, httpx, APScheduler, pydantic-settings.
- Frontend : Vue 3, Vite, TypeScript, vue-router. Interface pensée mobile d'abord.
- Base : SQLite dans `/data/myludo.db` (volume Docker).
- Conteneur : image unique, le backend sert l'API sous `/api` et le frontend compilé. Port **6018**.

## Commandes

```bash
# Conteneur complet
docker compose up --build            # http://localhost:6018

# Backend en local
cd backend && pip install -e ".[dev]"
uvicorn app.main:app --reload --port 6018
pytest

# Frontend en local (proxy /api vers le port 6018)
cd frontend && npm install && npm run dev
npm run build
```

## Conventions de code

- Noms de code (variables, fonctions, tables) en anglais. Textes affichés en français.
- Routes API en `/api/<ressource>`, découpées par fichier dans `backend/app/api/`.
- Clients d'API externes dans `backend/app/integrations/`, avec un timeout et un test qui simule la réponse.
- Toute modification du schéma passe par une migration Alembic.
- Tests pytest pour chaque route et chaque intégration. Pas d'appel réseau réel dans les tests.
