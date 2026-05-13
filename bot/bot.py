import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncpg
import os
from datetime import datetime, timezone

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
WEB_URL = os.environ.get("WEB_URL", "https://web-production-7f103.up.railway.app")
DATABASE_URL = os.environ.get("DATABASE_URL")

ERINNERUNGEN_CHANNEL_ID = int(os.environ.get("ERINNERUNGEN_CHANNEL_ID", "0"))
STAND_CHANNEL_ID = int(os.environ.get("STAND_CHANNEL_ID", "0"))
TEILNEHMER_CHANNEL_ID = int(os.environ.get("TEILNEHMER_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

pool: asyncpg.Pool = None

def get_ch(guild, ch_id):
    return guild.get_channel(ch_id) if ch_id else None

@bot.event
async def on_ready():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    await tree.sync()
    print(f"✅ Tippspiel Bot online als {bot.user}")
    await check_new_members()
    reminder_loop.start()
    daily_standings.start()

async def check_new_members():
    print("Prüfe neue Mitglieder...")
    try:
        async with pool.acquire() as db:
            new_members = await db.fetch(
                "SELECT id, discord_id, username FROM users WHERE welcomed=0 OR welcomed IS NULL")

            print(f"Gefunden: {len(new_members)} neue Mitglieder")

            for member_row in new_members:
                uid = member_row['id']
                discord_id = member_row['discord_id']
                username = member_row['username']

                for guild in bot.guilds:
                    channel = get_ch(guild, TEILNEHMER_CHANNEL_ID)
                    if not channel:
                        print(f"Channel {TEILNEHMER_CHANNEL_ID} nicht gefunden!")
                        continue

                    member = None
                    if discord_id:
                        try:
                            member = guild.get_member(int(discord_id))
                            if not member:
                                member = await guild.fetch_member(int(discord_id))
                        except Exception as e:
                            print(f"Member fetch Fehler: {e}")

                    mention = member.mention if member else ""
                    embed = discord.Embed(
                        title="🎉 Neuer Mitspieler!",
                        description=(
                            f"{mention} **{username}** ist dem WM 2026 Tippspiel von Manelo98 beigetreten. "
                            f"Viel Glück und vor allem Spaß! 🍀⚽\n\n"
                            f"🌐 [Zum Tippspiel]({WEB_URL})"
                        ),
                        color=0x2ecc71
                    )
                    if member:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text="Fanclub Manelo98 | WM Tippspiel 2026")
                    await channel.send(embed=embed)
                    print(f"✅ Begrüßung gesendet für {username}")

                await db.execute("UPDATE users SET welcomed=1 WHERE id=$1", uid)
    except Exception as e:
        print(f"check_new_members Fehler: {e}")

@tree.command(name="anmelden", description="Beim WM Tippspiel anmelden")
async def anmelden(interaction: discord.Interaction):
    async with pool.acquire() as db:
        user = await db.fetchrow("SELECT username FROM users WHERE discord_id=$1", str(interaction.user.id))
    if user:
        embed = discord.Embed(
            title="✅ Du bist bereits angemeldet!",
            description=f"Willkommen zurück, **{user['username']}**!\n\n🌐 [Zum Tippspiel]({WEB_URL})",
            color=0x2ecc71)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    embed = discord.Embed(
        title="🏆 WM Tippspiel 2026 — Anmeldung",
        description=f"Melde dich jetzt an!\n\n🌐 [Zum Tippspiel]({WEB_URL})",
        color=0xffcc00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="tabelle", description="Aktuelle Rangliste anzeigen")
async def tabelle(interaction: discord.Interaction):
    async with pool.acquire() as db:
        rows = await db.fetch("""
            SELECT u.username, COALESCE(SUM(t.points),0) as pts,
                   COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as tips
            FROM users u LEFT JOIN tips t ON u.id=t.user_id
            GROUP BY u.id ORDER BY pts DESC LIMIT 10""")
    if not rows:
        await interaction.response.send_message("Noch keine Mitspieler!", ephemeral=True)
        return
    medals = ["🥇","🥈","🥉"]
    desc = ""
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        desc += f"{medal} **{r['username']}** — {r['pts']} Punkte _{r['tips']} Tipps_\n"
    embed = discord.Embed(title="🏆 WM 2026 — Aktuelle Rangliste", description=desc, color=0xffcc00)
    embed.add_field(name="🌐 Vollständige Tabelle", value=f"[Zum Tippspiel]({WEB_URL})", inline=False)
    embed.set_footer(text=f"Fanclub Manelo98 | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="tippen", description="Link zum Spielplan öffnen")
async def tippen(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Jetzt tippen!",
        description=f"🌐 [Zum Spielplan]({WEB_URL})\n\n⏰ Tipps sind nur bis zum Anpfiff möglich!",
        color=0x5865f2)
    embed.set_footer(text="3 Pkt = exakt | 1 Pkt = Tendenz | 0 Pkt = falsch")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="meinetipps", description="Deine eigenen Tipps anzeigen")
async def meinetipps(interaction: discord.Interaction):
    async with pool.acquire() as db:
        tips = await db.fetch("""
            SELECT m.home_team, m.away_team, t.home_tip, t.away_tip, t.points, m.status
            FROM tips t JOIN matches m ON t.match_id=m.id
            WHERE t.user_id=(SELECT id FROM users WHERE discord_id=$1)
            ORDER BY m.match_date, m.match_time LIMIT 15""", str(interaction.user.id))
    if not tips:
        embed = discord.Embed(title="Noch keine Tipps", description=f"🌐 [Jetzt tippen]({WEB_URL})", color=0xe74c3c)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    desc = ""
    total = 0
    for t in tips:
        if t['status'] == "done" and t['points'] is not None:
            icon = "✅" if t['points'] == 3 else ("〽️" if t['points'] == 1 else "❌")
            desc += f"{icon} {t['home_team']} **{t['home_tip']}:{t['away_tip']}** {t['away_team']} → +{t['points']} Pkt\n"
            total += t['points']
        else:
            desc += f"⏳ {t['home_team']} **{t['home_tip']}:{t['away_tip']}** {t['away_team']}\n"
    embed = discord.Embed(title=f"Deine Tipps — {interaction.user.display_name}", description=desc, color=0x5865f2)
    embed.add_field(name="Gesamtpunkte", value=f"**{total} Punkte**", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="spielplan", description="Nächste Spiele anzeigen")
async def spielplan(interaction: discord.Interaction):
    async with pool.acquire() as db:
        matches = await db.fetch(
            "SELECT home_team, away_team, match_date, match_time, group_name FROM matches WHERE status='open' ORDER BY match_date, match_time LIMIT 6")
    if not matches:
        await interaction.response.send_message("Keine offenen Spiele.", ephemeral=True)
        return
    desc = ""
    for m in matches:
        desc += f"🗓️ **{m['home_team']}** vs **{m['away_team']}** — {m['match_date']} {m['match_time']} Uhr _(Gruppe {m['group_name']})_\n"
    embed = discord.Embed(title="📅 Nächste Spiele", description=desc + f"\n🌐 [Alle Tipps abgeben]({WEB_URL})", color=0x0f2744)
    await interaction.response.send_message(embed=embed)

@tree.command(name="reset_welcomed", description="Test: Begrüßung zurücksetzen (nur Admin)")
async def reset_welcomed(interaction: discord.Interaction):
    ADMIN_IDS = os.environ.get("ADMIN_DISCORD_IDS", "").split(",")
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Kein Zugriff!", ephemeral=True)
        return
    async with pool.acquire() as db:
        await db.execute("UPDATE users SET welcomed=0 WHERE discord_id=$1", str(interaction.user.id))
    await interaction.response.send_message("✅ Deine Begrüßung wurde zurückgesetzt! In max. 5 Min kommt sie.", ephemeral=True)

@tasks.loop(minutes=5)
async def reminder_loop():
    await check_new_members()
    now = datetime.now(timezone.utc)
    async with pool.acquire() as db:
        matches = await db.fetch("SELECT home_team, away_team, match_date, match_time, group_name FROM matches WHERE status='open'")
    for m in matches:
        try:
            parts = m['match_date'].split('.')
            dt = datetime.strptime(f"{parts[2]}-{parts[1]}-{parts[0]} {m['match_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            diff = (dt - now).total_seconds() / 60
            if 28 <= diff <= 32:
                for guild in bot.guilds:
                    channel = get_ch(guild, ERINNERUNGEN_CHANNEL_ID)
                    if channel:
                        embed = discord.Embed(
                            title="🚨 Anpfiff in 30 Minuten — Letzte Chance!",
                            description=f"⚽ **{m['home_team']}** 🆚 **{m['away_team']}**\n📅 {m['match_date']} um {m['match_time']} Uhr _(Gruppe {m['group_name']})_\n\n🌐 [Jetzt tippen]({WEB_URL})",
                            color=0xe74c3c)
                        await channel.send(embed=embed)
        except Exception as e:
            print(f"Reminder Fehler: {e}")

@tasks.loop(hours=1)
async def daily_standings():
    now = datetime.now(timezone.utc)
    if now.hour not in (6, 18):
        return
    async with pool.acquire() as db:
        rows = await db.fetch("""
            SELECT u.username, COALESCE(SUM(t.points),0) as pts,
                   COUNT(CASE WHEN t.points IS NOT NULL THEN 1 END) as tips
            FROM users u LEFT JOIN tips t ON u.id=t.user_id
            GROUP BY u.id ORDER BY pts DESC LIMIT 10""")
        played = await db.fetchval("SELECT COUNT(*) FROM matches WHERE status='done'")
        next_matches = await db.fetch(
            "SELECT home_team, away_team, match_date, match_time FROM matches WHERE status='open' ORDER BY match_date, match_time LIMIT 3")
    if not rows:
        return
    medals = ["🥇","🥈","🥉"]
    desc = ""
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        desc += f"{medal} **{r['username']}** — {r['pts']} Punkte _{r['tips']} Tipps_\n"
    zeitpunkt = "🌅 Morgen" if now.hour == 6 else "🌆 Abend"
    embed = discord.Embed(title=f"📊 {zeitpunkt}licher Tippspiel-Stand", description=desc, color=0x0f2744)
    embed.add_field(name="📈 Turnier", value=f"{played} Spiele gespielt", inline=True)
    if next_matches:
        next_str = "\n".join([f"⚽ **{m['home_team']}** vs **{m['away_team']}** — {m['match_date']} {m['match_time']} Uhr" for m in next_matches])
        embed.add_field(name="📅 Nächste Spiele", value=next_str, inline=False)
    embed.add_field(name="🌐 Vollständige Tabelle", value=f"[Zum Tippspiel]({WEB_URL})", inline=False)
    embed.set_footer(text=f"Fanclub Manelo98 | {now.strftime('%d.%m.%Y')}")
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
