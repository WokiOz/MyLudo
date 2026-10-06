# Spécification fonctionnelle

Utilisateur cible : une personne qui gère sa ludothèque, joue avec des débutants et compare les prix en magasin.
Usage principal sur téléphone, accès sur le réseau local.

## 1. Collection

- Ajouter un jeu par recherche de nom. La fiche se pré-remplit depuis BoardGameGeek : nom français, année, éditeur, image, joueurs min/max, nombre de joueurs conseillé, durée, âge, poids (difficulté), mécaniques, catégories.
- Saisie manuelle possible de tous les champs si BoardGameGeek est indisponible.
- Champs perso : date et prix d'achat, lieu d'achat, état (neuf, très bon, bon, usé), extensions possédées, emplacement de rangement.
- Statut : possédé, prêté (à qui, depuis quand), souhaité, vendu.
- Import CSV et export CSV/JSON de la collection.

## 2. Tags et recherche

- Tags automatiques issus des données :
  - **Style** : stratégie, ambiance, coopératif, familial, enquête, placement d'ouvriers, deck-building, etc.
  - **Difficulté** : Très facile / Facile / Moyen / Expert, déduite du poids BoardGameGeek (1–5).
  - **Joueurs** : solo, 2 joueurs, 3–4, 5 et plus, et « idéal à N ».
  - **Durée** : moins de 30 min, 30–60 min, 1–2 h, plus de 2 h.
  - **Public** : enfants, famille, initiés, experts.
- Tags personnels libres.
- Recherche texte et filtres combinables. Exemple : « 5 joueurs, moins de 45 min, facile ».
- Bouton « Que jouer ce soir ? » : nombre de joueurs + temps dispo + niveau du groupe donne une sélection.

## 3. Notes, commentaires et aides

- Note personnelle sur 10 et commentaire libre.
- Aides pour les futures parties : règles souvent oubliées, erreurs fréquentes, astuces de stratégie, variantes maison.
- Journal des parties : date, joueurs, scores, gagnant, remarque.

## 4. Vidéos de règles

- **Sans aucune clé** : on colle l'adresse publique d'une vidéo YouTube. Le titre et la chaîne se remplissent tout seuls, la vidéo se lit dans la fiche. Des boutons ouvrent YouTube sur une recherche déjà écrite (Ludochrono + nom du jeu, ou règles en français).
- **Facultatif, avec une clé YouTube Data API** : l'appli propose elle-même des vidéos en français, Ludochrono en priorité. L'utilisateur valide avant enregistrement.

## 5. Règles simplifiées et fiches débutants

- **Vue règles simple** : but du jeu, mise en place, tour de jeu, fin de partie et décompte. Une page courte et lisible sur téléphone.
- **Fiche méthodologique débutants** :
  - ordre conseillé pour expliquer le jeu,
  - aide-mémoire du tour,
  - erreurs classiques des nouveaux joueurs,
  - partie d'essai ou tour à découvert conseillé,
  - durée d'explication estimée.
- Version imprimable (CSS print).
- Rédaction manuelle dans un éditeur Markdown. Un paquet de fiches et de vidéos prêtes à l'emploi, livré avec l'appli, complète en un clic les jeux courants déjà présents. Un brouillon généré via l'API Claude reste possible si une clé est fournie. Tout brouillon est à relire avant publication.
- Interdiction de recopier le livret officiel.

## 6. Prix du marché

- Saisie manuelle d'un prix relevé : boutique, prix, neuf ou occasion, date, lien.
- Modules de relevé automatique optionnels par boutique (Philibert, Ludum, Okkazeo pour l'occasion). Désactivés par défaut, rafraîchis une fois par nuit.
- Historique des prix par jeu, prix le plus bas, prix moyen.
- **Mode magasin** : page mobile avec recherche rapide par nom. Affiche les prix connus et dit si le prix en rayon est bon. Scan du code-barres si l'appli est servie en HTTPS.
- Le mode magasin fonctionne aussi pour un jeu absent de la collection.

## 7. Valeur de la ludothèque

- Total payé, valeur actuelle neuf, valeur actuelle occasion, écart.
- Valeur des extensions comptée avec le jeu de base.
- Répartition par catégorie, par année d'achat, top 10 des jeux les plus chers.
- Les jeux sans prix connu sont signalés et non comptés en silence.

## 8. Jeux similaires et découverte

- Pour un jeu donné, liste de jeux proches selon mécaniques, catégories, difficulté et durée.
- Jeux de la collection et jeux à découvrir, avec description, vidéo et note BoardGameGeek.
- Ajout direct d'un jeu découvert à la liste de souhaits.

## Hors périmètre pour l'instant

- Comptes multiples et partage public.
- Application mobile native.
