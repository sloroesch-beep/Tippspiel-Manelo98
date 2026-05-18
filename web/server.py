from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse
import base64
import re
import asyncio
from datetime import datetime, timezone
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
import httpx
import os
import secrets
import hashlib

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATABASE_URL = os.environ.get("DATABASE_URL")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
WEB_URL = os.environ.get("WEB_URL", "http://localhost:8000")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DISCORD_REDIRECT = f"{WEB_URL}/auth/discord/callback"
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
FOOTBALL_API_URL = "https://api.football-data.org/v4"
WC_2026_ID = 2000

# Global connection pool
pool: asyncpg.Pool = None

GRUPPE_MATCHES = [
    ("Mexiko","Suedafrika","11.06.2026","21:00","A"),
    ("Suedkorea","Tschechien","12.06.2026","04:00","A"),
    ("Kanada","Bosnien-Herzegowina","12.06.2026","21:00","B"),
    ("USA","Paraguay","13.06.2026","03:00","D"),
    ("Katar","Schweiz","13.06.2026","21:00","B"),
    ("Deutschland","Curacao","14.06.2026","19:00","E"),
    ("Australien","Tuerkei","14.06.2026","06:00","D"),
    ("Niederlande","Japan","14.06.2026","22:00","F"),
    ("Elfenbeinkueste","Ecuador","15.06.2026","01:00","E"),
    ("Schweden","Tunesien","15.06.2026","04:00","F"),
    ("Spanien","Kap Verde","15.06.2026","18:00","H"),
    ("Belgien","Aegypten","15.06.2026","21:00","G"),
    ("Saudi-Arabien","Uruguay","16.06.2026","00:00","H"),
    ("Iran","Neuseeland","16.06.2026","03:00","G"),
    ("Frankreich","Senegal","16.06.2026","21:00","I"),
    ("Irak","Norwegen","17.06.2026","00:00","I"),
    ("Argentinien","Algerien","17.06.2026","03:00","J"),
    ("Oesterreich","Jordanien","17.06.2026","06:00","J"),
    ("Portugal","DR Kongo","17.06.2026","19:00","K"),
    ("England","Kroatien","17.06.2026","22:00","L"),
    ("Ghana","Panama","18.06.2026","01:00","L"),
    ("Usbekistan","Kolumbien","18.06.2026","04:00","K"),
    ("Mexiko","Suedkorea","18.06.2026","21:00","A"),
    ("Suedafrika","Tschechien","19.06.2026","00:00","A"),
    ("USA","Australien","19.06.2026","21:00","D"),
    ("Katar","Kanada","19.06.2026","22:00","B"),
    ("Paraguay","Tuerkei","20.06.2026","06:00","D"),
    ("Deutschland","Elfenbeinkueste","20.06.2026","22:00","E"),
    ("Niederlande","Schweden","20.06.2026","19:00","F"),
    ("Bosnien-Herzegowina","Schweiz","20.06.2026","21:00","B"),
    ("Ecuador","Curacao","21.06.2026","02:00","E"),
    ("Tunesien","Japan","21.06.2026","06:00","F"),
    ("Belgien","Iran","21.06.2026","21:00","G"),
    ("Spanien","Saudi-Arabien","22.06.2026","00:00","H"),
    ("Neuseeland","Aegypten","22.06.2026","03:00","G"),
    ("Kap Verde","Uruguay","22.06.2026","18:00","H"),
    ("Frankreich","Irak","22.06.2026","21:00","I"),
    ("Senegal","Norwegen","23.06.2026","00:00","I"),
    ("Argentinien","Oesterreich","23.06.2026","03:00","J"),
    ("Algerien","Jordanien","23.06.2026","06:00","J"),
    ("Portugal","Usbekistan","23.06.2026","19:00","K"),
    ("England","Ghana","23.06.2026","22:00","L"),
    ("Panama","Kroatien","24.06.2026","01:00","L"),
    ("Kolumbien","DR Kongo","24.06.2026","04:00","K"),
    ("Mexiko","Tschechien","25.06.2026","00:00","A"),
    ("Suedafrika","Suedkorea","25.06.2026","00:00","A"),
    ("Kanada","Schweiz","25.06.2026","21:00","B"),
    ("Bosnien-Herzegowina","Katar","25.06.2026","21:00","B"),
    ("Deutschland","Ecuador","25.06.2026","22:00","E"),
    ("Elfenbeinkueste","Curacao","25.06.2026","22:00","E"),
    ("Niederlande","Tunesien","26.06.2026","01:00","F"),
    ("Japan","Schweden","26.06.2026","01:00","F"),
    ("Tuerkei","USA","26.06.2026","04:00","D"),
    ("Paraguay","Australien","26.06.2026","04:00","D"),
    ("Belgien","Neuseeland","26.06.2026","21:00","G"),
    ("Aegypten","Iran","26.06.2026","21:00","G"),
    ("Spanien","Uruguay","27.06.2026","00:00","H"),
    ("Kap Verde","Saudi-Arabien","27.06.2026","00:00","H"),
    ("Frankreich","Norwegen","27.06.2026","21:00","I"),
    ("Senegal","Irak","27.06.2026","21:00","I"),
    ("Argentinien","Jordanien","27.06.2026","03:00","J"),
    ("Algerien","Oesterreich","27.06.2026","03:00","J"),
    ("Portugal","Kolumbien","28.06.2026","01:30","K"),
    ("DR Kongo","Usbekistan","28.06.2026","01:30","K"),
    ("England","Panama","27.06.2026","23:00","L"),
    ("Kroatien","Ghana","27.06.2026","23:00","L"),
    ("Brasilien","Schottland","14.06.2026","19:00","C"),
    ("Marokko","Haiti","14.06.2026","22:00","C"),
    ("Brasilien","Marokko","19.06.2026","00:00","C"),
    ("Schottland","Haiti","19.06.2026","03:00","C"),
    ("Brasilien","Haiti","24.06.2026","21:00","C"),
    ("Marokko","Schottland","24.06.2026","21:00","C"),
]

KO_MATCHES = [
    ("1. Gruppe A","2. Gruppe J","28.06.2026","22:00","SF1"),
    ("1. Gruppe B","2. Gruppe K","29.06.2026","00:30","SF2"),
    ("1. Gruppe C","3. Platz (best)","29.06.2026","19:00","SF3"),
    ("1. Gruppe D","2. Gruppe G","29.06.2026","22:30","SF4"),
    ("1. Gruppe E","3. Platz (best)","30.06.2026","19:00","SF5"),
    ("1. Gruppe F","2. Gruppe I","30.06.2026","22:00","SF6"),
    ("1. Gruppe G","2. Gruppe D","01.07.2026","01:00","SF7"),
    ("1. Gruppe H","3. Platz (best)","01.07.2026","19:00","SF8"),
    ("1. Gruppe I","2. Gruppe E","01.07.2026","22:00","SF9"),
    ("1. Gruppe J","2. Gruppe A","02.07.2026","01:00","SF10"),
    ("1. Gruppe K","2. Gruppe B","02.07.2026","19:00","SF11"),
    ("1. Gruppe L","3. Platz (best)","02.07.2026","22:00","SF12"),
    ("2. Gruppe C","3. Platz (best)","03.07.2026","01:00","SF13"),
    ("2. Gruppe F","3. Platz (best)","03.07.2026","19:00","SF14"),
    ("2. Gruppe H","3. Platz (best)","03.07.2026","22:00","SF15"),
    ("2. Gruppe L","3. Platz (best)","04.07.2026","01:00","SF16"),
    ("Sieger SF1","Sieger SF2","04.07.2026","22:00","AF1"),
    ("Sieger SF3","Sieger SF4","05.07.2026","01:00","AF2"),
    ("Sieger SF5","Sieger SF6","05.07.2026","22:00","AF3"),
    ("Sieger SF7","Sieger SF8","06.07.2026","01:00","AF4"),
    ("Sieger SF9","Sieger SF10","06.07.2026","22:00","AF5"),
    ("Sieger SF11","Sieger SF12","07.07.2026","01:00","AF6"),
    ("Sieger SF13","Sieger SF14","07.07.2026","22:00","AF7"),
    ("Sieger SF15","Sieger SF16","08.07.2026","01:00","AF8"),
    ("Sieger AF1","Sieger AF2","09.07.2026","22:00","VF1"),
    ("Sieger AF3","Sieger AF4","10.07.2026","22:00","VF2"),
    ("Sieger AF5","Sieger AF6","11.07.2026","19:00","VF3"),
    ("Sieger AF7","Sieger AF8","11.07.2026","22:00","VF4"),
    ("Sieger VF1","Sieger VF3","14.07.2026","22:00","HF1"),
    ("Sieger VF2","Sieger VF4","15.07.2026","22:00","HF2"),
    ("Verlierer HF1","Verlierer HF2","18.07.2026","21:00","P3"),
    ("Sieger HF1","Sieger HF2","19.07.2026","21:00","FIN"),
]

async def get_db():
    return pool

async def init_db():
    async with pool.acquire() as db:
        # Tabellen erstellen
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            discord_id TEXT UNIQUE,
            username TEXT NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            avatar TEXT,
            session_token TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            welcomed INTEGER DEFAULT 0)""")

        await db.execute("""CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            match_date TEXT NOT NULL,
            match_time TEXT NOT NULL,
            group_name TEXT NOT NULL,
            home_score INTEGER DEFAULT NULL,
            away_score INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'open')""")

        await db.execute("""CREATE TABLE IF NOT EXISTS tips (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            match_id INTEGER NOT NULL,
            home_tip INTEGER NOT NULL,
            away_tip INTEGER NOT NULL,
            points INTEGER DEFAULT NULL,
            UNIQUE(user_id, match_id))""")

        await db.execute("""CREATE TABLE IF NOT EXISTS db_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

        # Sanfte Migrationen
        try: await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS welcomed INTEGER DEFAULT 0")
        except: pass
        try: await db.execute("ALTER TABLE tips ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMP DEFAULT NULL")
        except: pass
        # wm_champion table
        await db.execute("""CREATE TABLE IF NOT EXISTS wm_champions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            champion TEXT NOT NULL,
            tipped_at TIMESTAMP DEFAULT NOW(),
            points INTEGER DEFAULT NULL)""")

        # Version prüfen
        row = await db.fetchrow("SELECT MAX(version) as v FROM db_version")
        current_version = row['v'] or 0

        # Version 1: Spiele eintragen wenn DB leer
        if current_version < 1:
            count = await db.fetchval("SELECT COUNT(*) FROM matches")
            if count == 0:
                all_matches = GRUPPE_MATCHES + KO_MATCHES
                await db.executemany(
                    "INSERT INTO matches (home_team,away_team,match_date,match_time,group_name) VALUES ($1,$2,$3,$4,$5)",
                    all_matches)
            await db.execute("INSERT INTO db_version (version) VALUES (1) ON CONFLICT DO NOTHING")

        # Version 2: Fehlende Spiele ergänzen
        if current_version < 2:
            rows = await db.fetch("SELECT home_team||'-'||away_team as key FROM matches")
            existing = {r['key'] for r in rows}
            new_matches = [m for m in GRUPPE_MATCHES + KO_MATCHES if f"{m[0]}-{m[1]}" not in existing]
            if new_matches:
                await db.executemany(
                    "INSERT INTO matches (home_team,away_team,match_date,match_time,group_name) VALUES ($1,$2,$3,$4,$5)",
                    new_matches)
            await db.execute("INSERT INTO db_version (version) VALUES (2) ON CONFLICT DO NOTHING")

        print("✅ Datenbank initialisiert")

# ─── Live Score System ────────────────────────────────────────────
async def fetch_live_scores():
    if not FOOTBALL_API_KEY:
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{FOOTBALL_API_URL}/competitions/{WC_2026_ID}/matches",
                headers={"X-Auth-Token": FOOTBALL_API_KEY},
                timeout=10)
            if r.status_code != 200:
                return
            data = r.json()
            matches = data.get("matches", [])

        async with pool.acquire() as db:
            for m in matches:
                status = m.get("status", "")
                score = m.get("score", {})
                ft = score.get("fullTime", {})
                home_score = ft.get("home")
                away_score = ft.get("away")

                if status in ("FINISHED",): db_status = "done"
                elif status in ("IN_PLAY", "PAUSED", "HALFTIME"): db_status = "live"
                else: db_status = "open"

                home_name = m.get("homeTeam", {}).get("shortName", "")
                away_name = m.get("awayTeam", {}).get("shortName", "")
                if not home_name or not away_name: continue

                row = await db.fetchrow(
                    "SELECT id FROM matches WHERE status != 'done' AND (home_team LIKE $1 OR away_team LIKE $2)",
                    f"%{home_name[:6]}%", f"%{away_name[:6]}%")

                if row and db_status in ("done", "live"):
                    match_id = row['id']
                    if home_score is not None and away_score is not None:
                        await db.execute(
                            "UPDATE matches SET status=$1, home_score=$2, away_score=$3 WHERE id=$4",
                            db_status, home_score, away_score, match_id)
                        if db_status == "done":
                            await evaluate_tips(db, match_id, home_score, away_score)
                            await update_ko_brackets(db)
    except Exception as e:
        print(f"Live score fetch error: {e}")


# ─── KO Advancement Logic ─────────────────────────────────────────────────────

# WM 2026 Sechzehntelfinale Mapping
# Basierend auf dem offiziellen WM 2026 Spielplan
# Format: (SF_group_name, 'home'|'away', source_type, source_id)
# source_type: 'gruppe_1', 'gruppe_2', 'beste_3'
# Die besten 3. der Gruppen werden nach Punkten/Tordifferenz vergeben

SF_MAPPING = {
    # SF1: 1.A vs 2.J
    'SF1': [('gruppe_1', 'A'), ('gruppe_2', 'J')],
    # SF2: 1.B vs 2.K
    'SF2': [('gruppe_1', 'B'), ('gruppe_2', 'K')],
    # SF3: 1.C vs beste_3
    'SF3': [('gruppe_1', 'C'), ('beste_3', None)],
    # SF4: 1.D vs 2.G
    'SF4': [('gruppe_1', 'D'), ('gruppe_2', 'G')],
    # SF5: 1.E vs beste_3
    'SF5': [('gruppe_1', 'E'), ('beste_3', None)],
    # SF6: 1.F vs 2.I
    'SF6': [('gruppe_1', 'F'), ('gruppe_2', 'I')],
    # SF7: 1.G vs 2.D
    'SF7': [('gruppe_1', 'G'), ('gruppe_2', 'D')],
    # SF8: 1.H vs beste_3
    'SF8': [('gruppe_1', 'H'), ('beste_3', None)],
    # SF9: 1.I vs 2.E
    'SF9': [('gruppe_1', 'I'), ('gruppe_2', 'E')],
    # SF10: 1.J vs 2.A
    'SF10': [('gruppe_1', 'J'), ('gruppe_2', 'A')],
    # SF11: 1.K vs 2.B
    'SF11': [('gruppe_1', 'K'), ('gruppe_2', 'B')],
    # SF12: 1.L vs beste_3
    'SF12': [('gruppe_1', 'L'), ('beste_3', None)],
    # SF13: 2.C vs beste_3
    'SF13': [('gruppe_2', 'C'), ('beste_3', None)],
    # SF14: 2.F vs beste_3
    'SF14': [('gruppe_2', 'F'), ('beste_3', None)],
    # SF15: 2.H vs beste_3
    'SF15': [('gruppe_2', 'H'), ('beste_3', None)],
    # SF16: 2.L vs beste_3
    'SF16': [('gruppe_2', 'L'), ('beste_3', None)],
}

# KO Advancement: welcher Sieger/Verlierer kommt in welches nächste Spiel
# Format: {ziel_group: [(quelle_group, 'home'|'away', 'winner'|'loser'), ...]}
KO_ADVANCEMENT = {
    'AF1':  [('SF1',  'home', 'winner'), ('SF2',  'away', 'winner')],
    'AF2':  [('SF3',  'home', 'winner'), ('SF4',  'away', 'winner')],
    'AF3':  [('SF5',  'home', 'winner'), ('SF6',  'away', 'winner')],
    'AF4':  [('SF7',  'home', 'winner'), ('SF8',  'away', 'winner')],
    'AF5':  [('SF9',  'home', 'winner'), ('SF10', 'away', 'winner')],
    'AF6':  [('SF11', 'home', 'winner'), ('SF12', 'away', 'winner')],
    'AF7':  [('SF13', 'home', 'winner'), ('SF14', 'away', 'winner')],
    'AF8':  [('SF15', 'home', 'winner'), ('SF16', 'away', 'winner')],
    'VF1':  [('AF1',  'home', 'winner'), ('AF2',  'away', 'winner')],
    'VF2':  [('AF3',  'home', 'winner'), ('AF4',  'away', 'winner')],
    'VF3':  [('AF5',  'home', 'winner'), ('AF6',  'away', 'winner')],
    'VF4':  [('AF7',  'home', 'winner'), ('AF8',  'away', 'winner')],
    'HF1':  [('VF1',  'home', 'winner'), ('VF3',  'away', 'winner')],
    'HF2':  [('VF2',  'home', 'winner'), ('VF4',  'away', 'winner')],
    'P3':   [('HF1',  'home', 'loser'),  ('HF2',  'away', 'loser')],
    'FIN':  [('HF1',  'home', 'winner'), ('HF2',  'away', 'winner')],
}

async def get_gruppe_standing(db, gruppe: str):
    """Berechnet die Tabelle einer Gruppe und gibt sie sortiert zurück."""
    matches = await db.fetch(
        "SELECT home_team, away_team, home_score, away_score FROM matches WHERE group_name=$1 AND status='done'",
        gruppe
    )
    all_teams = await db.fetch(
        "SELECT DISTINCT home_team FROM matches WHERE group_name=$1 UNION SELECT DISTINCT away_team FROM matches WHERE group_name=$1",
        gruppe
    )
    teams = [r[0] for r in all_teams]
    st = {t: {'pts':0,'gd':0,'gf':0,'sp':0} for t in teams}
    for m in matches:
        h, a = m['home_team'], m['away_team']
        hs, as_ = m['home_score'], m['away_score']
        st[h]['sp']+=1; st[a]['sp']+=1
        st[h]['gf']+=hs; st[h]['gd']+=hs-as_
        st[a]['gf']+=as_; st[a]['gd']+=as_-hs
        if hs>as_: st[h]['pts']+=3
        elif hs<as_: st[a]['pts']+=3
        else: st[h]['pts']+=1; st[a]['pts']+=1
    sorted_teams = sorted(teams, key=lambda t: (st[t]['pts'], st[t]['gd'], st[t]['gf']), reverse=True)
    # Prüfen ob alle Gruppenspiele fertig sind (jede Gruppe hat 6 Spiele)
    total = await db.fetchval("SELECT COUNT(*) FROM matches WHERE group_name=$1", gruppe)
    done = await db.fetchval("SELECT COUNT(*) FROM matches WHERE group_name=$1 AND status='done'", gruppe)
    complete = (done == total)
    return sorted_teams, st, complete

async def get_ko_winner(db, group_name: str):
    """Gibt den Sieger eines abgeschlossenen KO-Spiels zurück."""
    match = await db.fetchrow(
        "SELECT home_team, away_team, home_score, away_score, status FROM matches WHERE group_name=$1",
        group_name
    )
    if not match or match['status'] != 'done': return None, None
    if match['home_score'] > match['away_score']:
        return match['home_team'], match['away_team']
    elif match['away_score'] > match['home_score']:
        return match['away_team'], match['home_team']
    return None, None  # Unentschieden (sollte in KO nicht vorkommen)

async def update_ko_brackets(db):
    """
    Aktualisiert alle KO-Spiele basierend auf abgeschlossenen Gruppen/KO-Spielen.
    Wird nach jedem Ergebnis-Update aufgerufen.
    """
    updated = []

    # 1. Sechzehntelfinale aus Gruppenphase befüllen
    for sf_group, sources in SF_MAPPING.items():
        sf_match = await db.fetchrow(
            "SELECT id, home_team, away_team FROM matches WHERE group_name=$1", sf_group
        )
        if not sf_match: continue

        new_home = sf_match['home_team']
        new_away = sf_match['away_team']
        changed = False

        for i, (src_type, src_gruppe) in enumerate(sources):
            team = None
            if src_type in ('gruppe_1', 'gruppe_2'):
                sorted_teams, st, complete = await get_gruppe_standing(db, src_gruppe)
                if complete and sorted_teams:
                    rank = 0 if src_type == 'gruppe_1' else 1
                    if len(sorted_teams) > rank:
                        team = sorted_teams[rank]
            elif src_type == 'beste_3':
                # Beste Dritte: komplexe Logik, erstmal Platzhalter
                team = None  # Wird separat berechnet

            if team:
                if i == 0 and sf_match['home_team'] != team:
                    new_home = team
                    changed = True
                elif i == 1 and sf_match['away_team'] != team:
                    new_away = team
                    changed = True

        if changed:
            await db.execute(
                "UPDATE matches SET home_team=$1, away_team=$2 WHERE group_name=$3",
                new_home, new_away, sf_group
            )
            updated.append(sf_group)

    # 2. KO-Runden aus vorherigen KO-Spielen befüllen
    for target_group, sources in KO_ADVANCEMENT.items():
        target = await db.fetchrow(
            "SELECT id, home_team, away_team FROM matches WHERE group_name=$1", target_group
        )
        if not target: continue

        new_home = target['home_team']
        new_away = target['away_team']
        changed = False

        for src_group, slot, result_type in sources:
            winner, loser = await get_ko_winner(db, src_group)
            team = winner if result_type == 'winner' else loser
            if not team: continue

            placeholder = f"Sieger {src_group}" if result_type == 'winner' else f"Verlierer {src_group}"

            if slot == 'home' and (target['home_team'] == placeholder or target['home_team'] != team):
                if target['home_team'] != team:
                    new_home = team
                    changed = True
            elif slot == 'away' and (target['away_team'] == placeholder or target['away_team'] != team):
                if target['away_team'] != team:
                    new_away = team
                    changed = True

        if changed:
            await db.execute(
                "UPDATE matches SET home_team=$1, away_team=$2 WHERE group_name=$3",
                new_home, new_away, target_group
            )
            updated.append(target_group)

    if updated:
        print(f"KO-Brackets aktualisiert: {updated}")
    return updated

async def evaluate_tips(db, match_id: int, home_score: int, away_score: int):
    tips = await db.fetch(
        "SELECT id, user_id, home_tip, away_tip FROM tips WHERE match_id=$1 AND points IS NULL", match_id)
    for tip in tips:
        ht, at = tip['home_tip'], tip['away_tip']
        if ht == home_score and at == away_score: pts = 3
        elif (ht>at and home_score>away_score) or (ht<at and home_score<away_score) or (ht==at and home_score==away_score): pts = 1
        else: pts = 0
        await db.execute("UPDATE tips SET points=$1, evaluated_at=NOW() WHERE id=$2", pts, tip["id"])

async def close_expired_tips():
    now = datetime.now(timezone.utc)
    async with pool.acquire() as db:
        matches = await db.fetch("SELECT id, match_date, match_time FROM matches WHERE status='open'")
        for m in matches:
            try:
                dt = datetime.strptime(f"{m['match_date']} {m['match_time']}", "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
                if now >= dt:
                    await db.execute("UPDATE matches SET status='closed' WHERE id=$1 AND status='open'", m['id'])
                    all_users = await db.fetch("SELECT id FROM users")
                    for u in all_users:
                        await db.execute(
                            "INSERT INTO tips (user_id, match_id, home_tip, away_tip, points) VALUES ($1,$2,0,0,0) ON CONFLICT DO NOTHING",
                            u['id'], m['id'])
            except Exception:
                pass

async def live_update_loop():
    while True:
        await asyncio.sleep(60)
        await close_expired_tips()
        await fetch_live_scores()

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    await init_db()
    asyncio.create_task(live_update_loop())

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

async def get_user(token):
    if not token: return None
    async with pool.acquire() as db:
        return await db.fetchrow("SELECT * FROM users WHERE session_token=$1", token)

class RegisterBody(BaseModel):
    username: str
    email: str
    password: str

class LoginBody(BaseModel):
    email: str
    password: str

class TipBody(BaseModel):
    match_id: int
    home_tip: int
    away_tip: int

@app.post("/api/register")
async def register(body: RegisterBody, response: Response):
    if len(body.username) < 2: raise HTTPException(400, "Benutzername zu kurz")
    if len(body.password) < 8: raise HTTPException(400, "Passwort zu kurz")
    token = secrets.token_urlsafe(32)
    async with pool.acquire() as db:
        try:
            await db.execute(
                "INSERT INTO users (username,email,password_hash,session_token) VALUES ($1,$2,$3,$4)",
                body.username, body.email, hash_pw(body.password), token)
        except Exception: raise HTTPException(400, "E-Mail bereits registriert")
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=2592000)
    return {"ok": True, "username": body.username}

@app.post("/api/login")
async def login(body: LoginBody, response: Response):
    async with pool.acquire() as db:
        user = await db.fetchrow(
            "SELECT * FROM users WHERE email=$1 AND password_hash=$2",
            body.email, hash_pw(body.password))
    if not user: raise HTTPException(401, "E-Mail oder Passwort falsch")
    token = secrets.token_urlsafe(32)
    async with pool.acquire() as db:
        await db.execute("UPDATE users SET session_token=$1 WHERE id=$2", token, user['id'])
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=2592000)
    return {"ok": True, "username": user['username']}

@app.get("/auth/discord")
async def discord_login():
    return RedirectResponse(f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT}&response_type=code&scope=identify+email")

@app.get("/auth/discord/callback")
async def discord_callback(code: str, response: Response):
    async with httpx.AsyncClient() as client:
        tr = await client.post("https://discord.com/api/oauth2/token", data={
            "client_id": DISCORD_CLIENT_ID, "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code", "code": code, "redirect_uri": DISCORD_REDIRECT})
        td = tr.json()
        ur = await client.get("https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {td['access_token']}"})
        du = ur.json()
    did = du["id"]
    uname = du.get("global_name") or du.get("display_name") or du["username"]
    avatar_hash = du.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        av = f"https://cdn.discordapp.com/avatars/{did}/{avatar_hash}.{ext}?size=256"
    else:
        default_idx = (int(did) >> 22) % 6
        av = f"https://cdn.discordapp.com/embed/avatars/{default_idx}.png"
    token = secrets.token_urlsafe(32)
    async with pool.acquire() as db:
        ex = await db.fetchrow("SELECT id FROM users WHERE discord_id=$1", did)
        if ex:
            await db.execute("UPDATE users SET session_token=$1,avatar=$2 WHERE discord_id=$3", token, av, did)
        else:
            await db.execute(
                "INSERT INTO users (discord_id,username,avatar,session_token) VALUES ($1,$2,$3,$4)",
                did, uname, av, token)
    r = RedirectResponse(url="/")
    r.set_cookie("session", token, httponly=True, samesite="lax", max_age=2592000)
    return r

@app.get("/api/me")
async def me(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    return {"id": user['id'], "username": user['username'], "avatar": user['avatar']}

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}

@app.get("/api/matches")
async def matches():
    async with pool.acquire() as db:
        rows = await db.fetch("SELECT * FROM matches ORDER BY match_date,match_time")
    return [{"id":r['id'],"home":r['home_team'],"away":r['away_team'],"date":r['match_date'],
             "time":r['match_time'],"group":r['group_name'],"home_score":r['home_score'],
             "away_score":r['away_score'],"status":r['status']} for r in rows]

@app.get("/api/tips")
async def get_tips(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    async with pool.acquire() as db:
        rows = await db.fetch("SELECT match_id,home_tip,away_tip,points FROM tips WHERE user_id=$1", user['id'])
    return {r['match_id']: {"home":r['home_tip'],"away":r['away_tip'],"points":r['points']} for r in rows}

@app.post("/api/tips")
async def save_tip(body: TipBody, request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    async with pool.acquire() as db:
        m = await db.fetchrow("SELECT status FROM matches WHERE id=$1", body.match_id)
        if not m or m['status'] != "open": raise HTTPException(400, "Tipp nicht mehr möglich")
        await db.execute(
            "INSERT INTO tips (user_id,match_id,home_tip,away_tip) VALUES ($1,$2,$3,$4) ON CONFLICT(user_id,match_id) DO UPDATE SET home_tip=EXCLUDED.home_tip,away_tip=EXCLUDED.away_tip",
            user['id'], body.match_id, body.home_tip, body.away_tip)
    return {"ok": True}

@app.get("/api/wm-champion")
async def get_wm_champion(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401)
    async with pool.acquire() as db:
        row = await db.fetchrow("SELECT champion, points FROM wm_champions WHERE user_id=$1", user["id"])
        # Check if opening match has started (first match in DB by date)
        first = await db.fetchrow("SELECT status FROM matches ORDER BY id LIMIT 1")
        locked = first and first["status"] != "open"
        return {"champion": row["champion"] if row else None, "points": row["points"] if row else None, "locked": locked}

@app.post("/api/wm-champion")
async def set_wm_champion(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401)
    data = await request.json()
    champion = data.get("champion", "").strip()
    if not champion: raise HTTPException(400, "Kein Team angegeben")
    async with pool.acquire() as db:
        # Check if opening match has started
        first = await db.fetchrow("SELECT status FROM matches ORDER BY id LIMIT 1")
        if first and first["status"] != "open":
            raise HTTPException(400, "Tippabgabe geschlossen – Eröffnungsspiel hat begonnen")
        await db.execute("""INSERT INTO wm_champions (user_id, champion)
            VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET champion=$2, tipped_at=NOW()""",
            user["id"], champion)
    return {"ok": True}

@app.post("/api/admin/evaluate-champion")
async def evaluate_champion(request: Request):
    if not await is_admin(request): raise HTTPException(403)
    data = await request.json()
    actual_winner = data.get("winner", "")
    if not actual_winner: raise HTTPException(400)
    async with pool.acquire() as db:
        tips = await db.fetch("SELECT id, user_id, champion FROM wm_champions")
        for t in tips:
            pts = 15 if t["champion"] == actual_winner else 0
            await db.execute("UPDATE wm_champions SET points=$1 WHERE id=$2", pts, t["id"])
    return {"ok": True, "evaluated": len(tips)}

@app.get("/api/rankings")
async def rankings(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    async with pool.acquire() as db:
        rows = await db.fetch("""SELECT u.username,u.avatar,
            COALESCE(SUM(t.points),0) + COALESCE(MAX(wc.points),0) as pts,
            COALESCE(SUM(t.points),0) as tip_pts,
            COALESCE(MAX(wc.points),0) as champion_pts,
            COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as evaluated,
            COUNT(t.id) as total,
            wc.champion as wm_tip
            FROM users u
            LEFT JOIN tips t ON u.id=t.user_id
            LEFT JOIN wm_champions wc ON u.id=wc.user_id
            GROUP BY u.id, wc.champion ORDER BY pts DESC""")
    return [{"username":r['username'],"avatar":r['avatar'],"points":r['pts'],
             "tip_points":r['tip_pts'],"champion_points":r['champion_pts'],
             "evaluated":r['evaluated'],"total":r['total'],"wm_tip":r['wm_tip']} for r in rows]

@app.get("/api/results")
async def results():
    async with pool.acquire() as db:
        rows = await db.fetch("""SELECT m.home_team,m.away_team,m.home_score,m.away_score,
            u.username,t.home_tip,t.away_tip,t.points
            FROM matches m JOIN tips t ON m.id=t.match_id JOIN users u ON t.user_id=u.id
            WHERE m.status='done' ORDER BY m.match_date DESC""")
    grouped = {}
    for r in rows:
        key = f"{r['home_team']} {r['home_score']}:{r['away_score']} {r['away_team']}"
        if key not in grouped: grouped[key] = {"match":key,"tips":[]}
        grouped[key]["tips"].append({"username":r['username'],"tip":f"{r['home_tip']}:{r['away_tip']}","points":r['points']})
    return list(grouped.values())

class ProfileBody(BaseModel):
    username: str
    avatar_url: str = ""

@app.post("/api/profile")
async def update_profile(body: ProfileBody, request: Request, response: Response):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    if body.username and len(body.username) < 2: raise HTTPException(400, "Benutzername zu kurz")
    async with pool.acquire() as db:
        try:
            new_name = body.username or user['username']
            new_avatar = body.avatar or body.avatar_url or user['avatar']
            await db.execute("UPDATE users SET username=$1, avatar=$2 WHERE id=$3",
                new_name, new_avatar, user['id'])
            row = await db.fetchrow("SELECT * FROM users WHERE id=$1", user['id'])
            return {"id": row['id'], "username": row['username'], "avatar": row['avatar']}
        except Exception as e:
            raise HTTPException(400, str(e))


@app.post("/api/upload-avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Nur Bilder erlaubt")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Bild zu groß (max. 5MB)")
    b64 = base64.b64encode(data).decode()
    data_url = f"data:{file.content_type};base64,{b64}"
    async with pool.acquire() as db:
        await db.execute("UPDATE users SET avatar=$1 WHERE id=$2", data_url, user['id'])
    return {"ok": True, "avatar": data_url}

@app.get("/api/admin/status")
async def admin_status(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    async with pool.acquire() as db:
        users = await db.fetchval("SELECT COUNT(*) FROM users")
        matches = await db.fetchval("SELECT COUNT(*) FROM matches")
        tips = await db.fetchval("SELECT COUNT(*) FROM tips")
        version = await db.fetchval("SELECT MAX(version) FROM db_version")
    return {"users": users, "matches": matches, "tips": tips, "db_version": version}

@app.get("/api/live")
async def live_scores():
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT id, home_team, away_team, home_score, away_score, status, match_date, match_time FROM matches ORDER BY match_date, match_time")
    return [{"id":r['id'],"home":r['home_team'],"away":r['away_team'],"home_score":r['home_score'],
             "away_score":r['away_score'],"status":r['status'],"date":r['match_date'],"time":r['match_time']} for r in rows]

@app.post("/api/admin/fetch-scores")
async def manual_fetch(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    await fetch_live_scores()
    async with pool.acquire() as db:
        await update_ko_brackets(db)
    return {"ok": True, "message": "Scores aktualisiert"}

@app.post("/api/admin/update-brackets")
async def manual_update_brackets(request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        updated = await update_ko_brackets(db)
    return {"ok": True, "updated": updated}

# ─── Admin ────────────────────────────────────────────────────────
ADMIN_DISCORD_IDS = os.environ.get("ADMIN_DISCORD_IDS", "").split(",")

async def is_admin(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: return False
    discord_id = user['discord_id'] or ""
    return discord_id in ADMIN_DISCORD_IDS or user['id'] == 1

@app.get("/api/admin/users")
async def admin_get_users(request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        rows = await db.fetch("""
            SELECT u.id, u.discord_id, u.username, u.email, u.avatar, u.joined_at,
                   COUNT(t.id) as tips, COALESCE(SUM(t.points), 0) as pts
            FROM users u LEFT JOIN tips t ON u.id=t.user_id
            GROUP BY u.id ORDER BY u.joined_at DESC""")
    return [{"id":r['id'],"discord_id":r['discord_id'],"username":r['username'],"email":r['email'],
             "avatar":r['avatar'],"joined_at":str(r['joined_at']),"tips":r['tips'],"points":r['pts']} for r in rows]

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        await db.execute("DELETE FROM tips WHERE user_id=$1", user_id)
        await db.execute("DELETE FROM users WHERE id=$1", user_id)
    return {"ok": True}

@app.post("/api/admin/reset-users")
async def admin_reset_users(request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        await db.execute("DELETE FROM tips")
        await db.execute("DELETE FROM users")
    return {"ok": True, "message": "Alle Nutzer gelöscht"}

@app.post("/api/admin/reset-tips")
async def admin_reset_tips(request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        await db.execute("DELETE FROM tips")
    return {"ok": True, "message": "Alle Tipps zurückgesetzt"}

@app.post("/api/admin/reset-user-tips/{user_id}")
async def admin_reset_user_tips(user_id: int, request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        await db.execute("DELETE FROM tips WHERE user_id=$1", user_id)
    return {"ok": True}

@app.post("/api/admin/result")
async def admin_set_result(request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    body = await request.json()
    match_id = body.get("match_id")
    home_score = body.get("home_score")
    away_score = body.get("away_score")
    async with pool.acquire() as db:
        await db.execute(
            "UPDATE matches SET home_score=$1, away_score=$2, status='done' WHERE id=$3",
            home_score, away_score, match_id)
        tips = await db.fetch(
            "SELECT id,user_id,home_tip,away_tip FROM tips WHERE match_id=$1 AND points IS NULL", match_id)
        for tip in tips:
            ht, at = tip['home_tip'], tip['away_tip']
            if ht == home_score and at == away_score: pts = 3
            elif (ht>at and home_score>away_score) or (ht<at and home_score<away_score) or (ht==at and home_score==away_score): pts = 1
            else: pts = 0
            await db.execute("UPDATE tips SET points=$1, evaluated_at=NOW() WHERE id=$2", pts, tip["id"])
        await update_ko_brackets(db)
    return {"ok": True}

@app.get("/api/admin/matches")
async def admin_get_matches(request: Request):
    if not await is_admin(request): raise HTTPException(403, "Kein Zugriff")
    async with pool.acquire() as db:
        rows = await db.fetch("SELECT * FROM matches ORDER BY match_date,match_time")
    return [{"id":r['id'],"home":r['home_team'],"away":r['away_team'],"date":r['match_date'],
             "time":r['match_time'],"group":r['group_name'],"home_score":r['home_score'],
             "away_score":r['away_score'],"status":r['status']} for r in rows]

@app.get("/api/admin/check")
async def admin_check(request: Request):
    return {"is_admin": await is_admin(request)}

app.mount("/", StaticFiles(directory="web/public", html=True), name="static")
