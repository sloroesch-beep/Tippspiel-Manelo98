from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
import base64
import re
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
    # Gruppe C - Brasilien Gruppe
    ("Brasilien","Schottland","14.06.2026","19:00","C"),
    ("Marokko","Haiti","14.06.2026","22:00","C"),
    ("Brasilien","Marokko","19.06.2026","00:00","C"),
    ("Schottland","Haiti","19.06.2026","03:00","C"),
    ("Brasilien","Haiti","24.06.2026","21:00","C"),
    ("Marokko","Schottland","24.06.2026","21:00","C"),
]

KO_MATCHES = [
    # Sechzehntelfinale (28. Juni - 3. Juli)
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
    # Achtelfinale (4. Juli - 7. Juli)
    ("Sieger SF1","Sieger SF2","04.07.2026","22:00","AF1"),
    ("Sieger SF3","Sieger SF4","05.07.2026","01:00","AF2"),
    ("Sieger SF5","Sieger SF6","05.07.2026","22:00","AF3"),
    ("Sieger SF7","Sieger SF8","06.07.2026","01:00","AF4"),
    ("Sieger SF9","Sieger SF10","06.07.2026","22:00","AF5"),
    ("Sieger SF11","Sieger SF12","07.07.2026","01:00","AF6"),
    ("Sieger SF13","Sieger SF14","07.07.2026","22:00","AF7"),
    ("Sieger SF15","Sieger SF16","08.07.2026","01:00","AF8"),
    # Viertelfinale (9. Juli - 11. Juli)
    ("Sieger AF1","Sieger AF2","09.07.2026","22:00","VF1"),
    ("Sieger AF3","Sieger AF4","10.07.2026","22:00","VF2"),
    ("Sieger AF5","Sieger AF6","11.07.2026","19:00","VF3"),
    ("Sieger AF7","Sieger AF8","11.07.2026","22:00","VF4"),
    # Halbfinale (14. & 15. Juli)
    ("Sieger VF1","Sieger VF3","14.07.2026","22:00","HF1"),
    ("Sieger VF2","Sieger VF4","15.07.2026","22:00","HF2"),
    # Spiel um Platz 3 (18. Juli)
    ("Verlierer HF1","Verlierer HF2","18.07.2026","21:00","P3"),
    # Finale (19. Juli)
    ("Sieger HF1","Sieger HF2","19.07.2026","21:00","FIN"),
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
        if count > 0 and count < 100:
            await db.execute("DELETE FROM matches")
            count = 0
        if count == 0:
            all_matches = GRUPPE_MATCHES + KO_MATCHES
            await db.executemany(
                "INSERT INTO matches (home_team,away_team,match_date,match_time,group_name) VALUES (?,?,?,?,?)",
                all_matches)
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
    did = du["id"]
    # Bevorzuge global_name (Anzeigename) statt username (Anmeldename)
    uname = du.get("global_name") or du.get("display_name") or du["username"]
    # Avatar mit korrekter URL und .png oder .gif falls animiert
    avatar_hash = du.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        av = f"https://cdn.discordapp.com/avatars/{did}/{avatar_hash}.{ext}?size=256"
    else:
        # Standard Discord Avatar wenn keiner gesetzt
        discriminator = int(du.get("discriminator", "0") or "0")
        default_idx = (int(did) >> 22) % 6
        av = f"https://cdn.discordapp.com/embed/avatars/{default_idx}.png"
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

class ProfileBody(BaseModel):
    username: str
    avatar_url: str = ""

@app.post("/api/profile")
async def update_profile(body: ProfileBody, request: Request, response: Response):
    user = await get_user(request.cookies.get("session"))
    if not user: raise HTTPException(401, "Nicht angemeldet")
    if len(body.username) < 2: raise HTTPException(400, "Benutzername zu kurz")
    async with aiosqlite.connect(DB) as db:
        try:
            if body.avatar_url:
                await db.execute("UPDATE users SET username=?, avatar=? WHERE id=?",
                    (body.username, body.avatar_url, user[0]))
            else:
                await db.execute("UPDATE users SET username=? WHERE id=?",
                    (body.username, user[0]))
            await db.commit()
        except Exception: raise HTTPException(400, "Benutzername bereits vergeben")
    return {"ok": True, "username": body.username}

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
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET avatar=? WHERE id=?", (data_url, user[0]))
        await db.commit()
    return {"ok": True, "avatar": data_url}

app.mount("/", StaticFiles(directory="web/public", html=True), name="static")
