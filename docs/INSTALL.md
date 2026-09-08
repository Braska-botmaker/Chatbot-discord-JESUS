# 🛠️ Instalace

Jeden dokument, dvě cesty:

- **[Rychlý start](#-rychlý-start-desktop)** – vyzkoušet bota lokálně na Windows/Linux/macOS (5 minut)
- **[Produkční nasazení](#-produkční-nasazení-raspberry-pi--linux-server)** – běh 24/7 na Raspberry Pi nebo jiném serveru přes systemd

Obojí sdílí stejné [požadavky](#-požadavky) a [konfiguraci](#-konfigurace-env).

---

## 📋 Požadavky

| Co | Verze | Poznámka |
|---|---|---|
| Python | 3.10+ | |
| FFmpeg | jakákoli aktuální | přehrávání do voice kanálu |
| Opus knihovna | – | `libopus0` na Debian/Ubuntu/Raspberry Pi OS |
| Node.js *(nebo Deno)* | LTS | yt-dlp ho od ~2026.08 potřebuje k YouTube extrakci (JS challenge). Bez něj přehrávání selže na *„Sign in to confirm you're not a bot"*. |
| Discord účet | – | admin práva na serveru, kam bota přidáváš |

Instalace systémových balíčků:

```bash
# Debian / Ubuntu / Raspberry Pi OS
sudo apt update
sudo apt install -y ffmpeg libopus0 python3-venv git nodejs
```

```powershell
# Windows – stáhni FFmpeg (statický build) a přidej ffmpeg.exe do PATH
# https://www.gyan.dev/ffmpeg/builds/
```

---

## ⚡ Rychlý start (desktop)

```bash
# 1) Klonuj repozitář
git clone <URL_TOHOTO_REPA>.git
cd Chatbot-discord-JESUS

# 2) Virtuální prostředí
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3) Závislosti
pip install -U pip
pip install -r config/requirements.txt

# 4) Konfigurace
cp config/.env.example .env
# otevři .env a vlož DISCORD_TOKEN (viz sekce Discord aplikace níže)

# 5) Spuštění
python bot.py
```

Bot by se měl přihlásit: `Bot je přihlášen jako ...`

Otestuj v Discordu: `/commands`, `/verse`, `/yt https://www.youtube.com/watch?v=dQw4w9WgXcQ`

> Existují i hotové instalační skripty – `scripts/install-desktop.sh` (Linux/macOS) a `scripts/install.bat` (Windows) – dělají kroky 2–4 automaticky.

---

## 🔐 Discord aplikace a bot token

1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**
2. Sekce **Bot** → **Add Bot** → zkopíruj **TOKEN** (uložíš ho do `.env`)
3. V té samé sekci zapni **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
4. Sekce **OAuth2 → URL Generator** → zaškrtni scope `bot` a oprávnění minimálně: *View Channels, Send Messages, Connect, Speak* → vygenerovanou URL otevři v prohlížeči a pozvi bota na server

Bez kroku 3 se bot vůbec nepřihlásí (spadne s `PrivilegedIntentsRequired`).

---

## ⚙️ Konfigurace (.env)

V kořeni projektu vytvoř `.env` (nikdy ho necommituj – je v `.gitignore`):

```env
DISCORD_TOKEN=tvuj_token_zde
```

To je jediná **povinná** proměnná. Volitelné:

| Proměnná | Výchozí | K čemu je |
|---|---|---|
| `YTDLP_PLAYER_CLIENTS` | *(prázdné)* | Vynutí konkrétní yt-dlp "player kliency" pro YouTube extrakci. Nech prázdné – yt-dlp si aktuálně poradí sám. Použij jen jako nouzovou zálohu, viz [Troubleshooting](TROUBLESHOOTING.md#-youtube-nehraje--žádný-zvuk). |
| `YTDLP_COOKIES_FILE` | *(prázdné)* | Cesta k `cookies.txt` (Netscape formát) pro věkově omezená videa. |
| `YTDLP_JS_RUNTIME` | *(prázdné)* | Cesta / jméno JS runtime pro yt-dlp (`node`, `deno`, …). Nech prázdné – bot si ho najde v PATH. Vyplň jen když je binárka mimo PATH (`node:/opt/node/bin/node` nebo holá cesta). |

Šablona se všemi proměnnými a komentáři: [`config/.env.example`](../config/.env.example) (root `.env.example` je identický).

> 🎧 Spotify integrace (`SPOTIFY_CLIENT_ID` a podobné) je momentálně **odložená** – viz [Roadmapa v README](../README.md#-roadmapa).

---

## 🥧 Produkční nasazení (Raspberry Pi / Linux server)

Cíl: bot běží 24/7 jako systemd služba a restartuje se sám při pádu i po rebootu.

### 1) Připrav složku a nainstaluj závislosti

```bash
sudo mkdir -p /opt/discordbot && sudo chown $USER:$USER /opt/discordbot
cd /opt/discordbot
git clone <URL_TOHOTO_REPA>.git .

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r config/requirements.txt
```

Ověř, že je vše na místě:

```bash
python3 -c "import discord; print('discord.py OK')"
python3 -c "import nacl; print('PyNaCl OK')"
which ffmpeg
```

### 2) Nastav `.env`

```bash
cp config/.env.example .env
nano .env          # vlož DISCORD_TOKEN
chmod 600 .env      # jen vlastník smí číst
```

### 3) Otestuj ruční spuštění

```bash
python3 bot.py
```

Zastav pomocí `Ctrl+C`, jakmile vidíš `Bot je přihlášen jako ...` a `/commands` funguje v Discordu.

### 4) Vytvoř systemd službu

```bash
sudo nano /etc/systemd/system/discordbot.service
```

```ini
[Unit]
Description=Jezis Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/discordbot
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/opt/discordbot/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/discordbot/.venv/bin/python3 /opt/discordbot/bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discordbot

[Install]
WantedBy=multi-user.target
```

> Nahraď `User=pi` skutečným uživatelem, pod kterým má bot běžet.
> Řádek `Environment="PATH=…"` je důležitý – bez něj systemd běží s minimálním PATH
> a yt-dlp nenajde `node` (→ *„Sign in to confirm you're not a bot"*). `/usr/bin` v něm
> musí zůstat.

💡 **Rychlejší cesta:** `bash scripts/install.sh` udělá celé produkční nasazení včetně
této služby, instalace `nodejs` a `.env`. Proměnné `BOTDIR` / `SERVICE_NAME` / `REPO_URL`
jdou přepsat: `BOTDIR=/srv/bot bash scripts/install.sh`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now discordbot
sudo systemctl status discordbot --no-pager
```

### 5) Sleduj logy

```bash
journalctl -u discordbot -f
```

### Běžná údržba

| Akce | Příkaz |
|---|---|
| Restart | `sudo systemctl restart discordbot` |
| Stop | `sudo systemctl stop discordbot` |
| Stav | `sudo systemctl status discordbot --no-pager` |
| Live logy | `journalctl -u discordbot -f` |
| Aktualizace kódu | `cd /opt/discordbot && git pull && sudo systemctl restart discordbot` |
| Aktualizace balíčků | `source .venv/bin/activate && pip install -U -r config/requirements.txt && sudo systemctl restart discordbot` |
| Aktualizace **jen** yt-dlp (nejčastější fix) | `source .venv/bin/activate && pip install -U yt-dlp && sudo systemctl restart discordbot` |
| Aktualizace Node.js (yt-dlp JS runtime) | `sudo apt-get update && sudo apt-get install -y --only-upgrade nodejs && sudo systemctl restart discordbot` |

---

## ✅ Kontrolní seznam

- [ ] Python 3.10+, FFmpeg, `libopus0`, `nodejs` nainstalované (`node --version` odpoví)
- [ ] `pip install -r config/requirements.txt` proběhlo bez chyb
- [ ] `.env` obsahuje platný `DISCORD_TOKEN`
- [ ] Privileged Intents zapnuté v Developer Portalu (Presence, Server Members, Message Content)
- [ ] `python bot.py` se přihlásí a `/commands` odpoví v Discordu
- [ ] (produkce) systemd služba je `enabled` a `active (running)`

Něco nefunguje? → [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
