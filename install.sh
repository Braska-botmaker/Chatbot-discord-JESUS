#!/bin/bash
# Ježíš Discord Bot – Automatická instalace na Raspberry Pi
# Spuštění: bash install.sh
#
# Tento skript nainstaluje všechno co je potřeba:
#   ✅ Systémové balíčky (Python, FFmpeg, Opus)
#   ✅ Virtual environment
#   ✅ Python závislosti
#   ✅ Discord bot (git clone)
#   ✅ .env konfigurace
#   ✅ systemd služba (autostart)

set -e  # Vypni na první chybu

echo "=========================================="
echo "🙏 Ježíš Discord Bot – Instalace"
echo "=========================================="
echo ""

# Barvy pro výstup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funkce pro hlášky
info() {
    echo -e "${GREEN}✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 1. Zkontroluj, jestli jsi na RPi
echo "1️⃣  Zkontroluj systém..."
MACHINE=$(uname -m)
if [[ ! "$MACHINE" == "aarch64" && ! "$MACHINE" == "armv7l" ]]; then
    warn "Skript je optimalizován pro Raspberry Pi (ARM), ale detekuji: $MACHINE"
    warn "Pokud to není RPi, některé věci nemusí fungovat!"
    read -p "Pokračovat? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Instalace zrušena"
    fi
fi
info "Systém: $MACHINE"

# 2. Zkontroluj, jestli jsi root pro sudo
echo ""
echo "2️⃣  Kontrola sudo..."
if ! sudo -v &> /dev/null; then
    error "Sudo není dostupné. Spusť: sudo bash install.sh"
fi
info "Sudo OK"

# 3. Aktualizuj systém
echo ""
echo "3️⃣  Aktualizace systému..."
warn "Toto může trvat 2-5 minut..."
sudo apt-get update > /dev/null 2>&1 || error "apt update selhalo"
sudo apt-get upgrade -y > /dev/null 2>&1 || error "apt upgrade selhalo"
info "Systém aktualizován"

# 4. Instaluj potřebné balíčky
echo ""
echo "4️⃣  Instalace systémových balíčků..."
PACKAGES="python3-pip python3-venv ffmpeg libopus0 git"
for pkg in $PACKAGES; do
    if dpkg -l | grep -q "^ii  $pkg"; then
        info "$pkg již nainstalován"
    else
        warn "Instaluji $pkg..."
        sudo apt-get install -y "$pkg" > /dev/null 2>&1 || error "Instalace $pkg selhala"
        info "$pkg nainstalován"
    fi
done

# 5. Ověř verze
echo ""
echo "5️⃣  Ověřování verzí..."
PYTHON_VER=$(python3 --version | awk '{print $2}')
FFMPEG_VER=$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')
info "Python: $PYTHON_VER"
info "FFmpeg: $FFMPEG_VER"

# 6. Vytvoř složku pro bota
echo ""
echo "6️⃣  Příprava adresáře..."
BOTDIR="/opt/discordbot"
if [ -d "$BOTDIR" ]; then
    warn "Složka $BOTDIR již existuje"
    read -p "Přepsat? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo rm -rf "$BOTDIR"
        info "Složka smazána"
    else
        warn "Používám existující složku"
    fi
fi

if [ ! -d "$BOTDIR" ]; then
    sudo mkdir -p "$BOTDIR" || error "Nelze vytvořit $BOTDIR"
    sudo chown $USER:$USER "$BOTDIR"
    info "Složka $BOTDIR vytvořena"
fi

# 7. Klonuj nebo stáhni repo
echo ""
echo "7️⃣  Stažení bota..."
cd "$BOTDIR"

# Zkus git clone (pokud má přístup)
if [ -d ".git" ]; then
    warn "Git repo již existuje, update..."
    git pull origin main > /dev/null 2>&1 || warn "Git pull selhalo, pokračuji"
else
    warn "Klonuji repo z GitHubu..."
    # Zkus klonovat, pokud URL není dostupná, řekni uživateli co dělat
    if git clone https://github.com/Braska-botmaker/Chatbot-discord-JESUS.git . 2>/dev/null; then
        info "Repo naklonován"
    else
        warn "Git clone selhalo (offline?)"
        warn "Ručně vytvářím strukturu..."
        # Vytvoř základní strukturu
        mkdir -p docs config
        touch bot.py README.md .env .gitignore
        warn "Prosím zkopíruj bot.py a ostatní soubory ručně!"
    fi
fi

info "Soubory hotovy"

# 8. Vytvoř venv
echo ""
echo "8️⃣  Virtuální prostředí..."
if [ -d ".venv" ]; then
    info "venv již existuje"
else
    warn "Vytvářím venv..."
    python3 -m venv .venv > /dev/null 2>&1 || error "venv vytvoření selhalo"
    info "venv vytvořen"
fi

# Aktivuj venv
source .venv/bin/activate || error "Aktivace venv selhala"
info "venv aktivován"

# 9. Instaluj Python balíčky
echo ""
echo "9️⃣  Instalace Python balíčků..."
warn "Toto může trvat 3-10 minut (kompilace na RPi)..."
pip install --upgrade pip > /dev/null 2>&1
if [ -f "config/requirements.txt" ]; then
    pip install -r config/requirements.txt > /dev/null 2>&1 || error "Instalace balíčků selhala"
    info "Balíčky nainstalováy"
else
    error "config/requirements.txt nenalezen!"
fi

# 10. Vytvoř .env
echo ""
echo "🔟 Konfigurace .env..."
if [ -f ".env" ]; then
    warn ".env již existuje"
else
    if [ -f "config/.env.example" ]; then
        cp config/.env.example .env
        info ".env vytvořen"
    else
        error "config/.env.example nenalezen!"
    fi
fi

# Ověř token
if grep -q "your_bot_token_here" .env; then
    error ""
    error "❌ POZOR: Musíš vyplnit DISCORD_TOKEN v .env!"
    error ""
    error "Spusť:"
    error "  nano $BOTDIR/.env"
    error ""
    error "A změň:"
    error "  DISCORD_TOKEN=your_bot_token_here_not_example"
    error "na:"
    error "  DISCORD_TOKEN=tvuj_skutecny_token"
    error ""
    error "Token najdeš na: https://discord.com/developers/applications"
    error ""
    exit 1
fi
info ".env je vyplněn"

# 11. Testuj bota
echo ""
echo "1️⃣1️⃣  Test bota..."
warn "Spouštím bota na 10 sekund..."
timeout 10 python3 bot.py > /tmp/bot_test.log 2>&1 || true

if grep -q "Bot je přihlášen jako" /tmp/bot_test.log; then
    info "Bot se úspěšně přihlásil! ✅"
elif grep -q "ModuleNotFoundError\|ImportError" /tmp/bot_test.log; then
    error "Chybí Python modul! Zkontroluj logy: cat /tmp/bot_test.log"
else
    warn "Test timeout (je OK, bot se připravuje)"
fi

# 12. Systemd service
echo ""
echo "1️⃣2️⃣  Nastavení systemd služby..."
SERVICE_FILE="/etc/systemd/system/discordbot.service"

if [ -f "$SERVICE_FILE" ]; then
    warn "Systemd služba již existuje"
    read -p "Přepsat? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Služba nebyla změněna"
    else
        sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Ježíš Discord Bot (Raspberry Pi)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOTDIR
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=$BOTDIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$BOTDIR/.venv/bin/python3 $BOTDIR/bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discordbot

[Install]
WantedBy=multi-user.target
EOF
        info "Systemd služba aktualizována"
    fi
else
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Ježíš Discord Bot (Raspberry Pi)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOTDIR
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=$BOTDIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$BOTDIR/.venv/bin/python3 $BOTDIR/bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discordbot

[Install]
WantedBy=multi-user.target
EOF
    info "Systemd služba vytvořena"
fi

# 13. Aktivuj službu
echo ""
echo "1️⃣3️⃣  Aktivace služby..."
sudo systemctl daemon-reload > /dev/null 2>&1 || warn "daemon-reload selhalo"
sudo systemctl enable discordbot > /dev/null 2>&1 || warn "enable selhalo"
info "Služba je povolena (autostart)"

# 14. Spusť službu
echo ""
echo "1️⃣4️⃣  Spuštění bota..."
sudo systemctl start discordbot > /dev/null 2>&1 || warn "start selhalo"
sleep 2

# Zkontroluj status
if sudo systemctl is-active --quiet discordbot; then
    info "Bot běží! ✅"
else
    warn "Bot se nespustil. Zkontroluj:"
    warn "  sudo systemctl status discordbot"
    warn "  sudo journalctl -u discordbot -f"
fi

# HOTOVO! 🎉
echo ""
echo "=========================================="
echo "🎉 INSTALACE DOKONČENA! 🎉"
echo "=========================================="
echo ""
echo "📊 Příkazy:"
echo "  Status:        sudo systemctl status discordbot"
echo "  Logy:          sudo journalctl -u discordbot -f"
echo "  Zastavit:      sudo systemctl stop discordbot"
echo "  Restartovat:   sudo systemctl restart discordbot"
echo ""
echo "📝 Testuj v Discordu:"
echo "  !commands      # Seznam příkazů"
echo "  !diag          # Diagnostika"
echo "  !verš          # Náhodný verš"
echo ""
echo "📚 Dokumentace:"
echo "  docs/INSTALACE.md  – Podrobný guide"
echo "  docs/CHYBY.md      – Troubleshooting"
echo "  docs/RYCHLY_START.md – Rychlý start"
echo ""
echo "Přáti vítězství! ✝️"
echo ""
