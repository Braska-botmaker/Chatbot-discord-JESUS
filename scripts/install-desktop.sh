#!/bin/bash
# Ježíš Discord Bot – Instalace na Linux/macOS
# Spuštění: bash install-desktop.sh
#
# Tento skript nainstaluje všechno co je potřeba:
#   ✅ Python virtuální prostředí
#   ✅ Python závislosti
#   ✅ Bot nastavení

set -e

# Barvy
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

echo "=========================================="
echo "🙏 Ježíš Discord Bot – Instalace (Linux/macOS)"
echo "=========================================="
echo ""

# 1. Zkontroluj Python
echo "1️⃣  Zkontroluj Python..."
if ! command -v python3 &> /dev/null; then
    error "Python3 není nainstalován!"
fi
PYTHON_VER=$(python3 --version | awk '{print $2}')
info "Python: $PYTHON_VER"

# 2. Zkontroluj FFmpeg (nepovinné)
echo ""
echo "2️⃣  Zkontroluj FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VER=$(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')
    info "FFmpeg: $FFMPEG_VER"
else
    warn "FFmpeg není nainstalován (volitelný)"
    warn "Na Linuxu: sudo apt install ffmpeg"
    warn "Na macOS: brew install ffmpeg"
fi

# 3. Vytvoř venv
echo ""
echo "3️⃣  Vytváření virtuálního prostředí..."
if [ -d "venv" ]; then
    info "venv již existuje"
else
    python3 -m venv venv || error "venv vytvoření selhalo"
    info "venv vytvořen"
fi

# 4. Aktivuj venv
echo ""
echo "4️⃣  Aktivace venv..."
source venv/bin/activate || error "venv aktivace selhala"
info "venv aktivován"

# 5. Instaluj balíčky
echo ""
echo "5️⃣  Instalace Python balíčků..."
warn "Toto může trvat 1-3 minuty..."
pip install --upgrade pip > /dev/null 2>&1
if [ -f "config/requirements.txt" ]; then
    pip install -r config/requirements.txt > /dev/null 2>&1 || error "Instalace balíčků selhala"
    info "Balíčky nainstalováy"
else
    error "config/requirements.txt nenalezen!"
fi

# 6. Vytvoř .env
echo ""
echo "6️⃣  Konfigurace .env..."
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

# 7. Zkontroluj .env
if grep -q "your_bot_token_here" .env; then
    error ""
    error "❌ POZOR: Musíš vyplnit DISCORD_TOKEN v .env!"
    error ""
    error "Spusť:"
    error "  nano .env"
    error ""
    error "A změň:"
    error "  DISCORD_TOKEN=your_bot_token_here_not_example"
    error "na:"
    error "  DISCORD_TOKEN=tvuj_skutecny_token"
    error ""
fi
info ".env je vyplněn"

# 8. Testuj bota
echo ""
echo "7️⃣  Test bota..."
warn "Spouštím bota na 10 sekund..."
timeout 10 python3 bot.py > /tmp/bot_test.log 2>&1 || true

if grep -q "Bot je přihlášen jako" /tmp/bot_test.log; then
    info "Bot se úspěšně přihlásil! ✅"
else
    warn "Kontrola logu..."
    if grep -q "ModuleNotFoundError\|ImportError" /tmp/bot_test.log; then
        error "Chybí Python modul! Zkontroluj: cat /tmp/bot_test.log"
    else
        warn "Test timeout (je OK, bot se připravuje)"
    fi
fi

# HOTOVO!
echo ""
echo "=========================================="
echo "🎉 INSTALACE DOKONČENA! 🎉"
echo "=========================================="
echo ""
echo "🚀 Spuštění bota:"
echo ""
echo "  source venv/bin/activate"
echo "  python3 bot.py"
echo ""
echo "📝 Testuj v Discordu:"
echo "  /commands      # Seznam příkazů"
echo "  /diag          # Diagnostika"
echo "  /verse         # Náhodný verš"
echo ""
echo "📚 Dokumentace:"
echo "  docs/INSTALL.md         – Instalace a nastavení"
echo "  docs/TROUBLESHOOTING.md – Řešení problémů"
echo ""
echo "🥧 Raspberry Pi?"
echo "  Spusť: bash install.sh"
echo ""
echo "Přáti vítězství! ✝️"
echo ""
