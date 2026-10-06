# Modèle de données

SQLite, géré par SQLAlchemy 2 et Alembic. Montants en centimes (entiers), dates en ISO 8601.

```
game ─┬─< game_tag >── tag
      ├─< note_entry
      ├─< video
      ├─< rule_sheet
      ├─< play ─< play_player
      ├─< price_offer
      └─< game (extensions via base_game_id)
```

## game

| Colonne | Type | Remarque |
|---|---|---|
| id | int PK | |
| bgg_id | int, unique, nullable | identifiant BoardGameGeek |
| name_fr | text | nom affiché |
| name_original | text | |
| search_text | text | noms normalisés (sans accents ni majuscules) pour la recherche et le tri |
| year | int | |
| publisher | text | |
| description | text | |
| image_url | text | |
| ean | text, index | code-barres |
| min_players / max_players | int | |
| best_players | text | ex. « 3,4 » |
| min_time / max_time | int | minutes |
| min_age | int | |
| weight | real | poids BGG 1–5 |
| bgg_rating | real | |
| base_game_id | int FK game, nullable | rempli pour une extension |
| status | text | owned, lent, wishlist, sold |
| lent_to / lent_since | text / date | |
| condition | text | new, very_good, good, worn |
| purchase_price_cents | int | |
| purchase_date / purchase_place | date / text | |
| storage_location | text | |
| rating | int | note perso sur 10 |
| comment | text | |
| created_at / updated_at | datetime | |

## tag et game_tag

| tag | |
|---|---|
| id | int PK |
| kind | text : style, difficulty, players, duration, audience, mechanic, custom |
| label | text, unique avec kind |

`game_tag(game_id, tag_id, source)` où `source` vaut `auto` ou `user`. Les tags `auto` sont recalculés, les tags `user` jamais.
À chaque modification, les tags `difficulty`, `players`, `duration` et `audience` sont recalculés depuis la fiche. Les tags `style` et `mechanic` viennent de l'import BoardGameGeek et ne changent plus ensuite.

## note_entry

Aides pour les futures parties. `id, game_id, kind (forgotten_rule, common_mistake, strategy, house_rule), text, created_at`.

## video

`id, game_id, youtube_id, title, channel, language, source (manual, auto), validated (bool), added_at`. Une vidéo est unique par jeu. Les propositions de la recherche automatique ne sont pas stockées : seule celle que l'utilisateur ajoute l'est.

## rule_sheet

`id, game_id, kind (summary, beginner_guide), content_md, origin (manual, ai_draft), reviewed (bool), updated_at`.
Une fiche `ai_draft` non relue est affichée avec un bandeau d'avertissement.

## play et play_player

`play : id, game_id, played_on, duration_min, comment`.
`play_player : play_id, player_name, score, is_winner`.

## price_offer

| Colonne | Type | Remarque |
|---|---|---|
| id | int PK | |
| game_id | int FK, nullable | null pour une recherche en magasin hors collection |
| query | text | nom ou EAN recherché |
| shop | text | |
| price_cents | int | |
| condition | text | new, used |
| url | text | |
| source | text | manual ou nom du module |
| observed_at | datetime | |

## Calcul de la valeur

- Valeur neuf d'un jeu : médiane des offres `new` des 30 derniers jours, sinon dernière offre connue.
- Valeur occasion : même règle sur les offres `used`.
- Valeur de la collection : somme sur les jeux `owned` et `lent`, extensions comprises.
- Les jeux sans offre sont listés à part avec leur prix d'achat comme repère.
