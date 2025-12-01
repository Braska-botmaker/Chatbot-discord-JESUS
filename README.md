# ✝️ Ježíš Discord Bot – hudba, verše a hry zdarma 🙏

**Verze:** v2.3 – Game Presence Engine 2.0 | **Platform:** Raspberry Pi Ready

Discord bot napsaný v Pythonu (discord.py), který umí:

* 🎵 Přehrávat hudbu z URL (YouTube přes `yt-dlp`) do voice kanálu - s názvy skladeb
* 📖 Posílat ranní a večerní zprávy s biblickým veršem
* 🙏 Žehnat hráčům při spuštění her a reagovat na společné hraní ve voice
* 🎁 Každý večer publikovat „Hry zdarma" s embedem a Discord link previews
* 🎮 Minihry s XP systémem (kviz, veršový duel, RNG požehnání)
* ℹ️ Slash commands: `/komandy`, `/verze`, `/diag` s automatickým autocomplete

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

## ⚡ Rychlý start (5 minut)

Viz **docs/RYCHLY_START.md**

### Slash Commands – jak je používat?

Po přihlášení bota vidíte `/` v Discord chatu. Veškeré příkazy jsou **slash commands**:

```
/yt https://youtube.com/watch?v=... – Přidej skladbu
/další – Přeskoč
/verse – Náhodný verš
/bless @user – Požehnání pro uživatele
/komandy – Kompletní seznam
```

**Žádné prefix commands!** V2.1.5 používá pouze `/` (app_commands) pro modernost a bezpečnost.

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

V kořeni projektu vytvořte soubor `.env` (vzor: `config/.env.example`):

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

## ⌨️ Příkazy (Slash Commands – v2.3)

Hezký přehled najdete v `/komandy`. Základ:

### Hudba

* `/yt <url>` – přidá skladbu do fronty a spustí přehrávání (YouTube přes yt‑dlp)
* `/další` – přeskoči aktuální skladbu
* `/pauza` / `/pokračuj` – pauza/obnovení
* `/zastav` – zastaví a vyčistí frontu
* `/odejdi` – odpojí bota z voice
* `/fronta` – vypíše frontu
* `/np` – zobrazí právě přehrávanou skladbu
* `/vtest` – rychlý 3s tón pro ověření FFmpeg/voice
* `/diag` – výpis prostředí, práv a instalace

### Ostatní

* `/verze` – info o verzi a změnách
* `/verse` – náhodný biblický verš do chatu – denní streak s pochvalou
* `/freegames` – aktuální přehled free her (Epic Games)
* `/bless @uživatel` – krátké osobní požehnání
* `/komandy` – kompletní seznam příkazů

### Minihry & Hry (v2.3)

* `/biblickykviz` – biblický trivia systém s 10 otázkami
* `/versfight @user` – veršový duel mezi hráči (hlasování, XP)
* `/rollblessing` – RNG požehnání s cooldown 1 hodina
* `/profile [@user]` – kompletní profil s XP, TOP 5 herami, rankingem a rolemi (v2.3)


---

## ⏰ Plánované úlohy (cron-like)

* **Ráno 07:00 (CET)**: biblický verš do `požehnání🙏`
* **Večer 20:00 (CET)**: „Dobrou noc…“
* **Večer 20:10 (CET)**: „Hry zdarma“ do `hry_zdarma💵`

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

* Bot se nemusel správně **syncer** s Discordem. Zkus:
  1. Restartuj bot: `systemctl restart discordbot` (RPi) nebo Ctrl+C a znovu spusť
  2. Zkontroluj logy – měl by vidět: `[commands] Synced 15 slash commands`
  3. Pokud pořád ne, zkontroluj oprávnění bota (Bot → Scopes: `bot`, Permissions: minimálně `Send Messages`, `Connect`, `Speak`)

### Slash Command selhal – "Interaction Failed"

* Příčina: Bot nemá čas odpovědět do 3 sekund (timeout Discord API)
* V2.1.0 to řeší: všechny commands mají `await interaction.response.defer()` nebo `send_message()`
* Pokud pořád selhává: zkontroluj logy bota (`journalctl -u discordbot -f`)

### 🔧 Diagnostické nástroje

* **tools/rpi_voice_diagnostics.py** – Detailní diagnostika RPi voice stacku
```bash
python3 tools/rpi_voice_diagnostics.py
```

* **/diag command** – Přímo v Discord chatu
```
/diag
```

### ⚡ NOVÁ OPRAVA (v2.1.5) – Scheduled Tasks + Epic Games Fix

**Co se změnilo oproti v2.1.4:**
* ✅ **Opravy Scheduled Tasks** – "Dobré ráno" a "Dobrou noc" nyní fungují
* ✅ **Epic Games API Fix** – `/freegamesjo` (přeejmenováno) a automatické odeslání her
* ✅ **Robust Error Handling** – komplexní parsování dat s fallbacky
* ✅ **Debug Logging** – lépe vidít, co se děje v logů
* ✅ **Precision Timing** – tasks běží každé minuty a kontrolují přesný čas

**Proč upgrade?**
- Automatické zprávy nyní funkčují spolehlivě
- Epic Games API stávové chyby jsou vyřešeny
- Lepší viditelnost do problémů přes logging

---

### 1) „FFmpeg test selhal: ClientException: Not connected to voice"

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

## 🎧 Poznámky k Slash Commands (v2.1.5)

### Jak používat?

1. **Napište `/` do Discord zprávy** – Discord ti nabídne autocomplete
2. **Vyber příkaz** – např. `/yt`, `/verse`, `/bless`
3. **Vyplň parametry** – Discord ti pomůže s autosuggestem
4. **Stiskni Enter** – příkaz se vykoná

### Příklady

```
/yt https://youtube.com/watch?v=dQw4w9WgXcQ
/dalí
/verse
/bless @username
/komandy
/diag
```

### Slash Commands vs Prefix Commands (Proč upgrade?)

| Vlastnost | Slash Commands (`/`) | Prefix Commands (`!`) |
|-----------|----------------------|----------------------|
| Autocomplete | ✅ Ano | ❌ Ne |
| Viditelnost | ✅ Hned vidět | ❌ Skryta |
| Bezpečnost | ✅ Bezpečnější | ❌ Riziková |
| Modernost | ✅ Budoucí Discord | ❌ Zastaralé |
| Error Handling | ✅ 39 try/except | ⚠️ Méně |

**Doporučujeme: Upgrade na v2.1.0!**

---

## 🛠️ Přizpůsobení

* **Kanály**: změňte názvy v helperu `get_channel_by_name` nebo přidejte autodetekci podle ID.
* **Texty požehnání**: upravte dict `game_blessings`.
* **Verše**: rozšiřte list `verses`.
* **Plánovač**: upravte časy v `tasks.loop` (pozor na timezone `CET`).

---


## 🛣️ Roadmapa – Ježíš Discord Bot (v2.x → v3.x)

### 🟩 v2.3 (AKTUÁLNÍ VERZE – Game Presence Engine 2.0)

Nyní aktivní! Pokročilé sledování a management her:
* ✅ Automatické sledování hraných her uživatelů
* ✅ Personalizovaná požehnání podle hrané hry (54 her)
* ✅ **Nové v2.3**: `/profile` s TOP 5 herami, server rankingem, role achievements
* ✅ Auto-role: 🎮 Gamer, 🌙 Night Warrior, ⛪ Weekend Crusader
* ✅ Hudba, verše, minihry z v2.2, presence tracking

### 🟩 v2.2.1 (LEGACY – Enhanced Queue Display)

Starší verze s hudbou:
* ✅ `/fronta` zobrazuje názvy skladeb + URL (strukturovaně)
* ✅ Hudba s českými názvy (auto-extrakce z YouTube)
* ✅ Všechny minihry z v2.2 (kviz, versfight, rollblessing, profile basic)
* ✅ XP systém: 🔰 Učedník → 📜 Prorok → 👑 Apoštol
* ✅ Hry zdarma, verse streak

### 🟩 v2.2 (PŘEDCHOZÍ VERZE – Minihry & Interakce)

Verze s minihrama:
* ✅ `/biblickykviz` – biblický trivia s 10 otázkami a interaktivními buttony
* ✅ `/versfight @user` – veršový duel se hlasováním
* ✅ `/rollblessing` – RNG požehnání (cooldown 1h)
* ✅ `/profile [@user]` – zobrazení XP a levelu (3 stupně)
* ✅ XP Systém s automatickými levely

### 🟩 v2.1.5 (LEGACY VERZE – Enhanced Game Display)

Starší verze:
* ✅ Embed + Discord link previews pro hry zdarma (Epic, Steam, PlayStation)
* ✅ 24/7 scheduled tasks (ranní zprávy, noční zprávy, free games)
* ✅ RPi voice patches (Error 4006 – exponential backoff)


## ✨ v2.2 – Minihry & Interakce (HOTOVO)
* `/biblickykviz` – biblický trivia systém  
* `/versfight @user` – veršový duel  
* `/rollblessing` – RNG požehnání (cooldown)  
* XP/role systém „učedník → prorok → apoštol“  
* lehké textové minihry, RPi-friendly  



## 🎮 v2.3 – Game Presence Engine 2.0 (HOTOVO ✅)
* ✅ Pokročilé sledování hraných her uživatelů  
* ✅ Personalizovaná požehnání podle hrané hry (54 her)  
* ✅ Server ranking a statistiky: TOP 5 her, celkový čas  
* ✅ Auto-role: 🎮 Gamer (1+ hodina), 🌙 Night Warrior (23:00+), ⛪ Weekend Crusader (víkend)  
* ✅ `/profile` integruje veškeré game presence data



## 🔥 v2.4 – Music QoL Pack
* rychlejší reconnect při ping spikech  
* ukládání posledního voice kanálu → auto-reconnect po restartu  
* lepší práce s frontou (blokace duplicity, auto-clean)  
* přepracovaný `/mqueue` s embedem  
* stabilnější `/stop` a reconnect logika  



## 🛠️ v2.5 – Channel Config Pack
* `/setchannel <typ> <kanál>` – rychlé nastavení kanálů pro verše i „hry zdarma“  
* `/config` – přehled aktuální konfigurace serveru  
* bezpečné ukládání nastavení pro každý server zvlášť  
* validace perms (pokud bot nemůže psát → inteligentní hláška)  
* čisté logování změn (RPi-safe)



## 🎁 v2.6 – Free Games Engine 3.0
* přidány platformy: GOG, Ubisoft, Amazon Gaming  
* embed galerie her  
* upozornění na končící hry  
* `/freegames history`  
* robustnější scraping + bezpečné fallbacky  



## 📈 v2.7 – Server Analytics & Summary
* `/serverstats` – přehled aktivit, hudby, miniher  
* leaderboard hráčů  
* `/myactivity` – osobní statistiky  
* týdenní shrnutí aktivit (bez AI – čistá data)  
* agregace hraných her + hudební historie  



## 🌐 v2.8 – Web Dashboard (Pi-hosted)
* běžící přímo na Raspberry Pi (Flask nebo FastAPI)  
* živé zobrazení právě hrané hudby  
* vizuální konfigurace kanálů, nastavení, cron úloh  
* log viewer + jednodušší diagnostika  
* mobile-friendly UI  



## 💎 v3.0 – Ježíš Discord Bot PRO
* multi-language režim (CZ / EN / SK)  
* modulární plugin systém  
* oddělené konfigurace per-guild  
* základní companion web app (PWA)  
* příprava na více instancí (cluster-ready architektura)  



---

## 📄 Licence

Zvolte licenci dle potřeby (např. MIT). Přidejte `LICENSE` soubor do repozitáře.

---

## 🙌 Poděkování

* `discord.py` tým a komunita
* Autoři `yt-dlp` a `ffmpeg`


