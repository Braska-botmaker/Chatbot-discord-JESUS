# 📜 CHANGELOG – Ježíš Discord Bot

Všechny změny v tomto projektu jsou zaznamenány v tomto souboru.

---

## [v2.7.1] – 2026-01-04

### ✨ Nové funkce

#### 📊 Global Statistics Tracking – Kompletní systém statistik
- **Persistent counter** pro všechny metriky uložený v `bot_data.json`
- ✅ **All-time metrics** (celoživotní sledování):
  - `songs_played_total` – Počet všech přehraných skladeb
  - `xp_total` – Agregované XP všech hráčů (all-time)
  - `game_hours_total` – Součet všech herních hodin (all-time)
- ✅ **Weekly metrics** (resetují se každý týden):
  - `weekly_songs_played` – Skladby přehrané v aktuálním týdnu
  - `weekly_xp_gained` – XP získané v aktuálním týdnu
  - `weekly_game_hours` – Herní hodiny v aktuálním týdnu
  - `last_weekly_reset` – Timestamp posledního resetu

#### 🎵 Přesný počet přehraných skladeb
- ❌ Zrušen odhad na základě XP (nepřesný, XP pochází z mnoha zdrojů)
- ✅ Přidán přesný counter, který se inkrementuje v `play_next()`
- ✅ Uloženo v `stats_data["songs_played_total"]`
- ✅ `/serverstats` nyní zobrazuje skutečný počet skladeb (ne odhad)

#### 📈 Weekly Tracking – Sledování aktivit za týden
- ✅ **Inkrementace all-time metrics:**
  - `increment_songs_played()` – Volá se v `play_next()` po přehrání skladby
  - `increment_xp_stats(xp_amount)` – Volá se v `add_xp_to_user()` po přidělení XP
  - `increment_game_hours(hours)` – Volá se v `track_user_activity()` při sledování her
- ✅ **Reset weekly metrics v send_weekly_summary():**
  - `reset_weekly_stats()` – Resetuje všechny weekly metriky po odeslání summary
  - Automaticky se volá po zobrazení týdenního shrnutí
  - Uloží timestamp resetu pro audit trail

#### 📅 Vylepšená Weekly Summary
- ✅ Zobrazuje teď 3 klíčové metriky:
  - ⏱️ **Čas hrání** – Celkový čas ze `game_activity` (poslední 7 dní)
  - ⭐ **XP v týdnu** – `weekly_xp_gained` (nové)
  - 🎵 **Skladby** – `weekly_songs_played` (nově přesný counter)
- ✅ Reset všech weekly stats po odeslání
- ✅ Print debug info: zobrazuje all-time stats po resetu

#### 💾 JSON Persistence
- ✅ `load_stats_from_storage()` – Načítá statistiky z `bot_data.json` v `on_ready()`
- ✅ `save_stats_to_storage()` – Asynchronně ukládá po každé změně
- ✅ Struktura: `db["stats"]` s 8 klíči (all-time + weekly + reset timestamp)
- ✅ Bezpečné načtení s fallback default hodnotami (0 nebo None)

### 🔧 Technické vylepšení

#### Thread-safety & Race Conditions
- ✅ Všechny `increment_*` funkce jsou synchronní (bez async)
- ✅ Ukládání do JSON se provádí asynchronně (`asyncio.create_task()`)
- ✅ Všechny funkce mají `global stats_data` deklaraci
- ✅ Bez conflicts s ostatními systémy (`game_activity`, `user_xp`)

#### Optimization
- ✅ Minimální overhead – inkrementace je O(1) operace
- ✅ Asynchronní I/O neblokuje hlavní loop
- ✅ Weekly summary task má `@before_loop` pro správný startup

#### Code Quality
- ✅ Žádné zdvojení dat – všechny funkce se volají jen jednou
- ✅ Zálohy v print debug statements pro audit trail
- ✅ Správná error handling se try/except bloky

### 📝 Změny v příkazech

#### `/serverstats` – Aktualizace
- ✅ Zobrazuje teď skutečný počet skladeb z `stats_data["songs_played_total"]`
- ❌ Zrušen odhad na základě XP (proporcí 1-2 XP)
- ✅ Stejné formáty a emojis jako dříve

#### `send_weekly_summary()` task – Rozšíření
- ✅ Zobrazuje 3 metriky místo 2
- ✅ Uloží weekly stats PŘED resetem do lokálních proměnných
- ✅ Reset se provede PO odeslání všech zpráv (důležité!)
- ✅ Debug print s all-time stats

### ✅ Testování

- ✅ Bez syntax errors – kompletní kontrola kódu
- ✅ `/profile` příkaz není ovlivněn – používá jiné datové zdroje
- ✅ Všechny increment funkce jsou volány správně a jen jednou
- ✅ Persistence otestována – správné ukládání do JSON

---

## [v2.7] – 2026-01-04

### ✨ Nové funkce

#### Server Analytics & Summary – kompletní přehled aktivit 📊
- **4 nové slash commands** pro analytiku a statistiky serveru (v2.7)
  
##### `/serverstats` – Přehled serverových aktivit
- 👥 Celkový počet uživatelů a aktivních hráčů
- ⭐ Agregované Experience Points na serveru
- 🎵 Počet skladeb v běžných hudebních frontách
- 🏆 Top 5 nejhranějších her na serveru

##### `/leaderboard` – Leaderboard Top 10
- 🏆 Seřazení hráčů podle Experience Points (XP)
- 📊 Zobrazení levelu pro každého hráče
- 🔥 Verse streak (počet dní modlitby) pro top hráče
- 🎖️ Vizuální pořadí s pozicemi

##### `/myactivity` – Osobní profil & dosažení
- ⭐ Tvoje aktuální XP a level
- 🔥 Tvůj verse streak (počet dní v řadě)
- 🎯 Top 5 tvých nejhranějších her s dobou hrání
- 🏅 Automatické dosažení (Achievements):
  - 🌟 Veterán (100+ XP)
  - 👑 Mistr (500+ XP)
  - 🔥 Věrný (7+ dnů streaku)
  - 🎮 Hráč (3+ různých her)

##### `/weeklysummary` – Týdenní trend analýza
- 📅 Analýza poslední 7 dnů
- ⏱️ Celkový čas strávený hráním na serveru
- 👥 Počet aktivních hráčů v týdnu
- 🏆 Top 5 hráčů týdne podle hrané doby

#### Agregace dat z multiple zdrojů 📈
- **XP systém**: Sledování experience z hudby, miniher, interakcí
- **Game activity**: Agregace všech her hraných všemi uživateli
- **Verse streak**: Kombinace modlitební aktivity s leaderboardem
- **Music history**: Sledování skladeb v hudbě frontách

### 🎯 Vylepšení UX

- Barevné embedy s logickými sekcemi pro přehlednost
- Emojis pro jasnou identifikaci údajů
- Anti-cheat ochrana proti falšování dat
- Fallback error handling pro chybějící data

### 📝 Dokumentace

- Aktualizován README.md – přidány v2.7 commands
- Aktualizován header bot.py na v2.7
- Aktualizován /version command s novým popisem

---

## [v2.6.7] – 2025-12-18

### 🔧 Bugfixy & Optimalizace

#### Oprava datetime importu v Epic Games sekci 🐛
- **Problém:** `from datetime import datetime` v Epic Games sekci přepsal globální `datetime` modul
- **Vliv:** Způsoboval `TypeError: type object 'datetime.datetime' has no attribute...` v STEAM sekci
- **Řešení:** Změněno na `from datetime import datetime as dt_class`
- **Výsledek:** Steam Reddit hry se nyní správně parsují a posílají

#### Zlepšení popisků polí u Steam her 📝
- **Změna:** `⏰ Free Until:` → `⏰ Posted:` (specificko pro Steam Reddit, kde máme "Posted Xd/Xh/Xm ago")
- **Logika:** Podmíněné zobrazování dle zdroje: Steam = "Posted", ostatní = "Free Until"
- **Aplikace:** Obě místa - `/freegames` command a `send_free_games()` task (20:10 CET)

#### Vylepšení logo URL adres 🎯
- **Starý problém:** Imgur links byly zablokované/neplatné
- **Řešení:** Nahrazeny oficiálními CDN URL z epicgames.com, steampowered.com, playstation.com
- **Fallback:** Emoji loga v titulu (🟣 Epic, 🎮 Steam, atd.) - vždy viditelná

### ✨ Vylepšení UX

- Debug output v logu pro lepší diagnostiku STEAM sekce
- Čitelnější chybové zprávy při parsování Reddit postů
- Lepší viditelnost emoji log v embedu titulu

---

## [v2.6.6] – 2025-01-23

### ✨ Nové funkce

#### Steam Limited-Time Giveaways přes Reddit API 🎮
- **Zdroj:** `/r/FreeGameFindings` subreddit – veřejné Reddit API bez autentifikace
- **Filtrování:** Pouze příspěvky s `[Steam]` tagem, automatické vynechání `[psa]`, `[question]`, `[other]`, `[expired]`, `[ended]`
- **Engagement metrika:** Zobrazení upvotes a počtu komentářů (`👍 {upvotes} | 💬 {comments}`)
- **Limit:** Maximum 5 giveaways per výzva (anti-spam ochrana)
- **Časový údaj:** "Posted Xd/Xh/Xm ago" format

#### Filtrování Reviews u Steam Reddit 🔍
- **Skrytí Reviews pole** pro Steam Reddit zdroj (relevantní pouze pro Epic Games s % slevou a PS+ status)
- Podmíněné zobrazování: `if "reddit" not in source.lower()`

### 🔧 Bugfixy & Optimalizace

- Synchronizace Reviews pole across `/freegames` a `send_free_games()` task (20:10 CET)
- Konsistentní formátování cen přes všechny 3 zdroje
- Test utility `tools/test_steam_reddit.py` pro validaci Reddit integrace

### 📚 Dokumentace

- Aktualizováno: `README.md`, `FREE_GAMES.md`, verze pole v headeru
- Nový Steam Reddit zdroj zdokumentován v FREE_GAMES.md

---

## [v2.6.5] – 2025-01-22

### ✨ Nové funkce

#### Jednotný design embeda her zdarma 🎨
- **Synchronizace `/freegames` a automatického posílání** – Obě metody nyní používají identický formát
- **Lepší čitelnost polí:**
  - Price a Release Date **vedle sebe** (inline)
  - Reviews a Free Until **vedle sebe** (inline)
  - Obrázek umístěn **dolů** (full-width na konci)
- **PlayStation Plus články** – Všechny články v **jednom embedu** se seznamem odkazů
- **Odstraněno:** Supported Platforms pole (zbytečná informace)

### 🎯 Vylepšení

- Konzistentní vzhled napříč `/freegames` příkazem a automatickým odesílání (20:10 CET)
- Lepší organizace informací v embedech
- Čitelnější formátování pro Discord uživatele

---

## [v2.6.3] – 2025-01-22

### ✨ Nové funkce

#### Konsolidované zdroje her zdarma 🎮
- **Fokus na 3 stabilní zdroje:** Epic Games, Steam, PlayStation Plus
- Obrázky pro každou hru (Epic z keyImages API, Steam z header.jpg)
- Spolehlivost nad množstvím

#### Nový tool: `tools/free_games.py` 🛠️
- Komplexní nástroj pro testování platforem
- Detailní hlášení stavu jednotlivých zdrojů
- Export výsledků do JSON

### ❌ Odstraněno

- **GOG API** – Ztratila data (0 produktů), nepoužívat
- **Prime Gaming** – HTTP 404, Amazon endpoint není dostupný
- **Reddit r/FreeGames** – HTTP 403 Forbidden, anti-bot ochrana
- **IsThereAnyDeal** – HTTP 404, API endpoint byl odebrán

### 🔧 Bugfixy & Optimalizace

- Steam regex s DOTALL flag pro správné parsování nových řádků
- Odebráno 17 testovacích souborů
- source_status dict obsahuje jen 3 klíče: epic, steam, playstation
- Zmenšena bot.py o 152 řádků kódu

---

## [v2.6.2] – 2025-12-15

### ✨ Nové funkce

#### Free Games UI & Interactive Controls 🎮
- **Nový design her:** Každá hra má svůj embed s:
  - Obrázkem hry (z platformy API)
  - Tlačítky pro interakci (♥️ Wishlist, 📤 Share, 🔗 Otevřít)
  - Detaily: Cena, sleva do, platforma s logem
  - Barevné embedy dle zdroje (🟣 Epic, 🎮 Steam, 🎯 PlayStation, ⭐ GOG, 🔶 Prime Gaming)

- **Tlačítka na "🎵 Přehrávám":**
  - ⏭️ **Skip** – Přeskoč na další skladbu
  - ⏸️ **Pause/Resume** – Pozastavit/Obnovit přehrávání
  - 🔀 **Shuffle** – Zamíchat frontu skladeb

#### Prime Gaming Scraping ✅
- Implementován scraping Amazon Prime Gaming
- Fallback na Reddit r/FreeGames při selhání (detekce "One Gun Guy" atd.)
- Spolehlivé mapování na 🔶 Prime Gaming logo

#### Steam Free Games Filtr 🎮
- Vylepšený regex na vyhledávání skutečně bezplatných her
- Detekce ceny: `0,00 Kč`, `-100%`, `Free`, nebo prázdná (Steam skryje cenu)
- Automatické stažení obrázku z AppID: `https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{APP_ID}/header.jpg`

#### Auto-Send Free Games v 20:10 CET 📱
- Automatické odeslání až 12 her do kanálu
- Jednotlivé embedy s tlačítky (ne seznam v jednom embedu)
- Informativnější footer s detaily

### 🔧 Bugfixy & Optimalizace

- Epic Games parser teď sbírá: keyImage, originalPrice, effectiveDate
- Steam parser teď sbírá: obrázek z AppID
- Inteligentní mapování zdrojů (case-insensitive)
- Lepší error handling v bottonech (ephemeral responses)

### 📚 Dokumentace

- **NOVÝ SOUBOR:** `docs/FREE_GAMES.md` – Kompletní dokumentace Hry Zdarma
- Aktualizován README.md s v2.6.2 features

---

## [v2.6.1] – 2025-12-12

### ✨ Nové funkce

#### XP & Leveling Systém 🎮
- Nový command `/xp` pro zobrazení aktuální úrovně a XP
- XP odměny za hudební příkazy:
  - `/yt`, `/skip`, `/pause`, `/resume`, `/shuffle` – 1-2 XP s 20s cooldownem
- XP odměny za hlasovou aktivitu:
  - Automatické XP při vstupu do voice kanálu – 2-5 XP s 60s cooldownem
  - Bot musí aktivně přehrávat hudbu (anti-cheat ochrana)
- Persistent storage v `bot_data.json` – data přežívají restart
- Anti-cheat mechanismy:
  - Randomizované XP částky (nelze předpovídat farming)
  - Per-user cooldowny (brání spamování)
  - Ověření aktivní hudby (brání afk exploits)

#### Free Games Engine 3.0 – Opravy zdrojů 🎁
- ❌ **Odstraněno:** Ubisoft+ (bez veřejného API se strukturovanými daty)
- ❌ **Odstraněno:** Amazon Prime Gaming (vyžaduje autentizaci, nespolehlivé regex)
- ✅ **Přidáno:** IsThereAnyDeal API (spolehlivý agregátor s FREE filtrem)
- ✅ **Přidáno:** Reddit r/FreeGames feed (community-verified submissions, filtruje [F2P] permanentní hry)
- Výsledek: 4+ spolehlivé zdroje bez nutnosti autentizace

#### Anglické Příkazy 🌐
- Všechny slash commands převedeny na angličtinu pro universalitu:
  - `/yt`, `/skip`, `/pause`, `/resume`, `/stop`, `/leave`, `/queue`, `/shuffle`, `/voicetest`
  - `/verse`, `/bless`, `/biblicquiz`
  - `/xp`, `/freegames`, `/commands`, `/version`, `/diag`
  - `/setchannel`, `/config`
- Help texty a chybové zprávy zůstávají v **češtině**

### 🔧 Bugfixy & Optimalizace

- Opraveno XP storage – žádné duplikáty v bot_data.json
- Optimalizace voice event detekce – 1s delay pro ověření bot status
- Lepší error handling v `/freegames` – každý zdroj má vlastní try/except blok
- Cooldown tracking je efektivnější (per-user dictionary)

### 📚 Dokumentace

- Aktualizován README.md s v2.6.1 features
- Přidán CHANGELOG.md pro trackování verzí
- Zjednodušena dokumentace (odstraněny zastaralé verze)

### ⚠️ Breaking Changes

- Všechny příkazy nyní v angličtině – uživatelé musí aktualizovat `/yt` místo `/yt` (případně)
- Free games `/freegames` nyní bez Ubisoft+ a Prime Gaming
- Změna úložiště XP: všichni uživatelé začínají s 0 XP

### 🔄 Backward Compatibility

- Starý `bot_data.json` je automaticky migrován (XP data se resetují)
- Všechny starší konfigurace kanálů zůstávají funkční
- Bible verše a požehnání zůstávají v češtině

---

## [v2.6] – 2025-12-01

### ✨ Nové funkce

- Rozšířeno na 6 zdrojů free her (Epic, Steam, PlayStation, GOG, Ubisoft+, Prime Gaming)
- Per-source status reporting v `/freegames` embed (✅/❌)
- Robustnější error handling pro každý zdroj

### 🔧 Bugfixy

- Opraveno selhání `get_free_games()` když jeden zdroj selže
- Zlepšena cache validace (6 hodin TTL)

---

## [v2.5] – 2025-11-15

### ✨ Nové funkce

- `/setchannel <typ> <kanál>` – per-guild konfigurace kanálů
- `/config` – zobrazení aktuální konfigurace serveru
- Persistent config storage v `bot_data.json`

### 🔧 Bugfixy

- Opraveno hledání `požehnání🙏` a `hry_zdarma💵` kanálů
- Validace admin oprávnění v config příkazech

---

## [v2.4.1] – 2025-10-20

### ✨ Nové funkce

- YouTube playlist support – `/yt <playlist_url>` přidá všechny skladby
- `/shuffle` – náhodně zamíchá pořadí skladeb ve frontě
- Odhad času playlistu – zobrazuje celkový čas před přidáním
- Batch progress feedback – "⏳ Přidávám: 5/24 skladeb..."

### 🔧 Bugfixy

- Duplikát blocking na playlistech
- Zlepšena duplikát detekce v `/yt`

---

## [v2.4] – 2025-09-10

### ✨ Nové funkce

- Blokace duplikátních skladeb v frontě
- Odhad času fronty – `/queue` a `/yt` zobrazují zbývající čas
- Cachování doby trvání skladeb
- Rozšíření biblické kviz databáze na 32 otázek

### 🔧 Bugfixy

- Automatické čištění URL setu po přehrání
- Zlepšeno error handling v hudebních příkazech

---

## [v2.3.2] – 2025-08-05

### ✨ Nové funkce

- Multi-server thread-safety – guild-level locks
- Real-time herní statistiky bez race conditions
- `/profile [@user]` – zobrazení XP, TOP 5 her, rankingu
- Personalizovaná požehnání pro 54+ her
- Auto-role: 🎮 Gamer, 🌙 Night Warrior, ⛪ Weekend Crusader
- XP systém: 8 úrovní (🔰 Učedník → 👑 Apoštol)

### 🔧 Bugfixy

- Opraveno race condition v periodickém game tracking
- Zlepšeno error handling s JSON storage

---

## [v2.2] – 2025-06-15

### ✨ Nové funkce

- Herní tracking – bot sleduje co hráči hrají
- Automatické role při detekci herní aktivity
- Minihry: `/biblickykviz`, `/versfight`, `/rollblessing`

---

## [v2.1] – 2025-04-20

### ✨ Nové funkce

- Slash commands na `/yt`, `/verse`, `/bless` apod.
- Automatické ranní/večerní zprávy s biblickými verši
- Požehnání pro hráče (reaguje na `on_member_update` game status)

---

## [v2.0] – 2025-02-10

### ✨ Nové funkce

- Základní hudební přehrávání z YouTube (yt-dlp)
- Voice kanál support (FFmpeg)
- Bible verses API integraci
- Emoji reactions na různé akce

---

## [v1.0] – 2024-12-01

### ✨ Nové funkce

- Počáteční vydání
- Základní Discord bot s prefix commands
- Jednoduchá hudba a verše

---

## 📝 Vydavatelské poznámky

### v2.6.1 – Co se chystá?

Tato verze se zaměřuje na:
- ✅ Spolehlivost free games engine (oprava nesprávných API)
- ✅ Přidání XP systému pro engagement
- ✅ Internacionalizace příkazů (English commands)

### Jak přispět?

Máte bug report nebo feature request? Napište na GitHub nebo zkontrolujte sekci Troubleshooting v README.md.

### Kompatibilita

- **Python:** 3.10+
- **discord.py:** 2.0+
- **Systém:** Linux, macOS, Windows, Raspberry Pi OS

---

**Poslední aktualizace:** 2025-12-12
**Maintainer:** Matěj Horák (Braska-botmaker)
