# MyLudo

Une ludothèque personnelle : collection de jeux de société, tags, notes, vidéos de règles en français, fiches pour débutants, prix du marché et valeur de la collection.

## Lancer

```bash
cp .env.example .env   # optionnel, pour activer les intégrations
docker compose up -d --build
```

Puis ouvrir http://localhost:6018.

Les données sont dans le volume Docker `myludo-data`.

## Documentation

- `docs/SPEC.md` : fonctionnalités
- `docs/ARCHITECTURE.md` : technique et intégrations
- `docs/DATA_MODEL.md` : base de données
- `docs/ROADMAP.md` : avancement et idées
