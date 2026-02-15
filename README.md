# ✝️ Ježíš Discord Bot – hudba, verše a hry zdarma 🙏

**Verze:** v2.8 – Spotify Integration Pack | **Platform:** Raspberry Pi Ready

Discord bot napsaný v Pythonu (discord.py), který umí:

* 🎵 Prehrávat hudbu z URL (YouTube přes `yt-dlp`) do voice kanálu - s názvy skladeb, odhadem času fronty, blokaací duplictních skladeb, podporou playlistů a shuffle
* 📃 Posílat raní a večerní zprávy s biblickým veršem
* 🙏 Žehnat hráčům při spuštění her a reagovat na společné hrání ve voice
* 🎁 Kadý večer publikovat „Hry zdarma” z Epic, Steam, PlayStation Plus s **individuálními embedy, obrázky**
* 🔘 NOVÉ v2.6.5: Jednotný design embeda – `/freegames` = automatické posílání, PS+ články v jednom embedu
* 🎮 NOVÉ v2.6.6: Steam Limited-Time Giveaways přes Reddit API `/r/FreeGameFindings`* 📊 **NOVÉ v2.7**: Server Analytics s leaderboardy – `/serverstats`, `/leaderboard`, `/myactivity`, `/weeklysummary`* ⚙️ Konfigurovat kanály per-guild s `/setchannel` a `/config`
* 🎮 Minihry s XP systémem (kviz, veršový duel, RNG požehnání)
* ✨ XP odměny za hudbu a hlasovou aktivitu s anti-cheat ochranou
* ℹ️ Slash commands: `/commands`, `/version`, `/diag` s automatickým autocomplete

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
* [Poznámky k Slash Commands](#-poznámky-k-slash-commands)
* [Přizpůsobení](#-přizpůsobení)
* [Roadmapa](#-roadmapa)
* [Licence](#-licence)
* [Poděkování](#-poděkování)

---

## ⚡ Rychlý start (5 minut)

Viz **docs/RYCHLY_START.md**

---

## ⚙️ Požadavky

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

## 📚 Dokumentace

- **docs/RYCHLY_START.md** – 5 minut na desktop
- **docs/INSTALACE.md** – Raspberry Pi (systemd, autostart, monitoring)
- **docs/CHYBY.md** – Troubleshooting a FAQ
- **docs/ČTĚME_NEJDŘÍV.md** – Úvod pro nové uživatele
- **privacy-policy.md** – Ochrana osobních údajů
- **terms-of-service.md** – Podmínky služby

---

## 📥 Instalace

### Automatická instalace

**RPi/Linux:**
```bash
bash scripts/install.sh
```

**Linux/macOS (desktop):**
```bash
bash scripts/install-desktop.sh
```

**Windows:**
```cmd
scripts\install.bat
```

### Manuální instalace

```bash
# 1) klon repozitáře
git clone <URL_TO_THIS_REPO>.git
cd <REPO_DIR>

# 2) vytvoř a aktivuj virtuální prostředí
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) nainstaluj závislosti
pip install -U pip
pip install -r config/requirements.txt
```

> **Tip:** Na Raspberry Pi běžte `bash scripts/install.sh` – vše se nastaví automaticky!

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
SPOTIFY_CLIENT_ID=PASTE_SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET=PASTE_SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

> Pozn.: `SPOTIFY_REDIRECT_URI` musí být uvedena i v Spotify Developer Dashboardu.

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

## ⌨️ Příkazy (Slash Commands – v2.6.1)

Hezký přehled najdete v `/commands`. Základ:

### Hudba

* `/yt <url>` – přidá skladbu nebo playlist do fronty a spustí přehrávání (YouTube přes yt-dlp) - **+1-2 XP**
* `/spauth` – Spotify OAuth přihlášení (nutné pro `/sp`)
* `/spcode <url>` – dokončení Spotify OAuth (vložíš redirect URL)
* `/sp <spotify_url>` – přidá Spotify skladbu/playlist do fronty (Spotify Connect)
* Pozn.: Spotify Connect vyžaduje Spotify Premium
* `/skip` – přeskoči aktuální skladbu - **+1-2 XP**
* `/pause` / `/resume` – pauza/obnovení
* `/stop` – zastaví a vyčistí frontu
* `/leave` – odpojí bota z voice
* `/np` – zobrazí právě přehrávanou skladbu
* `/queue` – vypíše frontu s odhadem celkového času
* `/shuffle` – náhodně zamíchá pořadí skladeb - **+1-2 XP**
* `/voicetest` – rychlý 3s tón pro ověření FFmpeg/voice

### Biblické příkazy

* `/verse` – náhodný biblický verš do chatu
* `/bless [@user]` – krátké osobní požehnání pro uživatele
* `/biblicquiz` – biblický trivia s 10+ otázkami - **+1-2 XP**

### Server Analytics (v2.7.1)

* `/serverstats` – přehled aktivit, hudby (ve frontě + přehrané) a top her na serveru
* `/leaderboard` – Top 10 hráčů podle XP s hodinami hraní
* `/weeklysummary` – automaticky se posílá každý týden do požehnání kanálu

### Ostatní

* `/xp` – zobrazí tvou aktuální XP a úroveň
* `/freegames` – aktuální přehled free her z 4+ spolehlivých zdrojů (Epic, Steam, PlayStation, GOG, IsThereAnyDeal, Reddit)
* `/commands` – kompletní seznam příkazů
* `/version` – info o verzi
* `/diag` – diagnostika bota

### Admin

* `/setchannel <typ> <kanál>` – Nastaví kanál pro "Požehnání" nebo "Hry zdarma" (admin-only)
* `/config` – Zobrazí aktuální konfiguraci serveru (admin-only)

---

## ⏰ Plánované úlohy (cron-like)

* **Ráno 09:00 (CET)**: biblický verš do `požehnání🙏`
* **Večer 22:00 (CET)**: „Dobrou noc…"
* **Večer 20:10 (CET)**: „Hry zdarma" do `hry_zdarma💵`

> Časy jsou v **Europe/Prague**. Můžete je změnit v definicích `tasks.loop`.

---

## 🧱 Běh na Raspberry Pi jako služba (systemd)

> **Automaticky:** Spusť `bash scripts/install.sh` – vygeneruje a nastaví systemd službu!

**Manuální příklad:** `/etc/systemd/system/discordbot.service`

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

### Slash Commands se nezobrazují?

* Bot se nemusel správně **syncnout** s Discordem. Zkus:
  1. Restartuj bot: `systemctl restart discordbot` (RPi) nebo Ctrl+C a znovu spusť
  2. Zkontroluj logy – měl by vidět: `[commands] Synced 23 slash commands`
  3. Pokud pořád ne, zkontroluj oprávnění bota

### 🔧 Diagnostické nástroje

* **tools/rpi_voice_diagnostics.py** – Detailní diagnostika RPi voice stacku
```bash
python3 tools/rpi_voice_diagnostics.py
```

* **/diag command** – Přímo v Discord chatu
```
/diag
```

### 1) „FFmpeg test selhal: ClientException: Not connected to voice"

* Zkontrolujte, že jste v **tom samém voice kanálu** jako bot při `/voicetest`.
* Ověřte práva kanálu: **Connect** a **Speak**.
* Na *Stage* kanálu udělte botovi *Invite to Speak*.

### 2) Nejde přehrávání / YouTube 403

* Musí být nainstalováno **FFmpeg** a **yt-dlp**.
* Vyzkoušejte jinou URL nebo aktualizujte `yt-dlp`:

  ```bash
  .venv/bin/python -m pip install -U yt-dlp
  ```

### 3) „Nelze se připojit: chybí PyNaCl/Opus"

* Do venv nainstalujte **PyNaCl** a v systému mějte **libopus0**:

  ```bash
  .venv/bin/python -m pip install -U PyNaCl
  sudo apt install -y libopus0
  ```

### 4) Oprávnění bota

* Na Developer Portalu zapněte **Presence Intent** a **Server Members Intent**.
* Pozvěte bota s právy **Send Messages**, **Connect**, **Speak**.

---

## 🛠️ Přizpůsobení (v2.6.1)

### Per-Guild Konfigurace (Doporučeno)

Nejjednodušší způsob – Použijte **Discord commands** přímo v serveru (admin-only):

```
/setchannel blessing <channel>     – Nastaví kanál pro ranní verš a požehnání
/setchannel freegames <channel>    – Nastaví kanál pro denní přehled free her
/config                            – Zobrazí aktuální konfiguraci
```

Tímto způsobem máte konfiguraci **per-server** uloženou v `bot_data.json` a změny se projeví okamžitě. ✅

### Programové Přizpůsobení (Pro Vývojáře)

Pokud chcete změnit defaultní chování:

**Biblické verše** (seznam přes 50 veršů):
- Soubor: [bot.py](bot.py#L792) řádek 792
- Upravte seznam `verses = [...]` aby obsahoval vaše verše
- Vzor: `'"Text verše" (Bibličtí 1,1)'`

**Požehnání pro konkrétní hry** (dictionary se 54+ hrami):
- Soubor: [bot.py](bot.py#L852) řádek 852
- Upravte `game_blessings = {...}` aby obsahoval vaše hry
- Vzor: `"Název hry": "Personalizované požehnání text 🎮"`
- Default fallback: Náhodné požehnání když se hra v dictu nenajde

**Časy plánovaných úloh** (cron-like tasky):
- **Ráno (09:00 CET)**: Ranní zpráva s veršem – [řádek 1698](bot.py#L1698)
  - Změnit: `if now.hour == 9 and now.minute == 0:`
- **Večer (22:00 CET)**: Noční zpráva – [řádek 1716](bot.py#L1716)
  - Změnit: `if now.hour == 22 and now.minute == 0:`
- **Večer (20:10 CET)**: Free Games – [řádek 1733](bot.py#L1733)
  - Změnit: `if now.hour == 20 and now.minute == 10:`
- Vždy **timezone**: `Europe/Prague` (pytz)

**Free Games Platformy** (6 zdrojů):
- Soubor: [bot.py](bot.py#L602) řádek 602 – funkce `get_free_games()`
- Máte: Epic Games, Steam, PlayStation, GOG, Ubisoft+, Prime Gaming
- Chcete přidat/odebrat zdroj? Upravte try/except bloky v [get_free_games()](bot.py#L602)
- Fallback cache: 6 hodin (mění se v [řádku 223](bot.py#L223) – `21600 sekund`)

**XP Systém & Role Úrovně**:
- Soubor: [bot.py](bot.py) – hledejte `XP_LEVELS`, `ROLES`
- 8 úrovní s rolemi: 🔰 Učedník → 👑 Apoštol (nastaveno fixně)
- Cooldown požehnání: 1 hodina per-game (v `_game_blessing_cooldowns`)

### Databáze Konfigurace

- Soubor: `bot_data.json` (vytvoří se automaticky)
- Struktura: 
  ```json
  {
    "guild_configs": {
      "123456789": {
        "blessing_channel_id": 987654321,
        "freegames_channel_id": 987654322
      }
    }
  }
  ```
- Spravuje se přes `/setchannel` a `/config` – **nedoporučujeme ruční editaci**

---

## 🛣️ Roadmapa – Ježíš Discord Bot (v2.x → v3.x)

### 📦 v2.3.2 – Multi-Server Thread-Safety Patch (HOTOVO)

Historická verze:
* ✅ **Guild-level locks** pro bezpečné vytváření rolí
* ✅ **Periodic game tracking** se storage (každých 5 minut)
* ✅ **Real-time herní statistiky** bez race conditions
* ✅ Automatické sledování hraných her uživatelů
* ✅ Personalizovaná požehnání podle hrané hry (54 her)
* ✅ `/profile` s TOP 5 herami, server rankingem, role achievements
* ✅ Auto-role: 🎮 Gamer, 🌙 Night Warrior, ⛪ Weekend Crusader
* ✅ Multi-server ready bez konflikty dat
* ✅ Error handling s JSON
* ✅ Všechny minihry (kviz, versfight, rollblessing)
* ✅ XP systém: 🔰 Učedník → 📜 Prorok → 👑 Apoštol

### 📦 v2.4 – Music QoL Pack (HOTOVO)

Historická verze – Zlepšení hudby a miniher:
* ✅ **Blokace duplicitních skladeb** – Detekuje když se uživatel pokusí přidat stejnou skladbu do fronty
* ✅ **Odhad času fronty** – `/fronta` a `/yt` zobrazují odhad zbývajícího času (⏱️ Odhad: ~45m 30s, 12 skladeb)
* ✅ **Automatické čištění URL setu** – Když se skladba přehraje nebo se fronta vymaže
* ✅ **Cachování doby trvání** – Uloží délku skladby pro rychlejší výpočty
* ✅ **Rozšířená biblická databáze** – 32 otázek v kvízu (místo 10) pro vyšší variabilitu
* ✅ Všechny funkce v2.3.2 zachovány (bez breaking changes)
* ✅ Optimalizované pro multi-server i single-server nasazení

### 📦 v2.4.1 – Music Playlist & Shuffle (HOTOVO)

Historická verze – Playlist a shuffle funkcionalita:
* ✅ **YouTube Album/Playlist v jednom kroku** – `/yt <playlist_url>` detekuje playlist a přidá všechny skladby najednou s duplikát-checkingem
* ✅ **Zamíchání fronty** – Nový command `/shuffle` náhodně zamíchá pořadí skladeb ve frontě (aktuálně hraná skladba zůstane na místě)
* ✅ **Odhad času playlistu** – Bot vypočítá a zobrazí celkový čas všech skladeb v playlistu před přidáním
* ✅ **Batch progress feedback** – Zobrazuje průběh přidávání: "⏳ Přidávám: 5/24 skladeb..."
* ✅ **Duplikát blocking na playlistech** – Automaticky detekuje a přeskakuje duplikáty v playlistech
* ✅ Zpětná kompatibilita s v2.4 (vše funguje jako do teď)
* ✅ YouTube přehrávání zůstává beze změn (stejně skvěle funguje!)

### 🟩 v2.5 – Channel Config Pack (HOTOVO)

Správa konfigurace per-guild:
* ✅ **`/setchannel <typ> <kanál>`** – Rychlé nastavení kanálů (Požehnání, Hry zdarma)
* ✅ **`/config`** – Přehled aktuální konfigurace serveru s admin-only přístupem
* ✅ **Bezpečné ukládání nastavení** – Per-guild konfigurace v `bot_data.json` (centralizované)
* ✅ **Validace oprávnění** – Pouze administrátoři mohou měnit konfiguraci
* ✅ **Čisté logování** – Všechny změny jsou zaznamenány v konzoli
* ✅ **Fallback na staré hledání** – Pokud není kanál nastaven, bot si vyhledá kanál podle jména
* ✅ Zpětná kompatibilita se všemi předchozími verzemi

### 🟩 v2.6 – Free Games Engine 3.0 (AKTIVNÍ)

* ✅ **Přidané platformy: GOG, Ubisoft+, Amazon Prime Gaming** – Nový `/freegames` agreguje 6 zdrojů (Epic, Steam, PlayStation, GOG, Ubisoft+, Prime Gaming)
* ✅ **Per-source status reporting** – Embed zobrazuje stav každé platformy (✅/❌)
* ✅ **Robustnější scraping + fallbacky** – Všechny zdroje mají vlastní try/except, selhání jednoho neovlivní ostatní
* ✅ **Message když Steam nemá hry zdarma** – Zobrazí "❌ Steam" když je Steam prázdný
* 📍 *Upozornění na končící hry* – Základ implementován, volno pro rozšíření (API nevrací expiration data)

### 🟩 v2.7 – Server Analytics & Summary (AKTIVNÍ)

* `/serverstats` – přehled aktivit, hudby, miniher
* Leaderboard hráčů
* `/myactivity` – osobní statistiky
* Týdenní shrnutí aktivit
* Agregace hraných her + hudební historie

### 🟩 v2.8 – Spotify Integration Pack (HOTOVO)

* **Spotify Web API support** – `/sp <spotify_url>` přidá skladbu nebo playlist do fronty
* **Spotify Connect playback** – Bot ovládá tvou Spotify aplikaci přes Spotify Connect (legitimní streaming)
* **Premium account required** – Vyžaduje Spotify Premium pro programmatic playback
* **OAuth authentication** – Uživatel se autentifikuje přes Spotify OAuth na začátku
* **Duplikát blocking** – Spotify skladby jsou chráněny proti duplicitám jako YouTube
* **Queue duration estimation** – Odhad času i pro Spotify skladby
* **Error handling** – Bez vlivu na YouTube přehrávání (`/yt`), oddělené systémy

### 🟨 v2.9 – Web Dashboard (PLÁNOVANÉ)

* Běží přímo na Raspberry Pi (Flask/FastAPI)
* Živé zobrazení právě hrané hudby
* Vizuální konfigurace kanálů a nastavení
* Log viewer + diagnostika
* Mobile-friendly UI

### 🟨 v3.0 – Ježíš Discord Bot PRO (PLÁNOVANÉ)

* Multi-language režim (CZ / EN / SK)
* Modulární plugin systém
* Oddělené konfigurace per-guild
* Companion web app (PWA)
* Cluster-ready architektura

---

## 📄 Licence

**JEŽÍŠ DISCORD BOT – CUSTOM NON-COMMERCIAL LICENSE**

✅ **Povoleno:**
- Kopírování a úpravy kódu
- Osobní a nekomercí používání
- Distribuce v nekomercích účelech (bez poplatku)

❌ **Zakázáno:**
- Komerční využití bez svolení

⚠️ **Povinné:**
- Zmínit autora: **Matěj Horák (Braska-botmaker)**
- Zachovat licenci v distribuovaných verzích

Plný text licence: **LICENSE** soubor v kořeni repozitáře

---

## 🙌 Poděkování

* `discord.py` tým a komunita
* Autoři `yt-dlp` a `ffmpeg`
* Zdroje free her: Epic Games, Steam, PlayStation, GOG, IsThereAnyDeal, Reddit r/FreeGames

---

**Šťastné hraní a čtení! 🎵📖🎮**


