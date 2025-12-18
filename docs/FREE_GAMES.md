# 🎁 Hry Zdarma – Dokumentace (v2.6.7)

Kompletní guide na systém bezplatných her v Ježíši Discord Botu.

---

## 📋 Obsah

* [Přehled](#-přehled)
* [Zdroje her](#-zdroje-her)
* [Příkazy](#-příkazy)
* [Nastavení](#-nastavení)
* [Automatické odesílání](#-automatické-odesílání)
* [Technické detaily](#-technické-detaily)
* [Řešení problémů](#-řešení-problémů)

---

## 🎮 Přehled

Bot automaticky sbírá bezplatné hry ze **3 spolehlivých platforem** a odesílá je na Discord s:

- 🖼️ **Obrázky her** – umístěny dolů v embedu (full-width)
- 💰 **Cena** – Původní cena + "ZDARMA" **vedle Release Date**
- 📅 **Release Date** – Datum vydání **vedle Price**
- ⭐ **Reviews** – Hodnocení **vedle Free Until**
- ⏰ **Free Until** – Kdy skončí bezplatná dostupnost **vedle Reviews**

### Nové v2.6.6
- 🎮 **Steam Reddit Giveaways** – Limitované giveaways z `/r/FreeGameFindings` s engagementem
- 🔍 **Filtrované Reviews** – Skryto u Steam Reddit (relevantní jen pro Epic % slevy)
- 📡 **Veřejné Reddit API** – Bez autentifikace, žádné API tokeny potřeba

### Nové v2.6.5
- ✨ **Jednotný design** – `/freegames` příkaz = automatické odesílání (20:10 CET)
- 🎯 **PlayStation Plus** – Všechny články v **jednom embedu**
- 📊 **Lepší čitelnost** – Pole organizována do 2 sloupců
- 🗑️ **Odstraněno:** Supported Platforms pole

---

## 🌐 Zdroje her

### 🟣 Epic Games ✅
- **URL:** `https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions`
- **Typ:** Oficiální API
- **Frekvence:** Pondělí + Čtvrtek (změny her každý týden)
- **Data:** Title, obrázek (keyImages), cena, datum vypršení
- **Filtr:** `isFreeGame == true` nebo `discountPrice == 0`
- **Příklady:** Sims 4, Civilization, Ghostbusters atd.
- **Status:** ✅ Pracující (2-3 hry zdarma obvykle)

### 🎮 Steam ✅
- **URL:** `https://store.steampowered.com/search/?maxprice=0&specials=1`
- **Typ:** Web scraping s regex
- **Frekvence:** Různá (obvykle víkendy)
- **Data:** Title, AppID (→ obrázek), cena
- **Filtr:** Cena `0,00 Kč`, `-100%`, `Free`, nebo prázdná
- **Regex:** `(https://store\.steampowered\.com/app/\d+[^"?]*)` s `re.DOTALL` flag
- **Příklady:** One Gun Guy, Team Fortress 2, Dota 2
- **Status:** ✅ Pracující (50+ her obvykle)

**Steam Image URL:**
```
https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{APP_ID}/header.jpg
```

### � Steam Limited-Time Giveaways ✅ **(NOVÉ v2.6.6)**
- **Zdroj:** `https://www.reddit.com/r/FreeGameFindings/new.json?limit=50` (Reddit veřejné API)
- **Typ:** Reddit JSON API (bez autentifikace)
- **Frekvence:** Real-time (všech 4 hodinách se spouští bot)
- **Data:** Title, giveaway URL, engagement (upvotes + comments), čas příspěvku
- **Filtr:** Pouze `[Steam]` tag, vynechání `[psa]`, `[question]`, `[other]`, `[expired]`, `[ended]`
- **Limit:** Maximum 5 giveaways per spuštění (anti-spam)
- **Příklady:** "Free: Company of Heroes 3", "[Steam] Control free until Wed"
- **Status:** ✅ Pracující (2-5 giveaways obvykle)

**Engagement Metrika:**
```
👍 {upvotes} | 💬 {comments}
```

**Časový Formát:**
```
Posted 2d ago, Posted 3h ago, Posted 15m ago
```

### �🎯 PlayStation Plus ✅
- **URL:** `https://blog.playstation.com/tag/playstation-plus/feed/`
- **Typ:** RSS feed
- **Frekvence:** Měsíčně (obvykle 1. den měsíce)
- **Data:** Nadpisy a linky z blogů
- **Filtr:** Poslední články ze tagu `playstation-plus`
- **Status:** ✅ Pracující (10+ článků obvykle)

---

## 📡 Příkazy

### `/freegames`

Zobrazí až **10 bezplatných her** s embedy.

```
/freegames
```



---

## ⚙️ Nastavení

### Kanál pro hry zdarma

Nastav dedikovaný kanál pro automatické zprávy:

```
/setchannel freegames #hry-zdarma
```

**Podrobněji:**
```
/config
```

---

## 🤖 Automatické odesílání

### ⏰ Čas
**Každý den v 20:10 CET** (Prague timezone)

### 📊 Co se pošle
- Až **12 bezplatných her**
- Jednotlivé embedy s obrázky
- Tlačítka pro interakci
- Pokud nejsou hry dostupné: ❌ zpráva

### 🔄 Jak to funguje
1. Bot se spustí
2. Sbere hry ze všech zdrojů
3. V 20:10 CET je pošle do kanálu
4. Pokud se bot spadne, hry se nepošlou (restart boot)

---

## 🔧 Technické detaily

### Struktura dat

Každá hra má strukturu:
```python
{
    "title": "Nazwa gry",
    "url": "https://store.epicgames.com/p/...",
    "source": "Epic Games",
    "image": "https://..../header.jpg",
    "original_price": "19.99 USD",
    "expire_date": "2025-12-18"  # Formát YYYY-MM-DD
}
```

### Caching
- **Interval:** 6 hodin (v2.6)
- **Důvod:** Omezit API calls
- **Fallback:** Pokud se cache obtěžuje, vrátí poslední data

### Error Handling
Každý zdroj má vlastní `try/except`:
- Epic: Timeout 5s
- Steam: Timeout 6s, regex parsing
- PlayStation: Timeout 6s, RSS parsing
- GOG: Timeout 6s, JSON parsing
- Prime Gaming: Timeout 6s + Reddit fallback
- Selhání zdroje = přeskočeno (ostatní fungují dál)

### Mapování
```python
"epic" → "🟣 Epic Games"
"steam" → "🎮 Steam"
"playstation" → "🎯 PlayStation Plus"
```

---

## 🆘 Řešení problémů

### ❌ Bot nepošle hry v 20:10

**Příčiny:**
1. Bot je offline → Restartuj
2. Kanál není nastaven → `/setchannel freegames #kanál`
3. Bot nemá práva → Zkontroluj permission `Send Messages`
4. API je nedostupné → Čekej na obnovu internetu

**Debug:**
```
/diag
```

### 🎁 Chybí hry

**Příčiny:**
1. Žádná platforma nemá aktuálně zdarma hry
2. API je dočasně nedostupné
3. Timeout při stažení (6-8s limit)

**Řešení:**
- Spusť `/freegames` ručně
- Zkontroluj logs bota:
  ```
  [freegames] Epic error: ...
  [freegames] Steam error: ...
  [freegames] PlayStation error: ...
  ```

### 🖼️ Chybí obrázky her

**Příčiny:**
1. API je pomalé (timeout)
2. Image URL je mrtvá

**Řešení:**
- Počkej a zkus znovu
- Obrázek se stáhne při příštím spuštění

### 📱 Embedy vypadají špatně na mobilu

- Bot se ujišťuje, že text je krátký (max 70 znaků)
- Obrázky se zobrazují správně na všech zařízeních

---

## 🚀 Budoucí plány

- [ ] Filtrování dle žádné platformy (`/freegames steam`)
- [ ] Persistentní wishlist (databáze)
- [ ] Notifikace když je hra už v wishlistu
- [ ] Voice command "Jaké jsou hry zdarma?"
- [ ] Multilingua (angličtina)

---

## 📞 Podpora

Máš problém? Koukni na:
- [CHANGELOG.md](../CHANGELOG.md) – Novějších verzí
- [README.md](../README.md) – Hlavní dokumentace
- [Diagnostika](/diag) – Bot diagnostic report
- [tools/free_games.py](../tools/free_games.py) – Tool pro testování

