# Déploiement avec Portainer

L'image est construite par GitHub Actions à chaque push sur `main` et publiée sur
`ghcr.io/wokioz/myludo`, pour les serveurs x86 (amd64) et ARM (arm64, ex. Raspberry Pi).
Portainer se contente de télécharger l'image : rien n'est compilé sur le serveur.

## Première installation

1. Vérifier que l'image est publique : sur GitHub, profil, onglet **Packages**, `myludo`,
   **Package settings**, **Change visibility** sur **Public**. À faire une seule fois.
   Si elle reste privée, ajouter `ghcr.io` dans Portainer, menu **Registries**, avec un
   jeton GitHub ayant le droit `read:packages`.
2. Dans Portainer : **Stacks**, **Add stack**, nom `myludo`.
3. Choisir **Repository** :
   - Repository URL : `https://github.com/WokiOz/MyLudo`
   - Repository reference : `refs/heads/main`
   - Compose path : `deploy/portainer-stack.yml`

   Ou choisir **Web editor** et coller le contenu de `deploy/portainer-stack.yml`.
4. Dans **Environment variables**, ajouter uniquement les clés voulues :

   | Variable | Rôle |
   |---|---|
   | `BGG_TOKEN` | Import des fiches BoardGameGeek |
   | `YOUTUBE_API_KEY` | Recherche des vidéos de règles |
   | `YOUTUBE_CHANNELS` | Chaînes prioritaires, `Ludochrono` par défaut |
   | `ANTHROPIC_API_KEY` | Brouillons de fiches via l'API Claude |
   | `ANTHROPIC_MODEL` | Modèle des brouillons, `claude-opus-5-5` par défaut. `claude-sonnet-5-5` coûte moins cher |
   | `PRICE_SOURCES` | Modules de prix activés, vide par défaut |
   | `APP_PASSWORD` | Mot de passe, obligatoire si exposé sur Internet |
   | `FORWARDED_ALLOW_IPS` | Adresse ou réseau du reverse proxy, pour que le blocage après 5 mots de passe faux vise chaque visiteur |
   | `MYLUDO_PORT` | Port de l'hôte, `6018` par défaut |
   | `MYLUDO_TAG` | Version de l'image, `latest` par défaut |

5. **Deploy the stack**, puis ouvrir `http://<ip-du-serveur>:6018`.

## Mise à jour

Ouvrir la stack, cliquer **Pull and redeploy** (méthode Repository) ou **Update the stack**
en cochant **Re-pull image** (méthode Web editor). Les données restent dans le volume
`myludo-data`.

Pour revenir à une version précise, mettre `MYLUDO_TAG` sur un tag `sha-xxxxxxx`
visible dans l'onglet Packages de GitHub.

## Sauvegarde

Les données tiennent dans un fichier : `/data/myludo.db` du volume `myludo-data`.
Le copier depuis Portainer, **Volumes**, `myludo_myludo-data`, ou avec :

```bash
docker cp myludo:/data/myludo.db ./myludo-$(date +%F).db
```

## HTTPS

Pour le scan de code-barres sur téléphone ou un accès hors de chez soi, placer un reverse
proxy avec certificat devant le port 6018, par exemple Nginx Proxy Manager déployé lui
aussi dans Portainer.
