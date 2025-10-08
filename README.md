# ✝️ Discord bot – hudba, verše a upozornění na hry zdarma

Discord bot napsaný v Pythonu (discord.py), který umí:

* 🎵 Přehrávat hudbu z URL (YouTube přes `yt-dlp`) do voice kanálu
* 📖 Posílat ranní a večerní zprávy s biblickým veršem
* 🙏 Žehnat hráčům při spuštění her a reagovat na společné hraní ve voice
* 🎁 Každý večer publikovat „Hry zdarma“ z Epic Games a Steamu
* 🎁 Každý večer publikovat „Hry zdarma“ z Epic Games, Steamu a PlayStation Plus (oznámení)
* ℹ️ Hezké embed příkazy `!verze` a `!commands`

> Optimalizováno pro běh na Raspberry Pi 24/7, ale funguje i lokálně na Windows/Linux/macOS.

---

## 🗂️ Obsah

* [Požadavky](#-požadavky)
* [Instalace](#-instalace)
* [Nastavení Discord aplikace a bot tokenu](#-nastavení-discord-aplikace-a-bot-tokenu)
* [Konfigurace (.env)](#-konfigurace-env)
* [Spuštění](#-spuštění)
* [Kanály a oprávnění](#-kanály-a-oprávnění)
* [Příkazy](#-příkazy)
* [Plánované úlohy (cron-like)](#-plánované-úlohy-cron-like)
* [Běh na Raspberry Pi jako služba (systemd)](#-běh-na-raspberry-pi-jako-služba-systemd)
* [Diagnostika a řešení problémů](#-diagnostika-a-řešení-problémů)
* [Poznámky k hudbě a streamování](#-poznámky-k-hudbě-a-streamování)
* [Přizpůsobení](#-přizpůsobení)
* [Roadmapa](#-roadmapa)
* [Licence](#-licence)

---

## ✅ Požadavky

* **Python 3.10+**
* **FFmpeg** (pro přehrávání do voice)
* Knihovny:

  * `discord.py`
  * `python-dotenv`
  * `yt-dlp`
  * `PyNaCl` (hlas pro voice)
* **Opus** knihovna v systému (např. `libopus0` na Debian/Ubuntu/Raspbian)
* Přístup admina k Discord serveru pro udělení oprávnění

### Instalace systémových balíčků

**Debian/Ubuntu/Raspberry Pi OS:**

```bash
sudo apt update
sudo apt install -y ffmpeg libopus0 python3-venv
```

**Windows:**

* Stáhněte FFmpeg (statické buildy) a přidejte `ffmpeg.exe` do PATH.

---

## 📦 Instalace

```bash
# 1) klon repozitáře
git clone <URL_TO_THIS_REPO>.git
cd <REPO_DIR>

# 2) vytvoř a aktivuj virtuální prostředí
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) nainstaluj závislosti
pip install -U pip
pip install discord.py python-dotenv yt-dlp PyNaCl
```

> **Tip:** Na Raspberry Pi držte vše v `/opt/discordbot/` a používejte stejné venv pro stabilitu.

---

## 🔐 Nastavení Discord aplikace a bot tokenu

1. Jděte na **Discord Developer Portal** → *Applications* → *New Application*.
2. V sekci **Bot**: *Add Bot* → zkopírujte **TOKEN**.
3. V sekci **OAuth2 → URL Generator** vyberte **bot** a oprávnění (minimálně: *Read Messages/View Channels, Send Messages, Connect, Speak*). Vygenerovanou URL použijte pro pozvání bota na server.
4. **Privileged Gateway Intents** (v *Bot*): zapněte **Presence Intent** a **Server Members Intent** (bot je využívá).

---

## ⚙️ Konfigurace (.env)

V kořeni projektu vytvořte soubor `.env`:

```env
DISCORD_TOKEN=PASTE_VAS_TOKEN_SEM
```

> Token nikdy necommituje do repozitáře.

---

## ▶️ Spuštění

```bash
source .venv/bin/activate
python bot.py
```

Po přihlášení uvidíte v konzoli: `Bot je přihlášen jako ...`

---

## #️⃣ Kanály a oprávnění

Bot automaticky používá tyto textové kanály (pokud existují):

* `požehnání🙏` – uvítání, ranní/večerní zprávy, požehnání hráčům
* `hry_zdarma💵` – denní přehled her zdarma (Epic)

Ujistěte se, že má bot práva **Send Messages** v těchto kanálech.

Voice práva v cílovém kanálu:

* **Connect**, **Speak** (nutné)
* *(Stage kanály)* – udělit *Invite to Speak* nebo použít běžný voice

---

## ⌨️ Příkazy

Hezký přehled najdete v `!commands`. Základ:

### Hudba

* `!play <url>` – přidá skladbu do fronty a spustí přehrávání (YouTube přes yt‑dlp)
* `!skip` – přeskočí aktuální skladbu
* `!pause` / `!resume` – pauza/obnovení
* `!stop` – zastaví a vyčistí frontu
* `!leave` – odpojí bota z voice
* `!mqueue` – vypíše frontu
* `!np` – zobrazí právě přehrávanou skladbu
* `!vtest` – rychlý 3s tón pro ověření FFmpeg/voice
* `!diag` – výpis prostředí, práv a instalace

### Ostatní

* `!verze` – info o verzi a změnách
* `!verš` – náhodný biblický verš do chatu – denní streak s pochvalou
* `!hryzdarma` – aktuální přehled free her (Epic a Steam)
* `!pozehnani @uživatel` – krátké osobní požehnání


---

## ⏰ Plánované úlohy (cron-like)

* **Ráno 07:00 (CET)**: biblický verš do `požehnání🙏`
* **Večer 20:00 (CET)**: „Dobrou noc…“
* **Večer 20:10 (CET)**: „Hry zdarma“ do `hry_zdarma💵`

> Časy jsou v **Europe/Prague**. Můžete je změnit v definicích `tasks.loop`.

---

## 🧱 Běh na Raspberry Pi jako služba (systemd)

**Příklad:** `/etc/systemd/system/discordbot.service`

```ini
[Unit]
Description=Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=discordbot
WorkingDirectory=/opt/discordbot
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/discordbot/.venv/bin/python /opt/discordbot/bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Aktivace a start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable discordbot
sudo systemctl start discordbot
sudo systemctl status discordbot --no-pager
```

Logy:

```bash
journalctl -u discordbot -f
```

---

## 🩺 Diagnostika a řešení problémů

### 1) „FFmpeg test selhal: ClientException: Not connected to voice“

* Zkontrolujte, že jste v **tom samém voice kanálu** jako bot při `!vtest`/`!play`.
* Ověřte práva kanálu: **Connect** a **Speak**.
* Na *Stage* kanálu udělte botovi *Invite to Speak*.
* Zkuste jiný voice kanál (někdy pomůže změna regionu/latence).

### 2) Nejde přehrávání / YouTube 403

* Musí být nainstalováno **FFmpeg** a **yt-dlp**.
* Pokud YouTube blokuje bez hlaviček, kód už posílá správné HTTP headers do FFmpeg.
* Vyzkoušejte jinou URL nebo aktualizujte `yt-dlp`:

  ```bash
  .venv/bin/python -m pip install -U yt-dlp
  ```

### 3) „Nelze se připojit: chybí PyNaCl/Opus“

* Do venv nainstalujte **PyNaCl** a v systému mějte **libopus0**:

  ```bash
  .venv/bin/python -m pip install -U PyNaCl
  sudo apt install -y libopus0
  ```

### 4) Oprávnění bota

* Na Developer Portalu zapněte **Presence Intent** a **Server Members Intent**.
* Pozvěte bota s právy **Send Messages**, **Connect**, **Speak**.

### 5) Epic Games API vrací prázdno

* Někdy nejsou zrovna hry zdarma nebo API vrátí prázdný seznam → bot to ošetřuje.

---

## 🎧 Poznámky k hudbě a streamování

* Kód používá `FFmpegOpusAudio.from_probe` (pokud je k dispozici) s fallbackem na `FFmpegPCMAudio`.
* Pro nestabilní konektivity je implementován **reconnect watchdog** a **backoff**.
* Při `!play` se **ušetří poslední voice kanál** pro pozdější automatické připojení.

---

## 🛠️ Přizpůsobení

* **Kanály**: změňte názvy v helperu `get_channel_by_name` nebo přidejte autodetekci podle ID.
* **Texty požehnání**: upravte dict `game_blessings`.
* **Verše**: rozšiřte list `verses`.
* **Plánovač**: upravte časy v `tasks.loop` (pozor na timezone `CET`).

---

## 🗺️ Roadmapa

* [x] Minihra pro discord uživatele
* [ ] Vyhledávání písní podle názvu (bez URL)
* [ ] Lepší multi‑server fronty (persist na disk)
* [ ] Slash příkazy (`/play`, `/verš`…)
* [ ] Dockerfile a compose
* [ ] Přidání Steam a PS hry do her zdarma

---

## 📄 Licence

Zvolte licenci dle potřeby (např. MIT). Přidejte `LICENSE` soubor do repozitáře.

---

## 🙌 Poděkování

* `discord.py` tým a komunita
* Autoři `yt-dlp` a `ffmpeg`


