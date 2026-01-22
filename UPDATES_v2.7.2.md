# Bot Updates v2.7.2 – Error Handling & Data Protection

## 🚨 Hlavní Změny

### 1. **Discord Error Logging**
- ✅ Nová funkce `log_error_to_discord()` – chyby se automaticky posílají na Discord do kanálu `bot-logs`
- ✅ Všechny kritické chyby teď vidíš na Discordu, ne jen v terminálu
- Chyby se formátují do embed zpráv s časem a detaily

### 2. **Ochrana & Backup Dat** 🛡️
- ✅ Automatické vytváření backupu (`bot_data_backup.json`)
- ✅ Validace dat při čtení – pokud jsou data poškozená, načte se backup
- ✅ Validace dat před uložením – negativní čísla se opravují, neplatné typy se resetují
- ✅ Kontrola všech kritických datových struktur

### 3. **Vylepšené Týdenní Statistiky** 📊
- ✅ Task se spouští každou **neděli v 19:00 CET** (lze změnit)
- ✅ Fallback na `game_activity` data pokud jsou weekly data nízká
- ✅ Ověř se, že se data odesílají na Discord (ne jen do terminálu)
- ✅ Reset statistik se provádí jen pokud se úspěšně odeslaly na Discord
- ✅ Detailný logging s počtem odeslaných serverů a chyb

### 4. **Error Handling v Důležitých Funkcích**
- ✅ **leaderboard_command** – validace hodin, error logging
- ✅ **weeklysummary_command** – validace playtime, bezpečné parsování
- ✅ **track_game_activity_periodic** – počítá OK/chyby, logguje problémy
- ✅ **save_game_activity_to_storage** – čistí poškozená data, opravuje chyby
- ✅ **save_user_xp_to_storage** – validace XP hodnot
- ✅ **save_stats_to_storage** – validace všech statistik

---

## 🔧 Technické Detaily

### Nové Soubory
- `bot_data_backup.json` – automatický backup hlavního datového souboru

### Validace Dat
```python
# Příklady validace které se nyní provádějí:
- XP: max(0, int(xp))  # Nemůže být záporné
- Hodiny: max(0.0, float(hours))  # Nemůže být záporné
- Typ kontrol: isinstance(value, dict/int/float)
- Bezpečné parsování datetime
```

### Error Logging na Discord
Chyby se teď posílají s:
- 🚨 Titulem a popisem
- Detailnými zprávami
- Časem chyby
- Přivedou se do kanálu `bot-logs` (pokud existuje)

### Časový Schedule
```python
# send_weekly_summary – každou neděli v 19:00 CET
# Lze změnit v kódu:
# now_cet.weekday() == 6  # 6 = neděle (0-5 = pond-pátek)
# now_cet.hour == 19      # Hodina (0-23)
```

---

## 📋 Kontrolní List – Co bylo Opraveno

### Data Protection
- [x] Automatický backup starého souboru
- [x] Kontrola JSON syntaxu při čtení
- [x] Fallback na backup pokud je JSON poškozený
- [x] Validace všech číselných hodnot
- [x] Bezpečné parsování datetime

### Error Handling
- [x] Discord error logging funkcionalita
- [x] Try-except ve všech storage funkcích
- [x] Try-except v send_weekly_summary
- [x] Try-except v leaderboard a weeklysummary commands
- [x] Try-except v track_game_activity_periodic
- [x] Detailný logging s počty OK/chyb

### Týdenní Statistiky
- [x] Správný časový schedule (neděle 19:00)
- [x] Fallback na game_activity data
- [x] Validace dat před odesláním
- [x] Reset statistik se provádí až po úspěšném odeslání
- [x] Počítání serverů a chyb
- [x] Odesílání na Discord místo jen terminálu

---

## 🚀 Jak Používat

### 1. Kontrola Bot-logs Kanálu
Vytvoř na Discordu kanál `#bot-logs` a bot tam bude posílat všechny chyby.

### 2. Sledování Statistik
Hlídej Discord zprávy každou neděli v 19:00, tam se posílá týdenní summary.

### 3. Pokud se Chyby Objeví
- Podívej se na `bot-logs` kanál na Discordu
- Zkontroluj terminal pro detaily
- Pokud jsou data poškozená, bot se pokusí obnovit z `bot_data_backup.json`

### 4. Změna Času Weekly Summary
Pokud chceš jiný čas, změň v kódu (řádek s `send_weekly_summary`):
```python
# Změň z:
if not (now_cet.weekday() == 6 and now_cet.hour == 19 and now_cet.minute == 0):

# Na:
if not (now_cet.weekday() == 0 and now_cet.hour == 10 and now_cet.minute == 0):
# ^ pondělí v 10:00
```

---

## 📊 Verze
- **Předchozí**: v2.7.1
- **Aktuální**: v2.7.2
- **Status**: ✅ Ready to Deploy

## ✅ Testování
Všechny funkce byly otestovány na:
- ✅ Syntax chyby
- ✅ Type hints
- ✅ Data validace
- ✅ Error handling

---

## 🔄 Co se Stane když Bot Spadne?

1. **Při Startu**: Bot načte data, pokud budou poškozená, vrátí je z backupu
2. **Při Saveování**: Pokud se chyba stane, bot ji pošle na Discord a pokusí se znovu
3. **Při Weekly Summary**: Pokud se nepodaří odeslat, reset se neprovádí
4. **Automaticky**: Data se ukládají každých 5 minut (track_game_activity_periodic)

---

## 💡 Best Practices

1. Nech kanál `#bot-logs` aby viděl chyby
2. Periodicky kontroluj backup soubor
3. Hlídej weekly summary zprávy na Discordu
4. Pokud vidíš chyby v bot-logs, řekni mi o nich!

---

**Vytvořeno**: 22. ledna 2026
**Autor**: Jesus Bot v2.7.2
