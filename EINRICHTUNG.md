# WM Tippspiel 2026 — Fanclub Manelo98
## Einrichtung Schritt für Schritt

---

### SCHRITT 1 — Discord Bot erstellen (5 Min.)

1. Gehe zu https://discord.com/developers/applications
2. Klick "New Application" → Name: "Tippspiel Manelo98" → Create
3. Links auf "Bot" klicken → "Add Bot"
4. Unter "Token" → "Reset Token" → Token kopieren & sicher speichern ⚠️
5. Unter "Privileged Gateway Intents": alle drei einschalten → Save
6. Links auf "OAuth2" → "URL Generator"
7. Scopes: "bot" + "applications.commands" anhaken
8. Bot Permissions: "Send Messages", "Embed Links", "Read Message History"
9. Generierten Link öffnen → Bot zu deinem Server hinzufügen

Discord Client ID notieren (steht oben auf der "General Information" Seite)
Discord Client Secret notieren (OAuth2 → Client Secret → Reset Secret)

---

### SCHRITT 2 — GitHub (3 Min.)

1. Gehe zu https://github.com und erstelle ein kostenloses Konto
2. Klick "New Repository" → Name: "fanclub-tippspiel" → Public → Create
3. Lade alle Dateien aus diesem Ordner hoch (Upload files)

---

### SCHRITT 3 — Railway (kostenloser Server, 5 Min.)

1. Gehe zu https://railway.app → "Login with GitHub"
2. "New Project" → "Deploy from GitHub repo" → dein Repo wählen
3. Unter "Variables" folgende Umgebungsvariablen eintragen:

   DISCORD_TOKEN        = (dein Bot Token aus Schritt 1)
   DISCORD_CLIENT_ID    = (deine Client ID aus Schritt 1)
   DISCORD_CLIENT_SECRET= (dein Client Secret aus Schritt 1)
   SECRET_KEY           = (beliebiger langer zufälliger Text, z.B. 32 Buchstaben)
   WEB_URL              = (deine Railway URL, z.B. https://fanclub-manelo98.up.railway.app)

4. "Deploy" klicken → fertig!

---

### SCHRITT 4 — Discord OAuth Redirect eintragen (2 Min.)

1. Zurück zu https://discord.com/developers/applications → deine App
2. OAuth2 → Redirects → "Add Redirect"
3. Eintragen: https://DEINE-RAILWAY-URL.up.railway.app/auth/discord/callback
4. Save

---

### SCHRITT 5 — Channels auf Discord einrichten

Erstelle in deinem Server folgende Channels:
- #tippspiel-wm2026  (hier postet der Bot Ankündigungen)
- #rangliste         (optional, für /tabelle)
- #ergebnisse        (optional, für Auswertungen)

---

### Bot-Befehle

| Befehl | Wer | Was |
|--------|-----|-----|
| /anmelden | Jeder | Beim Tippspiel anmelden |
| /tippen | Jeder | Link zum Spielplan öffnen |
| /tabelle | Jeder | Aktuelle Rangliste anzeigen |
| /meinetipps | Jeder | Eigene Tipps & Punkte sehen |
| /spielplan | Jeder | Offene Spiele anzeigen |
| /ergebnis [id] [heim] [aus] | Admin | Ergebnis eintragen & auswerten |

---

### Punktesystem
- ✅ Exaktes Ergebnis = 3 Punkte
- ≈ Richtige Tendenz (Sieg/Unentschieden) = 1 Punkt
- ✗ Falsch = 0 Punkte

---

Bei Fragen einfach nochmal fragen! 🏆
