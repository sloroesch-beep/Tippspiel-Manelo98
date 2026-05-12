import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from datetime import datetime

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
WEB_URL = os.environ.get("WEB_URL", "https://fanclub-manelo98.up.railway.app")
ADMIN_ROLE = "Admin"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DB = "tippspiel.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                avatar TEXT,
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
                user_id TEXT NOT NULL,
                match_id INTEGER NOT NULL,
                home_tip INTEGER NOT NULL,
                away_tip INTEGER NOT NULL,
                points INTEGER DEFAULT NULL,
                UNIQUE(user_id, match_id)
            )
        """)
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    await tree.sync()
    print(f"Fanclub Manelo98 Tippspiel Bot ist online als {bot.user}")

@tree.command(name="anmelden", description="Melde dich beim WM Tippspiel an")
async def register(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM users WHERE discord_id = ?", (str(interaction.user.id),)) as cursor:
            user = await cursor.fetchone()

    if user:
        embed = discord.Embed(
            title="Du bist bereits angemeldet!",
            description=f"Willkommen zurück, **{interaction.user.display_name}**!\n\n"
                        f"[Zum Tippspiel]({WEB_URL})",
            color=0x2ecc71
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO users (discord_id, username, avatar) VALUES (?, ?, ?)",
            (str(interaction.user.id), interaction.user.display_name, str(interaction.user.display_avatar.url))
        )
        await db.commit()

    embed = discord.Embed(
        title="Willkommen beim WM Tippspiel 2026!",
        description=f"Hey **{interaction.user.display_name}**, du bist jetzt dabei!\n\n"
                    f"Tippe jetzt deine ersten Ergebnisse:\n"
                    f"[Zum Spielplan]({WEB_URL})",
        color=0xf1c40f
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Fanclub Manelo98 | WM Tippspiel 2026")
    await interaction.response.send_message(embed=embed, ephemeral=True)

    channel = discord.utils.get(interaction.guild.text_channels, name="tippspiel-wm2026")
    if channel:
        announce = discord.Embed(
            description=f"{interaction.user.mention} ist dem Tippspiel beigetreten!",
            color=0x5865f2
        )
        await channel.send(embed=announce)

@tree.command(name="tabelle", description="Zeigt die aktuelle Rangliste")
async def tabelle(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT u.username, COALESCE(SUM(t.points), 0) as pts,
                   COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as tips
            FROM users u
            LEFT JOIN tips t ON u.discord_id = t.user_id
            GROUP BY u.discord_id
            ORDER BY pts DESC
        """) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message("Noch keine Mitspieler!", ephemeral=True)
        return

    medals = ["🥇", "🥈", "🥉"]
    desc = ""
    for i, (name, pts, tips) in enumerate(rows):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        desc += f"{medal} **{name}** — {pts} Punkte _(_{tips} Tipps_)_\n"

    embed = discord.Embed(
        title="WM 2026 Tippspiel — Rangliste",
        description=desc,
        color=0xf1c40f
    )
    embed.set_footer(text=f"Fanclub Manelo98 | Stand: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="tippen", description="Rufe den Spielplan zum Tippen auf")
async def tippen(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Jetzt tippen!",
        description=f"Öffne den Spielplan und gib deine Tipps ab:\n\n"
                    f"[Zum Spielplan öffnen]({WEB_URL})\n\n"
                    f"Tipps sind bis zum Anpfiff möglich.",
        color=0x5865f2
    )
    embed.set_footer(text="3 Punkte = exaktes Ergebnis | 1 Punkt = richtige Tendenz")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="meinetipps", description="Zeigt deine eigenen Tipps")
async def meinetipps(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT m.home_team, m.away_team, t.home_tip, t.away_tip, t.points, m.status
            FROM tips t
            JOIN matches m ON t.match_id = m.id
            WHERE t.user_id = ?
            ORDER BY m.match_date, m.match_time
        """, (str(interaction.user.id),)) as cursor:
            tips = await cursor.fetchall()

    if not tips:
        embed = discord.Embed(
            title="Noch keine Tipps",
            description=f"Du hast noch keine Tipps abgegeben.\n[Jetzt tippen]({WEB_URL})",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    desc = ""
    total = 0
    for home, away, ht, at, pts, status in tips:
        if status == "done" and pts is not None:
            icon = "✅" if pts == 3 else ("〽️" if pts == 1 else "❌")
            desc += f"{icon} {home} **{ht}:{at}** {away} — +{pts} Pkt\n"
            total += pts
        else:
            desc += f"⏳ {home} **{ht}:{at}** {away}\n"

    embed = discord.Embed(
        title=f"Deine Tipps — {interaction.user.display_name}",
        description=desc,
        color=0x5865f2
    )
    embed.add_field(name="Gesamtpunkte", value=f"**{total}**", inline=True)
    embed.add_field(name="Tipps gesamt", value=f"**{len(tips)}**", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ergebnis", description="(Admin) Trägt ein Spielergebnis ein")
@app_commands.describe(
    match_id="ID des Spiels",
    home_score="Tore Heimteam",
    away_score="Tore Auswärtsteam"
)
async def ergebnis(interaction: discord.Interaction, match_id: int, home_score: int, away_score: int):
    if not any(r.name == ADMIN_ROLE for r in interaction.user.roles):
        await interaction.response.send_message("Nur Admins können Ergebnisse eintragen.", ephemeral=True)
        return

    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)) as cursor:
            match = await cursor.fetchone()

        if not match:
            await interaction.response.send_message(f"Spiel #{match_id} nicht gefunden.", ephemeral=True)
            return

        home_team, away_team = match[1], match[2]
        await db.execute(
            "UPDATE matches SET home_score=?, away_score=?, status='done' WHERE id=?",
            (home_score, away_score, match_id)
        )

        async with db.execute("SELECT * FROM tips WHERE match_id = ?", (match_id,)) as cursor:
            all_tips = await cursor.fetchall()

        results = []
        for tip in all_tips:
            uid, ht, at = tip[1], tip[3], tip[4]
            if ht == home_score and at == away_score:
                pts = 3
            elif (ht > at and home_score > away_score) or \
                 (ht < at and home_score < away_score) or \
                 (ht == at and home_score == away_score):
                pts = 1
            else:
                pts = 0
            await db.execute("UPDATE tips SET points=? WHERE user_id=? AND match_id=?", (pts, uid, match_id))
            results.append((uid, ht, at, pts))

        await db.commit()

    desc = f"**{home_team} {home_score}:{away_score} {away_team}**\n\n"
    for uid, ht, at, pts in results:
        member = interaction.guild.get_member(int(uid))
        name = member.display_name if member else f"<@{uid}>"
        icon = "✅" if pts == 3 else ("〽️" if pts == 1 else "❌")
        desc += f"{icon} {name}: {ht}:{at} → **+{pts} Pkt**\n"

    embed = discord.Embed(
        title="Auswertung abgeschlossen!",
        description=desc,
        color=0x2ecc71
    )
    embed.set_footer(text="Fanclub Manelo98 | WM Tippspiel 2026")
    await interaction.response.send_message(embed=embed)

@tree.command(name="spielplan", description="Zeigt alle offenen Spiele")
async def spielplan(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT id, home_team, away_team, match_date, match_time, group_name FROM matches WHERE status='open' ORDER BY match_date, match_time LIMIT 8"
        ) as cursor:
            matches = await cursor.fetchall()

    if not matches:
        await interaction.response.send_message("Keine offenen Spiele.", ephemeral=True)
        return

    desc = ""
    for mid, home, away, date, time, grp in matches:
        desc += f"`#{mid}` **{home}** vs **{away}** — {date} {time} Uhr _(Gruppe {grp})_\n"

    embed = discord.Embed(
        title="Offene Spiele",
        description=desc + f"\n[Alle Tipps abgeben]({WEB_URL})",
        color=0x0f2744
    )
    embed.set_footer(text="3 Pkt = exakt | 1 Pkt = Tendenz | 0 Pkt = falsch")
    await interaction.response.send_message(embed=embed)

bot.run(DISCORD_TOKEN)
