# 🎁 Hry Zdarma – Dokumentace (v2.6.2)

Kompletní guide na systém bezplatných her v Ježíši Discord Botu.

---

## 📋 Obsah

* [Přehled](#-přehled)
* [Zdoje her](#-zdroje-her)
* [Příkazy](#-příkazy)
* [Nastavení](#-nastavení)
* [Automatické odesílání](#-automatické-odesílání)
* [Technické detaily](#-technické-detaily)
* [Řešení problémů](#-řešení-problémů)

---

## 🎮 Přehled

Bot automaticky sbírá bezplatné hry z **5+ platforem** a odesílá je na Discord s:

- 🖼️ **Obrázky her** (z platformy API)
- 💰 **Cena** – Původní cena + "ZDARMA"
- ⏰ **Sleva do** – Kdy skončí bezplatná dostupnost
- 🏢 **Platforma** – S logem (Epic, Steam, PlayStation, GOG, Prime Gaming)
- 🔘 **Tlačítka** – ♥️ Wishlist, 📤 Share, 🔗 Otevřít

### Nové v2.6.2
- ✨ Jednotlivé barevné embedy pro každou hru (ne seznam)
- 🔘 Interaktivní tlačítka s emoji
- 🖼️ Automatické obrázky her
- 📱 Optimalizované pro mobil

---

## 🌐 Zdroje her

### 🟣 Epic Games
- **URL:** `https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions`
- **Typ:** Oficiální API
- **Frekvence:** Pondělí + Čtvrtek (změny her každý týden)
- **Data:** Title, obrázek, cena, datum vypršení
- **Filtr:** `discountPrice == 0`
- **Příklady:** Sims 4, Civilization, Ghostbusters atd.

### 🎮 Steam
- **URL:** `https://store.steampowered.com/search/?maxprice=0&specials=1`
- **Typ:** Web scraping s regex
- **Frekvence:** Různá (obvykle víkendy)
- **Data:** Title, AppID (→ obrázek), cena
- **Filtr:** Cena `0,00 Kč`, `-100%`, `Free`, nebo prázdná
- **Příklady:** One Gun Guy, Team Fortress 2, Dota 2

**Steam Image URL:**
```
https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{APP_ID}/header.jpg
```

### 🎯 PlayStation Plus
- **URL:** `https://blog.playstation.com/tag/playstation-plus/feed/`
- **Typ:** RSS feed
- **Frekvence:** Měsíčně (obvykle 1. den měsíce)
- **Data:** Nadpisy a linky z blogů
- **Filtr:** Poslední články ze tagu `playstation-plus`

### ⭐ GOG
- **URL:** `https://www.gog.com/games/ajax/filtered?mediaType=game&price=free&sortBy=trending`
- **Typ:** API
- **Frekvence:** Různá
- **Data:** Title, URL, cena
- **Filtr:** `price=free`

### 🔶 Prime Gaming
- **URL:** `https://gaming.amazon.com/`
- **Typ:** Web scraping + Reddit fallback
- **Frekvence:** Týdně (Amazon mění hry každý pátek)
- **Data:** Názvy her z Amazon stránky
- **Fallback:** Reddit r/FreeGames vyhledávání
- **Příklady:** Need for Speed, FIFA, Hitman atdy.

---

## 📡 Příkazy

### `/freegames`

Zobrazí až **10 bezplatných her** s embedy.

```
/freegames
```

**Odpověď:**
- Jednotlivý embed pro každou hru
- S obrázkem, cenou, datem vypršení
- Tlačítka: ♥️ ♥ 📤 🔗

### `/freegames` → Tlačítka

| Tlačítko | Akce |
|----------|------|
| 🔗 Otevřít | Otevře store v nový okno |
| ♥️ | Přidá do wishlistu (poznámka) |
| 📤 | Sdílí linku přátelům |

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
"gog" → "⭐ GOG"
"amazon" / "prime" → "🔶 Prime Gaming"
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

### 🎁 Chybí hry z určité platformy

**Příčiny:**
1. Platforma nemá aktuálně zdarma hry
2. API je dočasně nedostupné
3.Timeout při stažení (6s limit)

**Řešení:**
- Spusť `/freegames` ručně
- Zkontroluj logs bota:
  ```
  [freegames] Epic error: ...
  [freegames] Steam error: ...
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
- Tlačítka jsou vidět i na mobilu

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

