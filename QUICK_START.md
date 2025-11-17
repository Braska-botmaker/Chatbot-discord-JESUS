# ⚡ QUICK START – Upgrade na v2.0

## Pokud už máš bota spuštěného

### 1. Zastavit bota
```bash
# Pokud běží jako systemd služba:
sudo systemctl stop discordbot

# Pokud běží v terminálu:
Ctrl+C
```

### 2. Aktualizuj kód
```bash
cd <tvůj-bot-adresář>
git pull origin main
```

### 3. Aktualizuj balíčky
```bash
source .venv/bin/activate  # nebo .venv\Scripts\activate na Windows
pip install -r requirements.txt --upgrade
```

### 4. Spusť bota
```bash
# Terminal:
python bot.py

# Nebo systemd:
sudo systemctl start discordbot
```

### 5. Test
Zkontroluj že funguje:
- `!vtest` – test voice connectivity
- `!play <YouTube URL>` – test hudby
- `!diag` – kontrola všech komponent

---

## Nové features v v2.0

✅ **Automatický reconnect** – Bot se sám pokusí znovu připojit, když se voice ztratí  
✅ **Robustní timeout handling** – Žádné víc "TimeoutError", jen automatický retry  
✅ **Lepší YouTube streaming** – Správné HTTP headers, vyšší bitrate  
✅ **Watchdog system** –监視bot během přehrávání, automaticky reconnectuje  

---

## Pokud máš na Raspberry Pi

```bash
# Zkontroluj, že je FFmpeg:
ffmpeg -version

# Zkontroluj Opus lib:
dpkg -l | grep libopus

# Pokud chybí:
sudo apt install -y ffmpeg libopus0

# Pak upgrade:
cd /opt/discordbot
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart discordbot

# Kontrola logů:
journalctl -u discordbot -f
```

---

## Co se změnilo v kódu

| Funkce | Co se zlepšilo |
|--------|---|
| `ensure_voice()` | Timeout 8s, retry logika, lepší errors |
| `play_next()` | Fallback codec, queue return na fail |
| `wait_until_connected()` | 15 pokusů místo 6, progressivní delay |
| `ytdlp_extract()` | Retry na timeout (2 pokusy) |
| `voice_watchdog()` | Zvýšená frekvence (30s), delší throttle (90s) |
| `FFmpeg options` | `-rw_timeout 5000000`, vyšší bitrate buffer |

---

## Pokud cokoliv selhalo

Logs jsou tvůj nejlepší přítel:
```bash
# V terminálu:
tail -f bot.log  # pokud máš logging nastavený

# Nebo v systemd:
journalctl -u discordbot -e
```

Pokud vidíš error, zkontroluj **README.md** sekci **🩺 Diagnostika**.

---

**Vše hotovo! Bot by teď měl být 100% stabilní. ✝️**
