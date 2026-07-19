# Bot places Cineplex — The Odyssey

Surveille les places disponibles (rangée D ou plus) pour les séances de 19h de
**The Odyssey** au Cineplex Cinemas Vaughan (théâtre 7408), du 20 au 24 juillet 2026,
et envoie une notification **Pushbullet** quand de nouvelles places apparaissent.

## Fonctionnement

1. Interroge l'API Cineplex pour trouver automatiquement les séances de 19h du film
   sur les dates cibles (pas besoin de coder les showtime IDs en dur).
2. Pour chaque séance : croise `seat-layout` (plan de salle) et `seat-availability`.
3. Garde les sièges **Standard** disponibles en rangée **D ou plus loin** (D, E, F, …).
   Les sièges fauteuil roulant (EW*) et accompagnateur (EC*) sont exclus.
4. Notifie via Pushbullet **uniquement les nouvelles places** (état mémorisé dans
   `state.json`, committé par le workflow — pas de spam toutes les 10 minutes).

## Installation

```bash
cd bot-cineplex
git init && git add -A && git commit -m "bot cineplex"
gh repo create bot-cineplex --private --source . --push
```

Puis sur GitHub :

1. **Settings → Secrets and variables → Actions → New repository secret** :
   - Nom : `PUSHBULLET_TOKEN`
   - Valeur : ton token depuis https://www.pushbullet.com/#settings/account ("Create Access Token")
2. Onglet **Actions** → workflow "Check Odyssey seats" → **Run workflow** pour tester.

Le cron tourne ensuite toutes les 10 minutes (GitHub peut retarder de quelques minutes).

## Test local

```bash
python check_seats.py                      # sans token : affiche la notif au lieu de l'envoyer
PUSHBULLET_TOKEN=xxx python check_seats.py # envoie vraiment
```

## Configuration (variables d'environnement)

| Variable | Défaut | Description |
|---|---|---|
| `THEATRE_ID` | `7408` | Cineplex Cinemas Vaughan |
| `MOVIE_KEYWORD` | `odyssey` | Mot-clé dans le titre du film |
| `DATES` | `2026-07-20,…,2026-07-24` | Dates à surveiller |
| `TARGET_HOUR` | `19` | Heure de séance (19 = 19h00) |
| `MIN_ROW` | `D` | Rangée minimale acceptée |
| `EXPERIENCE` | `IMAX` | Filtre de salle (vide = toutes) |
| `SEAT_TYPES` | `Standard` | `Standard,Wheelchair,Companion` pour tout inclure |
