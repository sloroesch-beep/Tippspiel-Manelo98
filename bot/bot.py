import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import os
from datetime import datetime, timezone

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
WEB_URL = os.environ.get("WEB_URL", "https://web-production-7f103.up.railway.app")
ADMIN_ROLE = "Admin"
DB = "tippspiel.db"

ERINNERUNGEN_CHANNEL_ID = int(os.environ.get("ERINNERUNGEN_CHANNEL_ID", "0"))
STAND_CHANNEL_ID = int(os.environ.get("STAND_CHANNEL_ID", "0"))
TEILNEHMER_CHANNEL_ID = int(os.environ.get("TEILNEHMER_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def get_ch(guild, ch_id):
    return guild.get_channel(ch_id) if ch_id else None

# ─── Events ────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Tippspiel Bot online als {bot.user}")
    reminder_loop.start()
    daily_standings.start()

# ─── Slash Commands ────────────────────────────────────────────────

@tree.command(name="anmelden", description="Beim WM Tippspiel anmelden")
async def anmelden(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT username FROM users WHERE discord_id=?", (str(interaction.user.id),)) as c:
            user = await c.fetchone()

    if user:
        embed = discord.Embed(
            title="✅ Du bist bereits angemeldet!",
            description=f"Willkommen zurück, **{user[0]}**!\n\n🌐 [Zum Tippspiel]({WEB_URL})",
            color=0x2ecc71
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="🏆 WM Tippspiel 2026 — Anmeldung",
        description=f"Melde dich jetzt an und tippe deine Ergebnisse!\n\n🌐 [Zum Tippspiel]({WEB_URL})\n\nDu kannst dich mit deinem Discord-Account anmelden — Name und Profilbild werden automatisch übernommen.",
        color=0xffcc00
    )
    embed.set_footer(text="Fanclub Manelo98 | WM Tippspiel 2026")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="tabelle", description="Aktuelle Rangliste anzeigen")
async def tabelle(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT u.username, COALESCE(SUM(t.points),0) as pts,
                   COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as tips
            FROM users u LEFT JOIN tips t ON u.discord_id=t.user_id
            GROUP BY u.id ORDER BY pts DESC LIMIT 10
        """) as c:
            rows = await c.fetchall()

    if not rows:
        await interaction.response.send_message("Noch keine Mitspieler!", ephemeral=True)
        return

    medals = ["🥇","🥈","🥉"]
    desc = ""
    for i, (name, pts, tips) in enumerate(rows):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        desc += f"{medal} **{name}** — {pts} Punkte _{tips} Tipps_\n"

    embed = discord.Embed(
        title="🏆 WM 2026 — Aktuelle Rangliste",
        description=desc,
        color=0xffcc00
    )
    embed.add_field(name="🌐 Vollständige Tabelle", value=f"[Zum Tippspiel]({WEB_URL})", inline=False)
    embed.set_footer(text=f"Fanclub Manelo98 | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="tippen", description="Link zum Spielplan öffnen")
async def tippen(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Jetzt tippen!",
        description=f"Gib deine Tipps für alle WM-Spiele ab:\n\n🌐 [Zum Spielplan]({WEB_URL})\n\n⏰ Tipps sind nur bis zum Anpfiff möglich!",
        color=0x5865f2
    )
    embed.set_footer(text="3 Pkt = exakt | 1 Pkt = Tendenz | 0 Pkt = falsch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="meinetipps", description="Deine eigenen Tipps anzeigen")
async def meinetipps(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT m.home_team, m.away_team, t.home_tip, t.away_tip, t.points, m.status
            FROM tips t JOIN matches m ON t.match_id=m.id
            WHERE t.user_id=? ORDER BY m.match_date, m.match_time LIMIT 15
        """, (str(interaction.user.id),)) as c:
            tips = await c.fetchall()

    if not tips:
        embed = discord.Embed(
            title="Noch keine Tipps",
            description=f"Du hast noch keine Tipps abgegeben.\n🌐 [Jetzt tippen]({WEB_URL})",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    desc = ""
    total = 0
    for home, away, ht, at, pts, status in tips:
        if status == "done" and pts is not None:
            icon = "✅" if pts == 3 else ("〽️" if pts == 1 else "❌")
            desc += f"{icon} {home} **{ht}:{at}** {away} → +{pts} Pkt\n"
            total += pts
        else:
            desc += f"⏳ {home} **{ht}:{at}** {away}\n"

    embed = discord.Embed(
        title=f"Deine Tipps — {interaction.user.display_name}",
        description=desc,
        color=0x5865f2
    )
    embed.add_field(name="Gesamtpunkte", value=f"**{total} Punkte**", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="spielplan", description="Nächste Spiele anzeigen")
async def spielplan(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT home_team, away_team, match_date, match_time, group_name FROM matches WHERE status='open' ORDER BY match_date, match_time LIMIT 6"
        ) as c:
            matches = await c.fetchall()

    if not matches:
        await interaction.response.send_message("Keine offenen Spiele.", ephemeral=True)
        return

    desc = ""
    for home, away, date, time, grp in matches:
        desc += f"🗓️ **{home}** vs **{away}** — {date} {time} Uhr _(Gruppe {grp})_\n"

    embed = discord.Embed(
        title="📅 Nächste Spiele",
        description=desc + f"\n🌐 [Alle Tipps abgeben]({WEB_URL})",
        color=0x0f2744
    )
    await interaction.response.send_message(embed=embed)

# ─── API Endpunkt für Web-App Begrüßung ───────────────────────────
# Die Web-App ruft /api/welcome auf wenn sich jemand anmeldet
# Der Bot hört auf diese Anfragen über die DB

async def check_new_members():
    """Prüft ob neue Mitglieder sich angemeldet haben und begrüßt sie"""
    async with aiosqlite.connect(DB) as db:
        # Prüfe ob welcomed Spalte existiert
        try:
            await db.execute("ALTER TABLE users ADD COLUMN welcomed INTEGER DEFAULT 0")
            await db.commit()
        except:
            pass

        # Hole alle noch nicht begrüßten Nutzer
        async with db.execute(
            "SELECT discord_id, username FROM users WHERE welcomed=0 OR welcomed IS NULL"
        ) as c:
            new_members = await c.fetchall()

        for discord_id, username in new_members:
            for guild in bot.guilds:
                channel = get_ch(guild, TEILNEHMER_CHANNEL_ID)
                if channel:
                    # Versuche Discord-Member zu finden
                    member = None
                    if discord_id:
                        try:
                            member = guild.get_member(int(discord_id))
                        except:
                            pass

                    embed = discord.Embed(
                        title="🎉 Neuer Mitspieler im Tippspiel!",
                        description=(
                            f"{'Willkommen ' + member.mention + '!' if member else '🏆'} "
                            f"**{username}** ist dem WM Tippspiel 2026 beigetreten!\n\n"
                            f"Viel Erfolg beim Tippen! ⚽\n"
                            f"🌐 [Zum Tippspiel]({WEB_URL})"
                        ),
                        color=0x2ecc71
                    )
                    if member:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text="Fanclub Manelo98 | WM Tippspiel 2026")
                    await channel.send(embed=embed)

            # Als begrüßt markieren
            await db.execute("UPDATE users SET welcomed=1 WHERE discord_id=? OR username=?", (discord_id, username))
        await db.commit()

# ─── Automatische Tasks ────────────────────────────────────────────

@tasks.loop(minutes=5)
async def reminder_loop():
    """Prüft alle 5 Minuten ob Erinnerungen gesendet werden sollen"""
    now = datetime.now(timezone.utc)

    # Neue Mitglieder begrüßen
    await check_new_members()

    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT home_team, away_team, match_date, match_time, group_name FROM matches WHERE status='open'"
        ) as c:
            matches = await c.fetchall()

    for home, away, date_str, time_str, grp in matches:
        try:
            parts = date_str.split('.')
            dt = datetime.strptime(
                f"{parts[2]}-{parts[1]}-{parts[0]} {time_str}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
            diff = (dt - now).total_seconds() / 60

            # 30 Minuten vor Anpfiff
            if 28 <= diff <= 32:
                for guild in bot.guilds:
                    channel = get_ch(guild, ERINNERUNGEN_CHANNEL_ID)
                    if channel:
                        embed = discord.Embed(
                            title="🚨 Anpfiff in 30 Minuten — Letzte Chance zum Tippen!",
                            description=(
                                f"⚽ **{home}** 🆚 **{away}**\n"
                                f"📅 {date_str} um {time_str} Uhr _(Gruppe {grp})_\n\n"
                                f"⏰ Die Tipp-Abgabe schließt in Kürze!\n"
                                f"🌐 [Jetzt noch schnell tippen]({WEB_URL})"
                            ),
                            color=0xe74c3c
                        )
                        await channel.send(embed=embed)
        except Exception as e:
            print(f"Reminder error: {e}")

@tasks.loop(hours=1)
async def daily_standings():
    """Postet morgens (8 Uhr) und abends (20 Uhr) den aktuellen Stand"""
    now = datetime.now(timezone.utc)
    # 8 UTC = 10 Uhr MESZ, 18 UTC = 20 Uhr MESZ
    if now.hour not in (6, 18):
        return

    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT u.username, COALESCE(SUM(t.points),0) as pts,
                   COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as tips,
                   COUNT(t.id) as total_tips
            FROM users u LEFT JOIN tips t ON u.discord_id=t.user_id
            GROUP BY u.id ORDER BY pts DESC LIMIT 10
        """) as c:
            rows = await c.fetchall()

        async with db.execute("SELECT COUNT(*) FROM matches WHERE status='done'") as c:
            played = (await c.fetchone())[0]

        async with db.execute(
            "SELECT home_team, away_team, match_date, match_time FROM matches WHERE status='open' ORDER BY match_date, match_time LIMIT 3"
        ) as c:
            next_matches = await c.fetchall()

    if not rows:
        return

    medals = ["🥇","🥈","🥉"]
    desc = ""
    for i, (name, pts, tips, total) in enumerate(rows):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        desc += f"{medal} **{name}** — {pts} Punkte _{tips}/{total} Tipps_\n"

    zeitpunkt = "🌅 Morgen" if now.hour == 6 else "🌆 Abend"

    embed = discord.Embed(
        title=f"📊 {zeitpunkt}licher Tippspiel-Stand",
        description=desc,
        color=0x0f2744
    )
    embed.add_field(
        name="📈 Turnier",
        value=f"{played} Spiele gespielt",
        inline=True
    )
    if next_matches:
        next_str = "\n".join([f"⚽ **{h}** vs **{a}** — {d} {t} Uhr" for h, a, d, t in next_matches])
        embed.add_field(name="📅 Nächste Spiele", value=next_str, inline=False)
    embed.add_field(name="🌐 Vollständige Tabelle", value=f"[Zum Tippspiel]({WEB_URL})", inline=False)
    embed.set_footer(text=f"Fanclub Manelo98 | {now.strftime('%d.%m.%Y %H:%M')} UTC")

    for guild in bot.guilds:
        channel = get_ch(guild, STAND_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

@daily_standings.before_loop
async def before_daily():
    await bot.wait_until_ready()

@reminder_loop.before_loop
async def before_reminder():
    await bot.wait_until_ready()

bot.run(DISCORD_TOKEN)
