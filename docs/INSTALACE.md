# 🥧 Instalace na Raspberry Pi – Kompletní průvodce

Tento dokument obsahuje krok-za-krokem instrukce pro spuštění Ježíšova bota na Raspberry Pi 24/7.

---

## 📋 Požadavky

- **Raspberry Pi:** 3B+ nebo novější (aarch64 ARM)
- **OS:** Raspberry Pi OS Bookworm (64-bit) - **POVINNÉ** (32-bit je eol)
- **Internetu:** Stabilní připojení (kabelované)
- **Přístupu:** SSH nebo terminál přímo na RPi

---

## 🔧 KROK 1: Příprava systému

### 1a) Aktualizuj OS
```bash
sudo apt update
sudo apt upgrade -y
```

### 1b) Instaluj potřebné balíčky
```bash
sudo apt install -y \
    python3-pip \
    python3-venv \
    ffmpeg \
    libopus0 \
    git
```

Ověř verze:
```bash
python3 --version          # Python 3.11+
ffmpeg -version | head -1  # FFmpeg 5.0+
```

---

## 📁 KROK 2: Připrav složku bota

```bash
# Vytvoř adresář pro bota
sudo mkdir -p /opt/discordbot
sudo chown $USER:$USER /opt/discordbot

# Přejdi do něj
cd /opt/discordbot

# Klonuj (nebo nakopíruj) repo
git clone https://github.com/tvuj-github/Chatbot-discord-JESUS.git .

# Nebo jen nakopíruj soubory přes SCP:
# Na počítači:
scp -r * user@raspberrypi:/opt/discordbot/
```

---

## 🐍 KROK 3: Vytvoř virtuální prostředí

```bash
cd /opt/discordbot

# Vytvoř venv
python3 -m venv .venv

# Aktivuj
source .venv/bin/activate

# Aktualizuj pip
pip install --upgrade pip

# Instaluj závislosti (config/requirements.txt)
pip install -r config/requirements.txt
```

Ověř instalaci:
```bash
python3 -c "import discord; print('discord.py OK')"
python3 -c "import nacl; print('PyNaCl OK')"
which ffmpeg
```

---

## 🔐 KROK 4: Konfigurace

### 4a) Vytvoř `.env` soubor
```bash
# Zkopíruj příklad
cp config/.env.example .env

# Otevři a vyplň token
nano .env
```

Obsah:
```env
DISCORD_TOKEN=tvuj_token_z_discord_dev_portalu
```

Ulož: `CTRL+O` → `ENTER` → `CTRL+X`

### 4b) Ověř práva
```bash
chmod 600 .env
ls -la .env  # Měl by být -rw------- (600)
```

---

## 🤖 KROK 5: Testuj bota ručně

```bash
source /opt/discordbot/.venv/bin/activate
cd /opt/discordbot
python3 bot.py
```

Měl by se přihlásit:
```
[RPi patch] Platform detection: machine=aarch64, is_arm=True ✅
[RPi patch] ✅ Applied to VoiceClient.connect() - 4006 resilience active
Bot je přihlášen jako Ježíš#4405
```

**Testuj v Discordu:**
```
!verš
!diag
!commands
```

Zastavit: `CTRL+C`

---

## ⚙️ KROK 6: Nastav systemd službu (autostart)

### 6a) Vytvoř soubor služby
```bash
sudo nano /etc/systemd/system/discordbot.service
```

Zkopíruj:
```ini
[Unit]
Description=Ježíš Discord Bot (Raspberry Pi)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/discordbot
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/opt/discordbot/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/discordbot/.venv/bin/python3 /opt/discordbot/bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discordbot

[Install]
WantedBy=multi-user.target
```

Ulož: `CTRL+O` → `ENTER` → `CTRL+X`

### 6b) Aktivuj a spusť službu
```bash
# Znovu načti systemd konfiguraci
sudo systemctl daemon-reload

# Povolí autostart
sudo systemctl enable discordbot

# Spusť službu
sudo systemctl start discordbot

# Zkontroluj stav
sudo systemctl status discordbot

# Logy (live):
sudo journalctl -u discordbot -f

# Logy (posledních 50 řádků):
sudo journalctl -u discordbot -n 50 --no-pager
```

---

## 📊 KROK 7: Monitoring a údržba

### Běžné příkazy

```bash
# Stav služby
sudo systemctl status discordbot

# Restartuj bota (např. po updatu)
sudo systemctl restart discordbot

# Zastavit
sudo systemctl stop discordbot

# Logy s grep filtrem (Error 4006?)
sudo journalctl -u discordbot -f | grep -E "(4006|voice|error)"

# Kolik paměti má bot?
ps aux | grep discordbot | grep -v grep
```

### Updatuj kód (nová verze)

```bash
cd /opt/discordbot

# Stáhni nový kód
git pull origin main

# Nebo ručně nakopíruj nový bot.py přes SCP
# Na počítači:
scp bot.py user@raspberrypi:/opt/discordbot/

# Restartuj
sudo systemctl restart discordbot

# Ověř logy
sudo journalctl -u discordbot -f
```

### Updatuj Python balíčky

```bash
cd /opt/discordbot
source .venv/bin/activate

# Aktualizuj discord.py (bezpečnější než pip install -U všechno)
pip install --upgrade discord.py

# Nebo všechno
pip install --upgrade -r config/requirements.txt

# Restartuj
sudo systemctl restart discordbot
```

---

## 🩺 KROK 8: Diagnostika problémů

### ❌ Bot se nejde spustit

```bash
# Zkontroluj Python
python3 --version

# Zkontroluj venv
source /opt/discordbot/.venv/bin/activate
pip list | grep -i discord

# Zkontroluj .env
cat /opt/discordbot/.env

# Zkontroluj práva
ls -la /opt/discordbot/
```

### ❌ Voice se nepřipojuje (Error 4006)

```bash
# Spusť diagnostiku v Discordu
!diag
!vtest

# Logy s filtrem
sudo journalctl -u discordbot -f | grep -i "4006\|voice\|timeout"

# Zkontroluj UDP buffery
cat /proc/sys/net/core/rmem_default
cat /proc/sys/net/core/wmem_default
# Měly by být 212992 nebo vyšší
```

### ❌ Bot se neautomaticky nerestartuje

```bash
# Zkontroluj, jestli je služba povolena
sudo systemctl is-enabled discordbot

# Zkontroluj logy
sudo journalctl -u discordbot -n 100 --no-pager

# Manuální restart
sudo systemctl start discordbot
```

### ❌ Jak vidím logy v reálném čase?

```bash
# Vše
sudo journalctl -u discordbot -f

# Posledních 50 řádků
sudo journalctl -u discordbot -n 50

# Filtrované (jen chyby)
sudo journalctl -u discordbot -f --priority=3
```

---

## 🚀 Optimalizace pro produkci

### CPU teplota
```bash
vcgencmd measure_temp
# Měla by být < 60°C. Pokud je vyšší, přidej aktivní chladicí prvek.
```

### Paměť
```bash
free -h
# Mělo by být > 500MB volné
```

### Disk
```bash
df -h /
# Alespoň 1GB volné místa
```

### Nastavení Swap (volitelné, pomůže při nízké paměti)
```bash
# Zkontroluj swap
free -h

# Pokud nechceš swap, deaktivuj na RPi OS:
# sudo systemctl disable dphys-swapfile
```

---

## 📝 Checklist – Bot je připravený?

- ✅ OS je aktualizovaný (`apt update`, `apt upgrade`)
- ✅ Python3, FFmpeg, libopus0 nainstalováni
- ✅ Venv v `/opt/discordbot/.venv` s `pip install -r config/requirements.txt`
- ✅ `.env` soubor s DISCORD_TOKEN (práva 600)
- ✅ Bot se ručně spustí a přihlásí (`python3 bot.py`)
- ✅ Systemd služba je nastavená (`/etc/systemd/system/discordbot.service`)
- ✅ Služba je povolena (`systemctl enable`) a běží (`systemctl start`)
- ✅ Logy jsou vidět (`journalctl -u discordbot -f`)
- ✅ Discord kanály `#požehnání🙏` a `#hry_zdarma💵` existují
- ✅ Bot má práva **Send Messages, Connect, Speak** v kanálech

---

## 🎯 Ověř funkčnost

V Discordu spusť:

```
!commands       # Seznam příkazů
!diag           # Diagnostika RPi (Python, PyNaCl, Opus, FFmpeg)
!verš           # Náhodný verš
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Pokud vše funguje → Bot je připravený! 🎉

---

## 📞 Potřebuješ pomoc?

Viz `docs/CHYBY.md` pro troubleshooting a FAQ.
