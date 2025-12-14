# 📜 CHANGELOG – Ježíš Discord Bot

Všechny změny v tomto projektu jsou zaznamenány v tomto souboru.

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
