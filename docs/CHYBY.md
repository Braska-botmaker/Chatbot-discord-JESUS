# 🩺 Řešení problémů – FAQ & Troubleshooting

Najdi svůj problém a vrátí se ti řešení.

---

## 🎵 Problémy s voice/hudbou

### ❌ „Timeout na ch.connect (30s elapsed)"

**Příčina:** Bot se nemůže připojit do voice kanálu (problém s UDP handshake)

**Řešení:**
1. Zkontroluj, že jsi **ve stejném voice kanálu** jako chceš bota
2. Ověř práva kanálu:
   - Bot má **Connect** ✅
   - Bot má **Speak** ✅
3. Zkus jiný voice kanál
4. Restartuj bota: `sudo systemctl restart discordbot`
5. Běž na **RPi?** Spusť: `!diag` a podívej se na UDP buffery

**Error 4006 (Invalid Session Description)?** Viz sekce níž ↓

---

### ❌ Error 4006 – WebSocket closed with 4006

**Příčina:** discord.py se nemohou vyjednat UDP handshake s Discord servery (ARMspecific)

**To není tvůj problém!** ✅ v2.0.5e má automatickou opravu:
```
[RPi patch] ✅ Applied to VoiceClient.connect() - 4006 resilience active
```

Pokud stále vidíš Error 4006 v logech:

1. **Zkontroluj, jestli je RPi detekována:**
   ```bash
   sudo journalctl -u discordbot -n 20 | grep "Platform detection"
   ```
   Mělo by být: `machine=aarch64, is_arm=True`

2. **Pokud `is_arm=False`:**
   ```bash
   python3 -c "import platform; print(platform.machine())"
   ```
   Mělo by vrátit: `aarch64` nebo `armv7l`

3. **Zkontroluj UDP buffery:**
   ```bash
   cat /proc/sys/net/core/rmem_default
   # Mělo by být 212992 nebo vyšší
   ```
   Pokud je nižší, zvyš:
   ```bash
   echo "net.core.rmem_default=1048576" | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

4. **Logy s debug info:**
   ```bash
   sudo journalctl -u discordbot -f | grep -E "(4006|connect|retry)"
   ```

---

### ❌ „FFmpeg test selhal: Not connected to voice"

**Příčina:** `!vtest` se nemůže spustit, protože nejsi ve voice kanálu

**Řešení:**
1. Nejdřív se **připoj do voice kanálu** sám
2. Pak spusť: `!vtest`
3. Bot by měl zahrát 3sekundový tón (sine wave 440Hz)

Pokud stále selže:
- Zkontroluj, že máš práva Connect + Speak v kanálu
- Zkus jiný voice kanál
- Zkontroluj, že je FFmpeg nainstalovaný: `which ffmpeg`

---

### ❌ „Nelze se připojit: chybí PyNaCl"

**Příčina:** PyNaCl není nainstalován

**Řešení:**
```bash
cd /opt/discordbot
source .venv/bin/activate
pip install -U PyNaCl
sudo systemctl restart discordbot
```

---

### ❌ „Nelze se připojit: nenačtená knihovna Opus"

**Příčina:** Opus audio codec není v systému

**Řešení:**
```bash
# Na RPi / Linux
sudo apt install -y libopus0

# Na Windows (stáhni ze zde)
# https://github.com/xiph/opus/releases

sudo systemctl restart discordbot
```

Zkontroluj:
```bash
python3 -c "import discord.opus; print(discord.opus.is_loaded())"
# Mělo by vrátit: True
```

---

## 🎥 Problémy s YouTube

### ❌ „Nepodařilo se načíst audio. Zkontroluj odkaz nebo yt-dlp."

**Příčina:** Špatný odkaz nebo YouTube blokuje

**Řešení:**
1. Zkontroluj odkaz:
   ```
   !play https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```
   (zkus Rickroll 😄)

2. Pokud je odkaz OK, aktualizuj yt-dlp:
   ```bash
   cd /opt/discordbot
   source .venv/bin/activate
   pip install -U yt-dlp
   sudo systemctl restart discordbot
   ```

3. Zkontroluj logy:
   ```bash
   !play <url>
   sudo journalctl -u discordbot -f | grep -i "yt-dlp"
   ```

---

### ❌ „403 Forbidden" – YouTube blokuje FFmpeg

**Příčina:** YouTube vyžaduje správné HTTP headers

**Řešení:** V bot.py v2.0.5+ jsou headers již zabudované ✅. Pokud stále vidíš 403:

```bash
# Aktualizuj yt-dlp
pip install -U yt-dlp

# Zkontroluj, jestli jsou headers v kódu:
grep -n "User-Agent" /opt/discordbot/bot.py
```

---

### ❌ Soukromé video / Video není dostupné

**Příčina:** Video je soukromé, odstraněné nebo geo-blokované

**Řešení:** Zkus jiné video. Bot nemůže hrát obsah, který YouTube sám blokuje.

---

## 🔧 Problémy se spuštěním

### ❌ „ModuleNotFoundError: No module named 'discord'"

**Příčina:** discord.py není nainstalován

**Řešení:**
```bash
cd /opt/discordbot
source .venv/bin/activate
pip install -r config/requirements.txt
```

---

### ❌ Bot se nejde spustit manuálně (`python3 bot.py`)

**Příčina:** Chybí .env soubor nebo je špatný token

**Řešení:**
```bash
# Zkontroluj, že .env existuje
cat /opt/discordbot/.env

# Mělo by obsahovat (se správným tokenem):
# DISCORD_TOKEN=abcd1234...

# Zkontroluj práva
ls -la /opt/discordbot/.env
# Mělo by být -rw------- (600)

# Znovu spusť
cd /opt/discordbot
source .venv/bin/activate
python3 bot.py
```

---

### ❌ „AttributeError: 'Bot' has no attribute 'run'"

**Příčina:** Bot.py je poškozený nebo neuplný

**Řešení:**
```bash
# Zkontroluj konec souboru
tail -5 /opt/discordbot/bot.py

# Mělo by obsahovat:
# bot.run(TOKEN)

# Pokud ne, přepsat soubor (zkopíruj nový z repo)
```

---

### ❌ Systemd služba se nejde spustit

```bash
# Zkontroluj logy
sudo journalctl -u discordbot -n 50 --no-pager

# Zkontroluj konfiguraci
sudo systemctl status discordbot

# Zkontroluj syntax souboru
sudo systemd-analyze verify /etc/systemd/system/discordbot.service

# Znovu načti a spusť
sudo systemctl daemon-reload
sudo systemctl restart discordbot
```

---

## 🔐 Problémy s Discord tokenem

### ❌ Bot se neautentizuje

**Příčina:** Špatný nebo neplatný token

**Řešení:**
1. Jdi na https://discord.com/developers/applications
2. Vyber svou aplikaci
3. V sekci **Bot** klikni **Reset Token** (generuj nový!)
4. Zkopíruj nový token do `.env`
5. Restartuj: `sudo systemctl restart discordbot`

---

### ❌ Bot se přihlásí ale nic nedělá

**Příčina:** Chybí oprávnění nebo intents

**Řešení:**
1. Na Developer Portalu v sekci **Bot**:
   - Zapni **Presence Intent** ✅
   - Zapni **Server Members Intent** ✅
   - Zapni **Message Content Intent** ✅

2. Znovu si vygeneruj OAuth2 URL a pozvi bota

3. Restartuj: `sudo systemctl restart discordbot`

---

## 📊 RPi specifické problémy

### ❌ CPU nebo teplota je vysoká

```bash
# Zkontroluj teplotu
vcgencmd measure_temp
# Měla by být < 60°C

# Zkontroluj CPU
top -b -n 1 | head -10

# Pokud je bot na 50-100% CPU → je bug, kontaktuj support
```

**Řešení:**
- Přidej aktivní chladicí prvek (ventilátor)
- Zkontroluj, že nejsou jiné procesy parazitující CPU
- Restartuj bot: `sudo systemctl restart discordbot`

---

### ❌ Paměť je plná

```bash
free -h
# Mělo by být > 500MB volné
```

**Řešení:**
- Vyčisti cache: `sudo apt clean`
- Zkontroluj, co žere RAM: `ps aux --sort=-%mem | head`
- Restartuj RPi: `sudo reboot`

---

### ❌ Bot se po restartu RPi neautomaticky nespustí

**Řešení:**
```bash
# Zkontroluj, je-li služba povolena
sudo systemctl is-enabled discordbot
# Mělo by vrátit: enabled

# Pokud ne, aktivuj:
sudo systemctl enable discordbot

# Restartuj RPi a zkontroluj
sudo reboot
sleep 10
sudo systemctl status discordbot
```

---

## 📝 Logy a debugging

### Jak vidím co bot dělá?

```bash
# Realtime logy
sudo journalctl -u discordbot -f

# Posledních N řádků
sudo journalctl -u discordbot -n 50

# Jen chyby
sudo journalctl -u discordbot --priority=3

# Filtrované (grep)
sudo journalctl -u discordbot -f | grep -i "error\|4006\|timeout"

# Od určitého času
sudo journalctl -u discordbot --since "2 hours ago"

# Uložit do souboru
sudo journalctl -u discordbot > /tmp/discordbot_logs.txt
```

---

### Co znamenají jednotlivé hlášky?

| Log | Pochopení |
|-----|-----------|
| `[RPi patch] Platform detection: machine=aarch64, is_arm=True` | ✅ RPi detekována, ARM patch je aktivní |
| `[RPi patch] ✅ Applied to VoiceClient.connect()` | ✅ Voice retry logika je aktivní |
| `Bot je přihlášen jako ...` | ✅ Bot je online |
| `[voice] Attempting ch.connect()` | Bot se připojuje do voice |
| `[voice] Timeout on ch.connect` | Problém s UDP handshake → retry |
| `[RPi patch] 4006 in connect(), retrying` | Error 4006 detekován → automatický retry |
| `[FFmpeg error]` | FFmpeg proces skončil s chybou |

---

## ✅ Všechno je OK, ale chci ověřit

```bash
# 1. Zkontroluj systemd status
sudo systemctl status discordbot --no-pager

# 2. Spusť diagnostiku (v Discordu)
!diag

# 3. Zkontroluj logy (posledních 10 řádků)
sudo journalctl -u discordbot -n 10

# 4. Testuj voice
!vtest

# 5. Testuj YouTube
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ

# 6. Zkontroluj paměť a CPU
free -h
ps aux | grep discordbot
```

Vše OK? → 🎉 **Bot je optimálně nastavený!**

---

## 📞 Potřebuješ víc pomoci?

- Viz `docs/INSTALACE.md` pro krok-za-krokem setup
- Viz `README.md` pro přehled příkazů
- Zkontroluj GitHub Issues pro podobné problémy
