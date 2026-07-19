"""Surveille les places disponibles pour The Odyssey au Cineplex et notifie via Pushbullet.

Concu pour tourner via GitHub Actions (cron). Ne notifie que les nouveaux sieges
(etat persiste dans state.json, committe par le workflow).
"""

import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

THEATRE_ID = int(os.environ.get("THEATRE_ID", "7408"))
MOVIE_KEYWORD = os.environ.get("MOVIE_KEYWORD", "odyssey").lower()
DATES = os.environ.get("DATES", "2026-07-26,2026-07-27,2026-07-28,2026-07-29").split(",")
TARGET_HOUR = int(os.environ.get("TARGET_HOUR", "19"))  # 19h = 7pm
MIN_ROW = os.environ.get("MIN_ROW", "D").upper()  # rangee D ou plus loin (E, F, ...)
# "Standard" exclut les sieges fauteuil roulant (EW*) et accompagnateur (EC*).
# Mettre "Standard,Wheelchair,Companion" pour tout inclure.
SEAT_TYPES = set(os.environ.get("SEAT_TYPES", "Standard").split(","))
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
PUSHBULLET_TOKEN = os.environ.get("PUSHBULLET_TOKEN", "")

SHOWTIMES_URL = "https://apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes"
TICKETING_URL = "https://apis.cineplex.com/prod/ticketing/api/v1/theatre/{t}/showtime/{s}"
SUBSCRIPTION_KEY = "dcdac5601d864addbc2675a2e96cb1f8"


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def find_showtimes():
    """Retourne [(showtime_id, 'YYYY-MM-DDTHH:MM:SS', url_reservation), ...] pour le film a l'heure cible."""
    found = []
    for date in DATES:
        y, m, d = date.strip().split("-")
        url = f"{SHOWTIMES_URL}?language=fr&locationId={THEATRE_ID}&date={int(m)}/{int(d)}/{y}"
        try:
            data = get_json(url, {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY})
        except Exception as e:
            print(f"[warn] showtimes {date}: {e}")
            continue
        for theatre in data:
            for dd in theatre.get("dates", []):
                for movie in dd.get("movies", []):
                    if MOVIE_KEYWORD not in movie.get("name", "").lower():
                        continue
                    for exp in movie.get("experiences", []):
                        for sess in exp.get("sessions", []):
                            start = sess.get("showStartDateTime", "")
                            sid = sess.get("vistaSessionId") or sess.get("showtimeId")
                            if start and sid and int(start[11:13]) == TARGET_HOUR:
                                url = sess.get("deeplinkUrl") or sess.get("ticketingUrl") or ""
                                found.append((int(sid), start, url))
    return found


def good_seats(showtime_id):
    """Sieges disponibles en rangee MIN_ROW ou plus loin. Retourne ['E12', 'F3', ...]."""
    layout = get_json(TICKETING_URL.format(t=THEATRE_ID, s=showtime_id) + "/seat-layout")
    avail = get_json(TICKETING_URL.format(t=THEATRE_ID, s=showtime_id) + "/seat-availability")
    statuses = avail.get("seatAvailabilities", {})
    seats = []
    for area_key in ("standardSeats", "dboxSeats", "balconySeats"):
        area = layout.get(area_key) or {}
        for row in area.get("rows", []):
            label = row.get("label")
            if not label or label[0] < MIN_ROW:
                continue
            for seat in row.get("seats", []):
                if seat.get("type") in SEAT_TYPES and statuses.get(seat["id"]) == "Available":
                    seats.append(seat["label"])
    return sorted(seats, key=lambda s: (s[0], int(s[1:]) if s[1:].isdigit() else 0))


def push(title, body):
    if not PUSHBULLET_TOKEN:
        print("[warn] PUSHBULLET_TOKEN manquant, notification non envoyee")
        print(title, "\n", body)
        return
    payload = json.dumps({"type": "note", "title": title, "body": body}).encode()
    req = urllib.request.Request(
        "https://api.pushbullet.com/v2/pushes",
        data=payload,
        headers={"Access-Token": PUSHBULLET_TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"[ok] pushbullet: {resp.status}")


def main():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    showtimes = find_showtimes()
    if not showtimes:
        print("[warn] aucune seance trouvee — le film ou les dates ont peut-etre change")

    lines = []
    for sid, start, url in showtimes:
        try:
            seats = good_seats(sid)
        except Exception as e:
            print(f"[warn] seats {sid}: {e}")
            continue
        prev = set(state.get(str(sid), []))
        new = [s for s in seats if s not in prev]
        date_h = f"{start[8:10]}/{start[5:7]} {start[11:16]}"
        print(f"{date_h} (showtime {sid}): {len(seats)} places rangee {MIN_ROW}+ : {', '.join(seats) or '-'}")
        if new:
            lines.append(f"{date_h} : {', '.join(new)}\n➡ {url}")
        state[str(sid)] = seats

    if lines:
        push(
            "🎬 The Odyssey — places dispo !",
            f"Nouvelles places rangee {MIN_ROW}+ :\n\n" + "\n\n".join(lines),
        )

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    print("[ok] termine")


if __name__ == "__main__":
    sys.exit(main())
