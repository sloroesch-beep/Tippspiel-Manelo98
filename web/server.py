from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import aiosqlite
import httpx
import os
import secrets
import hashlib
import hmac
from datetime import datetime

app = FastAPI(title="Fanclub Manelo98 — WM Tippspiel 2026")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "tippspiel.db"
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
WEB_URL = os.environ.get("WEB_URL", "https://fanclub-manelo98.up.railway.app")
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE,
                username TEXT NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                avatar TEXT,
                session_token TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                match_date TEXT NOT NULL,
                match_time TEXT NOT NULL,
                group_name TEXT NOT NULL,
                home_score INTEGER DEFAULT NULL,
                away_score INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'open'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                home_tip INTEGER NOT NULL,
                away_tip INTEGER NOT NULL,
                points INTEGER DEFAULT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, match_id)
            )
        """)
        async with db.execute("SELECT COUNT(*) FROM matches") as cursor:
            count = (await cursor.fetchone())[0]
        if count == 0:
            await db.executemany(
                "INSERT INTO matches (home_team, away_team, match_date, match_time, group_name) VALUES (?,?,?,?,?)",
                WM_MATCHES
            )
        await db.commit()

@app.on_event("startup")
async def startup():
    await init_db()

def make_token():
    return secrets.token_urlsafe(32)

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

async def get_user_by_token(token: str):
    if not token:
        return None
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM users WHERE session_token = ?", (token,)) as cursor:
            return await cursor.fetchone()

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
    if len(body.username) < 2:
        raise HTTPException(400, "Benutzername zu kurz")
    if len(body.password) < 8:
        raise HTTPException(400, "Passwort muss mindestens 8 Zeichen haben")
    token = make_token()
    async with aiosqlite.connect(DB) as db:
        try:
            await db.execute(
                "INSERT INTO users (username, email, password_hash, session_token) VALUES (?,?,?,?)",
                (body.username, body.email, hash_password(body.password), token)
            )
            await db.commit()
        except Exception:
            raise HTTPException(400, "E-Mail bereits registriert")
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=60*60*24*30)
    return {"ok": True, "username": body.username}

@app.post("/api/login")
async def login(body: LoginBody, response: Response):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (body.email, hash_password(body.password))
        ) as cursor:
            user = await cursor.fetchone()
    if not user:
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    token = make_token()
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET session_token=? WHERE id=?", (token, user[0]))
        await db.commit()
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=60*60*24*30)
    return {"ok": True, "username": user[2]}

@app.get("/auth/discord")
async def discord_login():
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT}"
        f"&response_type=code"
        f"&scope=identify+email"
    )
    return RedirectResponse(url)

@app.get("/auth/discord/callback")
async def discord_callback(code: str, response: Response):
    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://discord.com/api/oauth2/token", data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT,
        })
        token_data = token_res.json()
        user_res = await client.get("https://discord.com/api/users/@me", headers={
            "Authorization": f"Bearer {token_data['access_token']}"
        })
        discord_user = user_res.json()

    discord_id = discord_user["id"]
    username = discord_user["username"]
    avatar_hash = discord_user.get("avatar")
    avatar = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png" if avatar_hash else None
    session_token = make_token()

    async with aiosqlite.connect(DB) as db:
        existing = await (await db.execute("SELECT id FROM users WHERE discord_id=?", (discord_id,))).fetchone()
        if existing:
            await db.execute("UPDATE users SET session_token=?, avatar=? WHERE discord_id=?", (session_token, avatar, discord_id))
        else:
            await db.execute(
                "INSERT INTO users (discord_id, username, avatar, session_token) VALUES (?,?,?,?)",
                (discord_id, username, avatar, session_token)
            )
        await db.commit()

    resp = RedirectResponse(url="/")
    resp.set_cookie("session", session_token, httponly=True, samesite="lax", max_age=60*60*24*30)
    return resp

@app.get("/api/me")
async def me(request: Request):
    token = request.cookies.get("session")
    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Nicht angemeldet")
    return {"id": user[0], "username": user[2], "avatar": user[6]}

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}

@app.get("/api/matches")
async def matches():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM matches ORDER BY match_date, match_time") as cursor:
            rows = await cursor.fetchall()
    return [{"id":r[0],"home":r[1],"away":r[2],"date":r[3],"time":r[4],"group":r[5],
             "home_score":r[6],"away_score":r[7],"status":r[8]} for r in rows]

@app.get("/api/tips")
async def get_tips(request: Request):
    token = request.cookies.get("session")
    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Nicht angemeldet")
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT match_id, home_tip, away_tip, points FROM tips WHERE user_id=?", (user[0],)) as cursor:
            rows = await cursor.fetchall()
    return {r[0]: {"home": r[1], "away": r[2], "points": r[3]} for r in rows}

@app.post("/api/tips")
async def save_tip(body: TipBody, request: Request):
    token = request.cookies.get("session")
    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Nicht angemeldet")
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT status FROM matches WHERE id=?", (body.match_id,)) as cursor:
            match = await cursor.fetchone()
        if not match or match[0] != "open":
            raise HTTPException(400, "Tipp nicht mehr möglich")
        await db.execute(
            "INSERT INTO tips (user_id, match_id, home_tip, away_tip) VALUES (?,?,?,?) ON CONFLICT(user_id, match_id) DO UPDATE SET home_tip=excluded.home_tip, away_tip=excluded.away_tip",
            (user[0], body.match_id, body.home_tip, body.away_tip)
        )
        await db.commit()
    return {"ok": True}

@app.get("/api/rankings")
async def rankings():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT u.username, u.avatar, COALESCE(SUM(t.points),0) as pts,
                   COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as evaluated,
                   COUNT(t.id) as total
            FROM users u LEFT JOIN tips t ON u.id = t.user_id
            GROUP BY u.id ORDER BY pts DESC
        """) as cursor:
            rows = await cursor.fetchall()
    return [{"username":r[0],"avatar":r[1],"points":r[2],"evaluated":r[3],"total":r[4]} for r in rows]

@app.get("/api/results")
async def results():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT m.home_team, m.away_team, m.home_score, m.away_score,
                   u.username, t.home_tip, t.away_tip, t.points
            FROM matches m
            JOIN tips t ON m.id = t.match_id
            JOIN users u ON t.user_id = u.id
            WHERE m.status = 'done'
            ORDER BY m.match_date DESC, m.match_time DESC
        """) as cursor:
            rows = await cursor.fetchall()
    grouped = {}
    for r in rows:
        key = f"{r[0]} {r[2]}:{r[3]} {r[1]}"
        if key not in grouped:
            grouped[key] = {"match": key, "tips": []}
        grouped[key]["tips"].append({"username":r[4],"tip":f"{r[5]}:{r[6]}","points":r[7]})
    return list(grouped.values())

app.mount("/", StaticFiles(directory="web/public", html=True), name="static")
