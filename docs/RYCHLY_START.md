# ⚡ Rychlý start – 5 minut

Pokud chceš bot spustit na Windows/Linux desktope v 5 minutách:

---

## 1️⃣ Klonuj a Příprava

```bash
git clone https://github.com/tvuj-repo/Chatbot-discord-JESUS.git
cd Chatbot-discord-JESUS
```

---

## 2️⃣ Virtuální prostředí

```bash
# Linux / Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

---

## 3️⃣ Instalace

```bash
pip install -r config/requirements.txt
```

---

## 4️⃣ Konfigurace

```bash
# Vytvoř .env ze šablony
cp config/.env.example .env

# Otevři .env v editoru a vložit bot token:
# DISCORD_TOKEN=tvuj_token_zde
```

[Jak získat bot token](https://discord.com/developers/applications) (3 minuty)

---

## 5️⃣ Spuštění

```bash
python3 bot.py
```

Měl by se přihlásit:
```
Bot je přihlášen jako Ježíš#4405
```

---

## ✅ Hotovo! Testuj v Discordu

```
/commands       # Seznam příkazů
/verse          # Náhodný verš
/yt https://www.youtube.com/watch?v=dQw4w9WgXcQ
/serverstats    # Server Analytics (v2.7)
/profile        # Tvůj profil (v2.7)
/leaderboard    # Leaderboard (v2.7)
```

---

## 🥧 Raspberry Pi?

Viz **docs/INSTALACE.md** pro kompletní krok-za-krokem setup (systemd, autostart).
