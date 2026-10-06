# MyLudo

Une ludothèque personnelle : collection de jeux de société, tags, notes, vidéos de règles en français, fiches pour débutants, prix du marché et valeur de la collection.

## Déployer avec Portainer

Créer une stack depuis `deploy/portainer-stack.yml`. Le pas-à-pas est dans `docs/DEPLOIEMENT.md`.

## Lancer en local

```bash
cp .env.example .env   # optionnel, pour activer les intégrations
docker compose up -d --build
```

Puis ouvrir http://localhost:6018. Les données sont dans le volume Docker `myludo-data`.

## Documentation

- `docs/SPEC.md` : fonctionnalités
- `docs/ARCHITECTURE.md` : technique et intégrations
- `docs/DATA_MODEL.md` : base de données
- `docs/ROADMAP.md` : avancement et idées
- `docs/DEPLOIEMENT.md` : installation et mise à jour avec Portainer
