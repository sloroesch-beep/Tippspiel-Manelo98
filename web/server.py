from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiosqlite
import httpx
import os
import secrets
import hashlib

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB = "tippspiel.db"
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
WEB_URL = os.environ.get("WEB_URL", "http://localhost:8000")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DISCORD_REDIRECT = f"{WEB_URL}/auth/discord/callback"

WM_MATCHES = [
    ("Deutschland","Frankreich","12.06.2026","21:00","A"),
    ("Portugal","Argentinien","12.06.2026","18:00","A"),
    ("Brasilien","England","13.06.2026","21:00","B"),
    ("Spanien","Niederlande","13.06.2026","18:00","B"),
    ("USA","Mexiko","14.06.2026","21:00","C"),
    ("Japan","Südkorea","14.06.2026","18:00","C"),
    ("Italien","Belgien","15.06.2026","21:00","D"),
    ("Kroatien","Marokko","15.06.2026","18:00","D"),
    ("Deutschland","Portugal","16.06.2026","21:00","A"),
    ("Frankreich","Argentinien","16.06.2026","18:00","A"),
    ("Brasilien","Spanien","17.06.2026","21:00","B"),
    ("England","Niederlande","17.06.2026","18:00","B"),
    ("USA","Japan","18.06.2026","21:00","C"),
    ("Mexiko","Südkorea","18.06.2026","18:00","C"),
    ("Italien","Kroatien","19.06.2026","21:00","D"),
    ("Belgien","Marokko","19.06.2026","18:00","D"),
]

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, discord_id TEXT UNIQUE,
            username TEXT NOT NULL, email TEXT UNIQUE, password_hash TEXT,
            avatar TEXT, session_token TEXT, joined_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT, home_team TEXT NOT NULL,
            away_team TEXT NOT NULL, match_date TEXT NOT NULL, match_time TEXT NOT NULL,
            group_name TEXT NOT NULL, home_score INTEGER DEFAULT NULL,
            away_score INTEGER DEFAULT NULL, status TEXT DEFAULT 'open')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            match_id INTEGER NOT NULL, home_tip INTEGER NOT NULL, away_tip INTEGER NOT NULL,
            points INTEGER DEFAULT NULL, UNIQUE(user_id, match_id))""")
        count = (await (await db.execute("SELECT COUNT(*) FROM matches")).fetchone())[0]
        if count == 0:
            await db.executemany(
                "INSERT INTO matches (home_team,away_team,match_date,match_time,group_name) VALUES (?,?,?,?,?)",
                WM_MATCHES)
        await db.commit()

@app.on_event("startup")
async def startup():
    await init_db()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

async def get_user(token):
    if not token: return None
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM users WHERE session_token=?", (token,)) as c:
