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
            return await c.fetchone()

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
    async with aiosqlite.connect(DB) as db:
        try:
            await db.execute("INSERT INTO users (username,email,password_hash,session_token) VALUES (?,?,?,?)",
                (body.username, body.email, hash_pw(body.password), token))
            await db.commit()
        except Exception: raise HTTPException(400, "E-Mail bereits registriert")
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=2592000)
    return {"ok": True, "username": body.username}

@app.post("/api/login")
async def login(body: LoginBody, response: Response):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM users WHERE email=? AND password_hash=?",
            (body.email, hash_pw(body.password))) as c:
            user = await c.fetchone()
    if not user: raise HTTPException(401, "E-Mail oder Passwort falsch")
    token = secrets.token_urlsafe(32)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET session_token=? WHERE id=?", (token, user[0]))
        await db.commit()
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=2592000)
    return {"ok": True, "username": user[2]}

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
    did, uname = du["id"], du["username"]
    av = f"https://cdn.discordapp.com/avatars/{did}/{du.get('avatar')}.png" if du.get("avatar") else None
    token = secrets.token_urlsafe(32)
    async with aiosqlite.connect(DB) as db:
        ex = await (await db.execute("SELECT id FROM users WHERE discord_id=?", (did,))).fetchone()
        if ex: await db.execute("UPDATE users SET session_token=?,avatar=? WHERE discord_id=?", (token,av,did))
        else: await db.execute("INSERT INTO users (discord_id,username,avatar,session_token) VALUES (?,?,?,?)", (did,uname,av,token))
        await db.commit()
    r = RedirectResponse(url="/")
    r.set_cookie("session", token, httponly=True, samesite="lax", max_age=2592000)
    return r

@app.get("/api/me")
async def me(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    return {"id": user[0], "username": user[2], "avatar": user[6]}

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}

@app.get("/api/matches")
async def matches():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM matches ORDER BY match_date,match_time") as c:
            rows = await c.fetchall()
    return [{"id":r[0],"home":r[1],"away":r[2],"date":r[3],"time":r[4],"group":r[5],"home_score":r[6],"away_score":r[7],"status":r[8]} for r in rows]

@app.get("/api/tips")
async def get_tips(request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT match_id,home_tip,away_tip,points FROM tips WHERE user_id=?", (user[0],)) as c:
            rows = await c.fetchall()
    return {r[0]: {"home":r[1],"away":r[2],"points":r[3]} for r in rows}

@app.post("/api/tips")
async def save_tip(body: TipBody, request: Request):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    async with aiosqlite.connect(DB) as db:
        m = await (await db.execute("SELECT status FROM matches WHERE id=?", (body.match_id,))).fetchone()
        if not m or m[0] != "open": raise HTTPException(400, "Tipp nicht mehr möglich")
        await db.execute("INSERT INTO tips (user_id,match_id,home_tip,away_tip) VALUES (?,?,?,?) ON CONFLICT(user_id,match_id) DO UPDATE SET home_tip=excluded.home_tip,away_tip=excluded.away_tip",
            (user[0],body.match_id,body.home_tip,body.away_tip))
        await db.commit()
    return {"ok": True}

@app.get("/api/rankings")
async def rankings():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""SELECT u.username,u.avatar,COALESCE(SUM(t.points),0),
            COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END),COUNT(t.id)
            FROM users u LEFT JOIN tips t ON u.id=t.user_id GROUP BY u.id ORDER BY 3 DESC""") as c:
            rows = await c.fetchall()
    return [{"username":r[0],"avatar":r[1],"points":r[2],"evaluated":r[3],"total":r[4]} for r in rows]

@app.get("/api/results")
async def results():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""SELECT m.home_team,m.away_team,m.home_score,m.away_score,
            u.username,t.home_tip,t.away_tip,t.points
            FROM matches m JOIN tips t ON m.id=t.match_id JOIN users u ON t.user_id=u.id
            WHERE m.status='done' ORDER BY m.match_date DESC""") as c:
            rows = await c.fetchall()
    grouped = {}
    for r in rows:
        key = f"{r[0]} {r[2]}:{r[3]} {r[1]}"
        if key not in grouped: grouped[key] = {"match":key,"tips":[]}
        grouped[key]["tips"].append({"username":r[4],"tip":f"{r[5]}:{r[6]}","points":r[7]})
    return list(grouped.values())

app.mount("/", StaticFiles(directory="web/public", html=True), name="static")
