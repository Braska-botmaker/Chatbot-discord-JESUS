#!/bin/bash
# Ježíš Discord Bot – Instalace na Linux/macOS
# Spuštění: bash install-desktop.sh
#
# Tento skript nainstaluje všechno co je potřeba:
#   ✅ Python virtuální prostředí (.venv)
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
    warn "FFmpeg není nainstalován (volitelný, ale bez něj nehraje hudba)"
    warn "Na Linuxu: sudo apt install ffmpeg"
    warn "Na macOS: brew install ffmpeg"
fi

# 3. Zkontroluj JS runtime pro yt-dlp (v2.8.3, volitelné ale doporučené)
echo ""
echo "3️⃣  Zkontroluj JS runtime (node/deno) pro yt-dlp..."
if command -v node &> /dev/null; then
    info "Node.js: $(node --version)"
elif command -v deno &> /dev/null; then
    info "Deno: $(deno --version 2>/dev/null | head -1)"
else
    warn "Node ani Deno nenalezeny – YouTube extrakce může selhat na 'Sign in to confirm you're not a bot'."
    warn "Na Linuxu: sudo apt install nodejs   |   Na macOS: brew install node"
fi

# 4. Vytvoř venv
echo ""
echo "4️⃣  Vytváření virtuálního prostředí (.venv)..."
if [ -d ".venv" ]; then
    info ".venv již existuje"
else
    python3 -m venv .venv || error "venv vytvoření selhalo"
    info ".venv vytvořen"
fi

# 5. Aktivuj venv
echo ""
echo "5️⃣  Aktivace .venv..."
source .venv/bin/activate || error "venv aktivace selhala"
info ".venv aktivován"

# 6. Instaluj balíčky
echo ""
echo "6️⃣  Instalace Python balíčků..."
warn "Toto může trvat 1-3 minuty..."
pip install --upgrade pip > /dev/null 2>&1
if [ -f "config/requirements.txt" ]; then
    pip install -r config/requirements.txt > /dev/null 2>&1 || error "Instalace balíčků selhala"
    info "Balíčky nainstalováy"
else
    error "config/requirements.txt nenalezen!"
fi

# 7. Vytvoř .env
echo ""
echo "7️⃣  Konfigurace .env..."
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

# 8. Zkontroluj .env
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

# 9. Testuj bota
echo ""
echo "9️⃣  Test bota..."
if command -v timeout &> /dev/null; then
    TIMEOUT_BIN=timeout
elif command -v gtimeout &> /dev/null; then
    TIMEOUT_BIN=gtimeout    # macOS s coreutils (brew install coreutils)
else
    TIMEOUT_BIN=""
fi

if [ -n "$TIMEOUT_BIN" ]; then
    warn "Spouštím bota na 10 sekund..."
    "$TIMEOUT_BIN" 10 python3 bot.py > /tmp/bot_test.log 2>&1 || true
    if grep -q "Bot je přihlášen jako" /tmp/bot_test.log; then
        info "Bot se úspěšně přihlásil! ✅"
    elif grep -q "ModuleNotFoundError\|ImportError" /tmp/bot_test.log; then
        error "Chybí Python modul! Zkontroluj: cat /tmp/bot_test.log"
    else
        warn "Test timeout (je OK, bot se připravuje)"
    fi
else
    warn "'timeout' není k dispozici – přeskakuji auto-test. Ověř ručně: python3 bot.py"
fi

# HOTOVO!
echo ""
echo "=========================================="
echo "🎉 INSTALACE DOKONČENA! 🎉"
echo "=========================================="
echo ""
echo "🚀 Spuštění bota:"
echo ""
echo "  source .venv/bin/activate"
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
