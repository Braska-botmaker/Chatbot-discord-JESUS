# Changelog

Všechny významné změny v tomto projektu jsou dokumentovány zde.

## [2.0] – 2025-11-17 – MAJOR VOICE & STREAMING FIXES 🎵

### 🔧 Opraveno

#### Voice Connection Stability (KRITICKÉ)
- ✅ **Timeout handling pro voice connect/move** – Přidáno `asyncio.wait_for()` s 8s timeoutem pro každý voice operaci
- ✅ **Exponential backoff retry** – Pokud voice selhání, bot se sám pokusí reconnectovat až 3x s progressivním čekáním
- ✅ **Improved `wait_until_connected()`** – Nyní až 15 pokusů s progressivním delay (až 4.5s celkem), místo pevného 3s
- ✅ **Voice state persistence** – Bot si pamatuje poslední voice kanál a automaticky se tam reconnectuje při selhání
- ✅ **Watchdog system** – Pokud bot ztratí voice během přehrávání, automaticky se reconnectuje (max 1x za 90 sekund)

#### FFmpeg & YouTube Stream Quality
- ✅ **Nové FFmpeg reconnect options** – `-rw_timeout 5000000` (5s timeout pro read/write) pro stabilnější streamování
- ✅ **Vyšší bitrate buffer** – `-b:a 128k -bufsize 256k` pro méně buffering chyb
- ✅ **Správné HTTP headers** – YouTube teď dostane User-Agent a ostatní headers z yt-dlp (`http_headers` v YDL_OPTS)
- ✅ **yt-dlp socket timeout** – Přidáno `socket_timeout: 30` pro yt-dlp extrakci

#### Error Handling & Diagnostics
- ✅ **Lepší error messages** – Nové descriptivní chyby pro timeout, forbidden access, disconnect cases
- ✅ **Queue persistence** – Pokud audio loading selhá, skladba se vrátí do fronty místo aby se ztratila
- ✅ **Fallback audio codec** – Pokud `FFmpegOpusAudio.from_probe` neexistuje, fallback na `FFmpegPCMAudio`
- ✅ **Better `!vtest` diagnostika** – Delší timeout pro test tónu (3s) plus retry logika

### 📝 Změny kódu

**Core functions:**
- `ensure_voice()` – Kompletní rewrite s timeouty a robustním error handlingem
- `ensure_voice_by_guild()` – Přidáno reconnect validation a timeout na connect/move
- `wait_until_connected()` – Nyní s progressivním delay a více pokusy
- `play_next()` – Pokud loading audio selhá, skladba se vrátí do fronty + lepší error messages
- `ytdlp_extract()` – Přidáno retry na timeout (2 pokusy)
- `voice_watchdog()` – Zvýšená frekvence (30s místo 20s) a delší throttle (90s místo 60s)

**Configuration:**
- `YDL_OPTS` – Přidáno `socket_timeout: 30` a `http_headers`
- `FFMPEG_OPTIONS` – Zvýšeno z `-vn -ac 1` na `-vn -ac 1 -b:a 128k -bufsize 256k`
- `FFMPEG_RECONNECT` – Přidáno `-rw_timeout 5000000 -nostdin`

### 📦 Dependencies
- Updated `requirements.txt` – `discord.py>=2.0` (bylo bez verze), `requests>=2.28`

### 🧪 Testing
Všechny následující scenáře by teď měly fungovat bezTimeoutError:
- `!play <YouTube URL>` – Ani slabší internet by neměl způsobit selhání
- Změna voice kanálu během přehrávání – Bot se automaticky přesune
- Rozpad voice connectionu – Bot se sám reconnectuje
- `!vtest` – Více tolerancí na pomalou síť

### 📚 Dokumentace
- Updated `README.md` – Nová sekce o opravách v v2.0
- Přidáno `CHANGELOG.md` (tento soubor)

---

## [1.4.0] – Previous stable

- 🎁 `!hryzdarma` – Free games command
- 🔄 Hra zdarma automation (20:10 CET)
- 📢 Steam + PlayStation Blog scraping
- 🙏 Bible verses & streaks
- 🎮 Game blessing system
- 📖 Bible verse command `!verš`

---

## [1.0.0] – Initial Release

- Basic music playback from YouTube
- Voice channel detection & auto-join
- Daily messages (morning/evening)
- Epic Games free games feed
- Player blessing system
