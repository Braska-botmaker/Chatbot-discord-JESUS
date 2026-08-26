# ✝️ Ježíš Discord Bot

![Version](https://img.shields.io/badge/version-v2.8.2-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%7C%20Linux%20%7C%20Windows-informational)
![License](https://img.shields.io/badge/license-Custom%20Non--Commercial-lightgrey)

Discord bot (Python, [discord.py](https://github.com/Rapptz/discord.py)) pro křesťanskou/herní
komunitu: přehrává hudbu z YouTube, posílá biblické verše, žehná hráčům, hlídá free hry
a sleduje aktivitu serveru přes XP a žebříčky.

Navržený na běh 24/7 na Raspberry Pi, ale funguje stejně dobře lokálně na Windows, Linux i macOS.

**➡️ Chceš bota rozjet?** Jdi rovnou na [docs/INSTALL.md](docs/INSTALL.md) – 5 minut na desktopu,
nebo kompletní návod pro Raspberry Pi.

---

## Obsah

- [Co bot umí](#-co-bot-umí)
- [Příkazy](#-příkazy)
- [Instalace](#-instalace)
- [Konfigurace](#-konfigurace)
- [Automatické zprávy](#-automatické-zprávy)
- [Řešení problémů](#-řešení-problémů)
- [Dokumentace](#-dokumentace)
- [Roadmapa](#-roadmapa)
- [Licence](#-licence)

---

## 🎯 Co bot umí

- 🎵 **Hudba z YouTube** – fronta, odhad délky, blokace duplicit, playlisty, shuffle
- 📖 **Biblické verše** – ranní/večerní zprávy + denní streak za `/verse`
- 🙏 **Požehnání** – automaticky při spuštění hry, i ručně přes `/bless`
- 🎁 **Free hry** – denní přehled z Epic Games, Steam (Reddit) a PlayStation Plus
- 🎮 **Minihry a XP** – biblický kvíz, veršový duel, RNG požehnání, levely a role
- 📊 **Server analytics** – leaderboardy, osobní profily, týdenní shrnutí
- ⚙️ **Per-server konfigurace** kanálů bez zásahu do kódu (`/setchannel`)

> 🎧 Spotify integrace je hotová v kódu, ale **odložená** na pozdější verzi – viz [Roadmapa](#-roadmapa).

---

## ⌨️ Příkazy

Kompletní přehled s ikonkami najdeš přímo v Discordu přes `/commands`.

### Hudba

| Příkaz | Popis |
|---|---|
| `/yt <url>` | Přidá skladbu nebo playlist do fronty (YouTube) |
| `/skip` | Přeskočí aktuální skladbu |
| `/pause` / `/resume` | Pozastaví / obnoví přehrávání |
| `/stop` | Zastaví přehrávání a vyčistí frontu |
| `/leave` | Odpojí bota z voice kanálu |
| `/np` | Zobrazí právě hranou skladbu (s ovládacími tlačítky) |
| `/queue` | Vypíše frontu s odhadem celkového času |
| `/shuffle` | Zamíchá frontu (aktuální skladba zůstává první) |
| `/voicetest` | 3s testovací tón – ověří FFmpeg/voice připojení |

### Bible a minihry

| Příkaz | Popis |
|---|---|
| `/verse` | Náhodný biblický verš + denní streak |
| `/bless [@user]` | Krátké požehnání pro tebe nebo jiného hráče |
| `/biblicquiz` | Biblický kvíz na 10 otázek |
| `/versfight @user` | Veršový duel s hlasováním komunity |
| `/rollblessing` | RNG požehnání (cooldown 1 hodina) |

### Statistiky a server

| Příkaz | Popis |
|---|---|
| `/profile [@user]` | Osobní profil – XP, level, TOP hry, ranking |
| `/serverstats` | Přehled aktivity celého serveru |
| `/leaderboard` | Top 10 hráčů podle XP a odehraných hodin |
| `/weeklysummary` | Týdenní shrnutí (posílá se i automaticky) |
| `/freegames` | Aktuální free hry (Epic, Steam, PlayStation Plus) |

### Admin

| Příkaz | Popis |
|---|---|
| `/setchannel <typ> <kanál>` | Nastaví kanál pro požehnání nebo free hry |
| `/config` | Zobrazí aktuální konfiguraci serveru |
| `/diag` | Diagnostika bota (FFmpeg, Opus, voice, živý yt-dlp test) |
| `/version` | Verze bota a přehled changelogu |

---

## 📥 Instalace

Zkrácená verze – plný návod (Discord token, systemd na Raspberry Pi, konfigurace) je
v **[docs/INSTALL.md](docs/INSTALL.md)**.

```bash
git clone <URL_TOHOTO_REPA>.git
cd Chatbot-discord-JESUS

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r config/requirements.txt

cp config/.env.example .env      # vlož DISCORD_TOKEN
python bot.py
```

Hotové instalační skripty: `scripts/install-desktop.sh` (Linux/macOS), `scripts/install.bat`
(Windows), `scripts/install.sh` (Raspberry Pi, vč. systemd služby).

---

## ⚙️ Konfigurace

Jediná povinná proměnná v `.env` je `DISCORD_TOKEN`. Volitelné proměnné pro YouTube
přehrávání (`YTDLP_PLAYER_CLIENTS`, `YTDLP_COOKIES_FILE`) jsou popsané v
[docs/INSTALL.md](docs/INSTALL.md#-konfigurace-env).

Kanály pro ranní/večerní zprávy a free hry se nastavují přímo v Discordu:

```
/setchannel blessing <kanál>     – požehnání a biblické verše
/setchannel freegames <kanál>    – denní přehled free her
/config                          – zobrazí aktuální nastavení
```

Konfigurace je per-server a ukládá se do `bot_data.json` – žádná úprava kódu potřeba.

---

## ⏰ Automatické zprávy

Vše v časovém pásmu **Europe/Prague**:

| Čas | Co se pošle | Kam |
|---|---|---|
| 09:00 | Ranní biblický verš | kanál `blessing` |
| 20:10 | Přehled free her | kanál `freegames` |
| 22:00 | Večerní zpráva | kanál `blessing` |
| Neděle 19:00 | Týdenní shrnutí aktivity | kanál `blessing` |

---

## 🩺 Řešení problémů

Nejde hudba, voice, nebo se bot nespustí? → **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**

Rychlá první pomoc: spusť `/diag` v Discordu – ukáže stav FFmpeg/Opus/voice a živě otestuje,
jestli aktuálně funguje YouTube extrakce.

---

## 📚 Dokumentace

| Dokument | Obsah |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | Instalace, Discord token, konfigurace, produkční nasazení |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Řešení problémů, FAQ, čtení logů |
| [docs/FREE_GAMES.md](docs/FREE_GAMES.md) | Jak funguje systém free her (zdroje, formát, nastavení) |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Historie verzí |
| [privacy-policy.md](privacy-policy.md) | Ochrana osobních údajů |
| [terms-of-service.md](terms-of-service.md) | Podmínky služby |

---

## 🛣️ Roadmapa

**Aktuální verze: v2.8.2** – oprava YouTube přehrávání a voice spojení (DAVE protokol).
Detaily v [CHANGELOG.md](docs/CHANGELOG.md).

**Plánované:**

- 🎧 **Spotify Integration** – `/sp`, `/spauth`, Spotify Connect playback (hotovo v kódu, čeká na vydání)
- 🖥️ **Web Dashboard** – živé zobrazení hrané hudby, vizuální konfigurace, log viewer (Flask/FastAPI na Raspberry Pi)
- 🌍 **v3.0** – vícejazyčný režim (CZ/EN/SK), modulární pluginy, companion web app

Historie všech předchozích verzí (v1.0 → v2.8.2) je v [docs/CHANGELOG.md](docs/CHANGELOG.md).

---

## 📄 Licence

**Custom Non-Commercial License** – zkopírovat, upravovat a nekomerčně sdílet můžeš volně,
komerční využití vyžaduje souhlas. Autora ([Matěj Horák / Braska-botmaker](https://github.com/Braska-botmaker))
je třeba uvést a licenci zachovat v distribuovaných verzích. Plný text: [LICENSE](LICENSE).

---

## 🙌 Poděkování

`discord.py` tým a komunita · autoři `yt-dlp` a `FFmpeg` · zdroje free her: Epic Games,
Steam, PlayStation Blog, r/FreeGameFindings

---

Šťastné hraní a čtení! 🎵📖🎮
