# Changelog

Všechny významné změny v tomto projektu jsou dokumentovány zde.

## [2.1] – 2025-11-10 – Basic Music & Verses 🎵

### ✨ Nové Features

#### Music System (Basic)
- ✅ **`/yt <url>`** – Přehrávání z YouTube do voice kanálu
- ✅ **`/další`** – Přeskočení aktuální skladby
- ✅ **`/pauza` / `/pokračuj`** – Pauza a obnovení
- ✅ **`/zastav`** – Zastavení a vyčištění fronty
- ✅ **`/odejdi`** – Odpojení z voice
- ✅ **`/np`** – Zobrazení právě hrané skladby
- ✅ **`/fronta`** – Zobrazení fronty
- ✅ **`/vtest`** – Test voice připojení

#### Bible & Spirituality
- ✅ **`/verse`** – Náhodný biblický verš s denním streak systémem
- ✅ **`/bless @user`** – Osobní požehnání pro uživatele
- ✅ **`/freegames`** – Přehled her zdarma (Epic Games)

#### Scheduled Messages
- ✅ **Ranní zpráva** – 09:00 CET s biblickým veršem
- ✅ **Noční zpráva** – 22:00 CET
- ✅ **Free Games zpráva** – 20:10 CET s novými hrami zdarma

#### Core Features
- ✅ **Slash commands** – `/` prefix místo `!` (discord.py 2.0+)
- ✅ **Error handling** – Try/except na všech commandech
- ✅ **Multi-server support** – Základní podpora více serverů

### 🔧 Architecture

**Components:**
- `music_system` – Queue management s deque
- `scheduled_tasks` – Automatické zprávy (tasks.loop)
- `data_persistence` – JSON storage (bot_data.json)

**Commands:**
- Music: `/yt`, `/další`, `/pauza`, `/pokračuj`, `/zastav`, `/odejdi`, `/np`, `/fronta`, `/vtest`
- Verses: `/verse`, `/bless`, `/freegames`
- System: `/verze`, `/komandy`, `/diag`

### 📦 Dependencies
- `discord.py>=2.0` – Discord API bindings
- `yt-dlp>=2023.11` – YouTube downloading
- `python-dotenv>=0.19` – Environment variables
- `requests>=2.28` – HTTP requests
- `pytz>=2023.3` – Timezone handling
- `PyNaCl>=1.5` – Voice encryption

### 🎯 Initial Release
- Základní hudební systém
- Biblické verše a požehnání
- Automatické zprávy
- Multi-server ready

---

## [2.2] – 2025-11-15 – Minihry & Interakce 🎮

### ✨ Nové Features

#### Minigame System
- ✅ **`/biblickykviz`** – Biblické trivia otázky (10 otázek, expandovatelné)
- ✅ **`/versfight @user`** – Veršový duel mezi hráči (hlasování pro vítěze)
- ✅ **`/rollblessing`** – RNG požehnání s cooldown 1 hodina
- ✅ **`/profile [@user]`** – Kompletní herní profil s XP, TOP 5 herami, rankingem

#### XP System
- ✅ **XP bodování** – Body za každou miniher
- ✅ **Levely/Rank system**:
  - 🔰 Učedník (0-100 XP)
  - 📜 Prorok (100-250 XP)
  - 👑 Apoštol (250+ XP)

### 🔧 Code Changes

**Commands:**
- `biblickykviz_command()` – Biblický kviz
- `versfight_command()` – Veršový duel
- `rollblessing_command()` – RNG požehnání
- `profile_command()` – Zobrazení profilu

**Data Structures:**
- `user_xp` – Dictionary pro XP tracking
- `quiz_questions` – Seznam 10 biblických otázek

### 📦 Dependencies
- `requests>=2.28` – Pro HTTP requesty

### ✅ Backward Compatibility
- Všechny v2.1 features jsou zachovány

---

## [2.2.1] – 2025-11-20 – Enhanced Queue Display ✨

### ✨ Nové Features

#### Queue Display Improvements
- ✅ **Strukturovaný výpis fronty** – `/fronta` zobrazuje "Jméno – URL" formát
- ✅ **Auto-extrakce názvů** – Automatické získání názvů skladeb z YouTube

### 🔧 Code Changes

**Queue Display:**
- Vylepšené `_show_queue()` funkce s lepším formatováním
- Auto-title extraction z YouTube metadata

### ✅ Backward Compatibility
- Všechny v2.2 features jsou zachovány

---

## [2.3] – 2025-11-25 – Game Presence Engine 2.0 🎮

### ✨ Nové Features

#### Automatic Game Detection
- ✅ **Sledování hraných her** – Bot detekuje když uživatel začne/skončí hrát hru
- ✅ **Personalizovaná požehnání** – 54 různých her s vlastními požehnáními
- ✅ **Presence events** – `on_presence_update` event pro detekci her

#### Supported Games (54 total)
- Minecraft, League of Legends, Valorant, CS:GO, Fortnite, PUBG, Dota 2, Call of Duty, Overwatch, World of Warcraft, Final Fantasy XIV, Elden Ring, Dark Souls III, Baldur's Gate 3, Starfield, Cyberpunk 2077, The Witcher 3, Skyrim, a další...

### 🔧 Code Changes

**Game System:**
- `game_blessings` – Dictionary s blessings pro každou hru (54 her)
- `on_presence_update()` – Event pro detekci změn presence

**Blessing System:**
- Automatické posílání požehnání do `požehnání🙏` kanálu
- Informace o hráči a hrané hře v embedu

### ✅ Backward Compatibility
- Všechny v2.2 features jsou zachovány

---

## [2.3.1] – 2025-11-30 – Multi-Server Thread-Safety Patch 🔒

### ✨ Nové Features

#### Data Persistence & Tracking
- ✅ **Guild-level locks** – Bezpečné vytváření rolí bez race conditions
- ✅ **Periodic game tracking** – Měření doby hraní her každých 5 minut
- ✅ **Real-time herní statistiky** – Aktualizace bez konfliktu dat mezi servery
- ✅ **Multi-server ready** – Bezpečné pro paralelní operace na více serverech

#### XP & Role System
- ✅ **XP Tracking** – Automatické sledování XP hráčů z miniher
- ✅ **Auto-role assignment** – Automatické přidělování rolí dle aktivit:
  - 🎮 Gamer – Když hráč hraje hru
  - 🌙 Night Warrior – Když je online v noci (22:00-06:00)
  - ⛪ Weekend Crusader – Když je online o víkendech

### 🔧 Code Changes

**Threading/Locking:**
- `_guild_lock()` – Async context manager pro guild-level synchronizaci
- `_guild_locks` – Dictionary s asyncio.Lock na guild

**Data Storage:**
- `_load_data()` / `_save_data()` – JSON persistence
- `DATA_FILE` – `bot_data.json` pro globální storage
- `_g()` – Guild-specific namespace helper

**Functions:**
- `track_user_activity()` – Zaznamenání aktivity s optional game reset
- `assign_game_roles()` – Auto-přidělování rolí dle hry
- `track_game_activity_periodic()` – Background task (každých 5 minut)

### 📊 Data Structure
```json
{
  "verse_streak": {
    "user_id": streak_count
  },
  "game_activity": {
    "user_id": {"game": "game_name", "time": timestamp}
  },
  "user_xp": {
    "user_id": xp_points
  }
}
```

### ✅ Backward Compatibility
- Všechny v2.2 features jsou zachovány

---

## [2.4] – 2025-12-05 – Music QoL Pack 🎵

### ✨ Nové Features

#### Music System Improvements
- ✅ **Blokace duplicitních skladeb** – Detekuje pokud se uživatel pokusí přidat stejnou skladbu do fronty
- ✅ **Odhad času fronty** – `/fronta` a `/yt` zobrazují odhad zbývajícího času (⏱️ Odhad: ~45m 30s)
- ✅ **Cachování doby trvání** – Uloží délku skladby pro rychlejší výpočty
- ✅ **Automatické čištění URL setu** – Když se skladba přehraje nebo se fronta vymaže

#### Extended Content
- ✅ **Rozšířená biblická databáze** – 32 otázek v kvízu (místo 10) pro vyšší variabilitu

### 🔧 Code Changes

**Data structures:**
- `queue_urls_seen` – Novádict struktura pro tracking URL v queue per-guild
- `song_durations` – Cache pro délky skladeb pro rychlejší odhady

**Functions:**
- `_init_queue_urls_seen()` – Inicializuj prázdný set pro guild
- `_is_url_in_queue()` – Zkontroluj zda je URL v queue
- `_add_url_to_queue()` – Přidej URL do tracking setu
- `_remove_url_from_queue()` – Odeber URL z tracking setu
- `_clear_queue_urls()` – Vymažu všechny URL pro guild
- `_estimate_queue_duration()` – Odhad celkové doby trvání queue

### ✅ Backward Compatibility
- Všechny v2.3.1 features jsou zachovány
- Bez breaking changes

---

## [2.4.1] – 2025-12-05 – Playlist & Shuffle 🎶

### ✨ Nové Features

#### Playlist Support
- ✅ **`/yt <playlist_url>`** – Přehraj celý playlist do queue (detekce playlist URL automaticky)
- ✅ **`/shuffle`** – Náhodně zamíchej frontu (první skladba zůstane hrát)
- ✅ **Playlist detection** – Automatické rozpoznání playlist URL (youtube.com/playlist, list= parameter)

#### Performance Optimization
- ✅ **10-20x rychlejší import playlistů** – Změna z per-track extraction na batch extraction
- ✅ **Offline metadata** – Používá se default 180s duration (bez čekání na per-track extrakci)
- ✅ **Optimalizovaná yt-dlp config** – "extract_flat": "in_playlist" pro instant metadata

### 🔧 Code Changes

**Helper Functions:**
- `_is_youtube_playlist(url)` – Detekuje playlist URL (regex, youtube.com/playlist, list= param)
- `_shuffle_queue(guild_id)` – Shuffle s preservováním první skladby
- `extract_playlist_tracks(url)` – Batch extraction metadata z playlistů

**Command Updates:**
- `/yt` – Přidán conditional: if playlist → playlist_mode else → original single-track code (100% safe)
- `/shuffle` – Nový command pro shuffle fronty

**Optimizations:**
- Odstraněno per-track `ytdlp_extract()` volání pro playlisty
- Výsledek: 2+ minut import → 5-10 sekund import

### 🎯 Performance Metrics
- **Playlist 10 skladeb**: ~5-10 sekund (dříve 2+ minuty)
- **Import speedup**: 10-20x (batch extraction vs per-track)
- **Memory**: Lineárně s počtem skladeb (bez caching)

### 🧪 Testing
- ✅ Playlist detection – Testováno s různými playlist URL formáty
- ✅ Shuffle functionality – Ověřeno že první skladba zůstane
- ✅ YouTube playback – Zachován původní kód (100% backward compatible)
- ✅ Queue management – Fronta správně spravuje mix playlistů a jednotlivých skladeb

### ✅ Backward Compatibility
- ✅ Všechny v2.4 features jsou zachovány
- ✅ YouTube single-track playback 100% zachován (conditional routing)
- ✅ Bez breaking changes

---

## [2.5] – 2025-12-06 – Channel Config Pack ⚙️

### ✨ Nové Features

#### Per-Guild Configuration System (v2.5)
- ✅ **`/setchannel <typ> <kanál>`** – Admin-only command pro nastavení kanálů (Požehnání, Hry zdarma)
- ✅ **`/config`** – Zobrazení aktuální konfigurace serveru s admin-only přístupem
- ✅ **Centralizované ukládání** – Všechna nastavení se ukládají do `bot_data.json` (ne oddělený soubor)
- ✅ **Fallback mechanismus** – Pokud není kanál nastaven, bot si vyhledá kanál podle jména (backward compatibility)
- ✅ **Audit logging** – Všechny změny konfigurace se zaznamenávají v konzoli

#### Code Improvements
- ✅ **`_get_guild_all_config(db, gid)`** – Helper funkce pro načtení konfigurace z bot_data.json
- ✅ **`_save_guild_config_to_db(db, gid, typ, channel_id)`** – Async ukládání konfigurace
- ✅ **`_get_channel_for_type(guild, typ)`** – Vrací channel s fallbackem na staré hledání
- ✅ Integrováno do všech míst: `/send_morning_message`, `/send_night_message`, `/send_free_games`, `on_presence_update`

### 🔧 Opravy a Zlepšení

- ✅ **Optimalizovaný playlist import** – Removed per-track extraction, používá se defaultní duration 180s (10-20x rychlejší)
- ✅ **Discord Embed field size fix** – Rozděleny dlouhé embed fields na více menších (Discord limit 1024 chars)
- ✅ **Config persistence** – Konfigurace si přetrvá i po restartu bota

### 📝 Změny kódu

**Core functions:**
- `_get_guild_all_config()` – Nová helper funkce
- `_save_guild_config_to_db()` – Nová async helper funkce
- `_get_channel_for_type()` – Updatováno na nový config system
- `setchannel_command()` – Nový slash command (admin-only)
- `config_command()` – Nový slash command (admin-only)
- Všechny scheduled tasks – Updatovány na `_get_channel_for_type()`

**Configuration:**
- Přidáno `_get_guild_all_config()` a `_save_guild_config_to_db()` do `bot_data.json` managementu
- Odstraněno: `guild_config` dictionary, `CONFIG_FILE` (guild_config.json)

### 📚 Dokumentace
- Updated `README.md` – Verze v2.5, aktualizované příkazy a roadmapa
- Updated `/verze` command – Zobrazuje v2.5 s novými features
- Updated `/komandy` command – Přidán nový "Admin (v2.5)" section
- Updated `/diag` command – Verze v2.5

### 🔄 Backward Compatibility
- ✅ Všechny staré features z v2.4 a v2.4.1 jsou zachovány
- ✅ Fallback na staré hledání kanálů podle jména (pro servery bez konfigurace)
- ✅ Žádný breaking changes

---

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

---

## [2.4] – 2025-12-05 – Music QoL Pack 🎵

### ✨ Nové Features

#### Music System Improvements
- ✅ **Blokace duplicitních skladeb** – Detekuje pokud se uživatel pokusí přidat stejnou skladbu do fronty
- ✅ **Odhad času fronty** – `/fronta` a `/yt` zobrazují odhad zbývajícího času (⏱️ Odhad: ~45m 30s)
- ✅ **Cachování doby trvání** – Uloží délku skladby pro rychlejší výpočty
- ✅ **Automatické čištění URL setu** – Když se skladba přehraje nebo se fronta vymaže

#### Extended Content
- ✅ **Rozšířená biblická databáze** – 32 otázek v kvízu (místo 10) pro vyšší variabilitu

### 🔧 Code Changes

**Data structures:**
- `queue_urls_seen` – Novádict struktura pro tracking URL v queue per-guild
- `song_durations` – Cache pro délky skladeb pro rychlejší odhady

**Functions:**
- `_init_queue_urls_seen()` – Inicializuj prázdný set pro guild
- `_is_url_in_queue()` – Zkontroluj zda je URL v queue
- `_add_url_to_queue()` – Přidej URL do tracking setu
- `_remove_url_from_queue()` – Odeber URL z tracking setu
- `_clear_queue_urls()` – Vymažu všechny URL pro guild
- `_estimate_queue_duration()` – Odhad celkové doby trvání queue

### ✅ Backward Compatibility
- Všechny v2.3.1 features jsou zachovány
- Bez breaking changes

---

## [2.3.1] – 2025-11-30 – Multi-Server Thread-Safety Patch 🔒

### ✨ Nové Features

#### Data Persistence & Tracking
- ✅ **Guild-level locks** – Bezpečné vytváření rolí bez race conditions
- ✅ **Periodic game tracking** – Měření doby hraní her každých 5 minut
- ✅ **Real-time herní statistiky** – Aktualizace bez konfliktu dat mezi servery
- ✅ **Multi-server ready** – Bezpečné pro paralelní operace na více serverech

#### XP & Role System
- ✅ **XP Tracking** – Automatické sledování XP hráčů z miniher
- ✅ **Auto-role assignment** – Automatické přidělování rolí dle aktivit:
  - 🎮 Gamer – Když hráč hraje hru
  - 🌙 Night Warrior – Když je online v noci (22:00-06:00)
  - ⛪ Weekend Crusader – Když je online o víkendech

### 🔧 Code Changes

**Threading/Locking:**
- `_guild_lock()` – Async context manager pro guild-level synchronizaci
- `_guild_locks` – Dictionary s asyncio.Lock na guild

**Data Storage:**
- `_load_data()` / `_save_data()` – JSON persistence
- `DATA_FILE` – `bot_data.json` pro globální storage
- `_g()` – Guild-specific namespace helper

**Functions:**
- `track_user_activity()` – Zaznamenání aktivity s optional game reset
- `assign_game_roles()` – Auto-přidělování rolí dle hry
- `track_game_activity_periodic()` – Background task (každých 5 minut)

### 📊 Data Structure
```json
{
  "verse_streak": {
    "user_id": streak_count
  },
  "game_activity": {
    "user_id": {"game": "game_name", "time": timestamp}
  },
  "user_xp": {
    "user_id": xp_points
  }
}
```

### ✅ Backward Compatibility
- Všechny v2.2 features jsou zachovány

---

## [2.3] – 2025-11-25 – Game Presence Engine 2.0 🎮

### ✨ Nové Features

#### Automatic Game Detection
- ✅ **Sledování hraných her** – Bot detekuje když uživatel začne/skončí hrát hru
- ✅ **Personalizovaná požehnání** – 54 různých her s vlastními požehnáními
- ✅ **Presence events** – `on_presence_update` event pro detekci her

#### Supported Games (54 total)
- Minecraft, League of Legends, Valorant, CS:GO, Fortnite, PUBG, Dota 2, Call of Duty, Overwatch, World of Warcraft, Final Fantasy XIV, Elden Ring, Dark Souls III, Baldur's Gate 3, Starfield, Cyberpunk 2077, The Witcher 3, Skyrim, a další...

### 🔧 Code Changes

**Game System:**
- `game_blessings` – Dictionary s blessings pro každou hru (54 her)
- `on_presence_update()` – Event pro detekci změn presence

**Blessing System:**
- Automatické posílání požehnání do `požehnání🙏` kanálu
- Informace o hráči a hrané hře v embedu

### ✅ Backward Compatibility
- Všechny v2.2 features jsou zachovány

---

## [2.2.1] – 2025-11-20 – Enhanced Queue Display ✨

### ✨ Nové Features

#### Queue Display Improvements
- ✅ **Strukturovaný výpis fronty** – `/fronta` zobrazuje "Jméno – URL" formát
- ✅ **Auto-extrakce názvů** – Automatické získání názvů skladeb z YouTube

### 🔧 Code Changes

**Queue Display:**
- Vylepšené `_show_queue()` funkce s lepším formatováním
- Auto-title extraction z YouTube metadata

### ✅ Backward Compatibility
- Všechny v2.2 features jsou zachovány

---

## [2.2] – 2025-11-15 – Minihry & Interakce 🎮

### ✨ Nové Features

#### Minigame System
- ✅ **`/biblickykviz`** – Biblické trivia otázky (10 otázek, expandovatelné)
- ✅ **`/versfight @user`** – Veršový duel mezi hráči (hlasování pro vítěze)
- ✅ **`/rollblessing`** – RNG požehnání s cooldown 1 hodina
- ✅ **`/profile [@user]`** – Kompletní herní profil s XP, TOP 5 herami, rankingem

#### XP System
- ✅ **XP bodování** – Body za každou miniher
- ✅ **Levely/Rank system**:
  - 🔰 Učedník (0-100 XP)
  - 📜 Prorok (100-250 XP)
  - 👑 Apoštol (250+ XP)

### 🔧 Code Changes

**Commands:**
- `biblickykviz_command()` – Biblický kviz
- `versfight_command()` – Veršový duel
- `rollblessing_command()` – RNG požehnání
- `profile_command()` – Zobrazení profilu

**Data Structures:**
- `user_xp` – Dictionary pro XP tracking
- `quiz_questions` – Seznam 10 biblických otázek

### 📦 Dependencies
- `requests>=2.28` – Pro HTTP requesty

### ✅ Backward Compatibility
- Všechny v2.1 features jsou zachovány

---

## [2.1] – 2025-11-10 – Basic Music & Verses 🎵

### ✨ Nové Features

#### Music System (Basic)
- ✅ **`/yt <url>`** – Přehrávání z YouTube do voice kanálu
- ✅ **`/další`** – Přeskočení aktuální skladby
- ✅ **`/pauza` / `/pokračuj`** – Pauza a obnovení
- ✅ **`/zastav`** – Zastavení a vyčištění fronty
- ✅ **`/odejdi`** – Odpojení z voice
- ✅ **`/np`** – Zobrazení právě hrané skladby
- ✅ **`/fronta`** – Zobrazení fronty
- ✅ **`/vtest`** – Test voice připojení

#### Bible & Spirituality
- ✅ **`/verse`** – Náhodný biblický verš s denním streak systémem
- ✅ **`/bless @user`** – Osobní požehnání pro uživatele
- ✅ **`/freegames`** – Přehled her zdarma (Epic Games)

#### Scheduled Messages
- ✅ **Ranní zpráva** – 09:00 CET s biblickým veršem
- ✅ **Noční zpráva** – 22:00 CET
- ✅ **Free Games zpráva** – 20:10 CET s novými hrami zdarma

#### Core Features
- ✅ **Slash commands** – `/` prefix místo `!` (discord.py 2.0+)
- ✅ **Error handling** – Try/except na všech commandech
- ✅ **Multi-server support** – Základní podpora více serverů

### 🔧 Architecture

**Components:**
- `music_system` – Queue management s deque
- `scheduled_tasks` – Automatické zprávy (tasks.loop)
- `data_persistence` – JSON storage (bot_data.json)

**Commands:**
- Music: `/yt`, `/další`, `/pauza`, `/pokračuj`, `/zastav`, `/odejdi`, `/np`, `/fronta`, `/vtest`
- Verses: `/verse`, `/bless`, `/freegames`
- System: `/verze`, `/komandy`, `/diag`

### 📦 Dependencies
- `discord.py>=2.0` – Discord API bindings
- `yt-dlp>=2023.11` – YouTube downloading
- `python-dotenv>=0.19` – Environment variables
- `requests>=2.28` – HTTP requests
- `pytz>=2023.3` – Timezone handling
- `PyNaCl>=1.5` – Voice encryption

### 🎯 Initial Release
- Základní hudební systém
- Biblické verše a požehnání
- Automatické zprávy
- Multi-server ready

---
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
