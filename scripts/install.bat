@echo off
REM Ježíš Discord Bot – Instalace na Windows
REM Spuštění: install.bat
REM
REM Tento skript nainstaluje všechno co je potřeba:
REM   ✅ Python virtuální prostředí (.venv)
REM   ✅ Python závislosti
REM   ✅ Discord bot nastavení

chcp 65001 >nul
setlocal enabledelayedexpansion
cls

echo ==========================================
echo.
echo  🙏 Ježíš Discord Bot – Instalace (Windows)
echo.
echo ==========================================
echo.

REM 1. Zkontroluj Python
echo 1️⃣  Zkontroluj Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ Python není nainstalován!
    echo.
    echo Stáhni si Python z: https://www.python.org/downloads/
    echo Při instalaci ZAŠKRTNI: "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo ✅ Python: %PYTHON_VER%
echo.

REM 2. Zkontroluj FFmpeg
echo 2️⃣  Zkontroluj FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  FFmpeg není nainstalován ^(nepovinný, ale bez něj nehraje hudba^)
    echo.
    echo Stáhni si: https://www.gyan.dev/ffmpeg/builds/
    echo Přidej ffmpeg.exe do PATH nebo do složky bota.
    echo.
    set /p continue="Pokračovat bez FFmpeg? (y/n): "
    if /i not "!continue!"=="y" exit /b 1
) else (
    for /f "tokens=3" %%i in ('ffmpeg -version 2^>^&1 ^| findstr /R "^ffmpeg version"') do set FFMPEG_VER=%%i
    echo ✅ FFmpeg: !FFMPEG_VER!
)
echo.

REM 3. Zkontroluj JS runtime (node/deno) pro yt-dlp – v2.8.3
echo 3️⃣  Zkontroluj Node.js ^(pro yt-dlp JS challenge^)...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Node.js nenalezen – YouTube extrakce může selhat na "Sign in to confirm you're not a bot".
    echo    Nainstaluj: https://nodejs.org  nebo  winget install OpenJS.NodeJS.LTS
) else (
    for /f %%i in ('node --version 2^>^&1') do echo ✅ Node.js: %%i
)
echo.

REM 4. Vytvoř venv
echo 4️⃣  Vytváření virtuálního prostředí (.venv)...
if exist .venv (
    echo ℹ️  .venv již existuje
) else (
    echo Čekám na vytvoření (může trvat 30 sekund)...
    python -m venv .venv >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ❌ venv vytvoření selhalo!
        pause
        exit /b 1
    )
    echo ✅ .venv vytvořen
)
echo.

REM 5. Aktivuj venv
echo 5️⃣  Aktivace .venv...
call .venv\Scripts\activate.bat >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ venv aktivace selhala!
    pause
    exit /b 1
)
echo ✅ .venv aktivován
echo.

REM 6. Instaluj balíčky
echo 6️⃣  Instalace Python balíčků...
echo ⏳ Čekám (může trvat 2-5 minut)...
pip install --upgrade pip >nul 2>&1
if exist config\requirements.txt (
    pip install -r config\requirements.txt >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ❌ Instalace balíčků selhala!
        echo Spusť: pip install -r config/requirements.txt
        pause
        exit /b 1
    )
    echo ✅ Balíčky nainstalováy
) else (
    echo ❌ config\requirements.txt nenalezen!
    pause
    exit /b 1
)
echo.

REM 7. Vytvoř .env
echo 7️⃣  Konfigurace .env...
if exist .env (
    echo ℹ️  .env již existuje
) else (
    if exist config\.env.example (
        copy /y config\.env.example .env >nul
        echo ✅ .env vytvořen
    ) else (
        echo ❌ config\.env.example nenalezen!
        pause
        exit /b 1
    )
)
echo.

REM 8. Zkontroluj .env
findstr /R "your_bot_token_here" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ❌ POZOR: Musíš vyplnit DISCORD_TOKEN v .env!
    echo.
    echo Otevři: .env
    echo Změň:
    echo   DISCORD_TOKEN=your_bot_token_here_not_example
    echo na tvůj skutečný token
    echo.
    echo Token najdeš na: https://discord.com/developers/applications
    echo.
    pause
    exit /b 1
)
echo ✅ .env je vyplněn
echo.

REM 9. Test závislostí (bez spouštění celého bota – to na Windows spolehlivě nezabijeme)
echo 8️⃣  Kontrola importů...
python -c "import discord, yt_dlp, dotenv, requests, pytz; print('deps OK')"
if %errorlevel% neq 0 (
    echo ❌ Nějaká závislost chybí – zkontroluj výstup výše.
    pause
    exit /b 1
)
python -c "import ast; ast.parse(open('bot.py', encoding='utf-8').read()); print('bot.py syntax OK')"
if %errorlevel% neq 0 (
    echo ❌ bot.py má syntaktickou chybu.
    pause
    exit /b 1
)
echo ✅ Test dokončen
echo.

REM HOTOVO!
echo.
echo ==========================================
echo 🎉 INSTALACE DOKONČENA! 🎉
echo ==========================================
echo.
echo 🚀 Spuštění bota:
echo.
echo   .venv\Scripts\activate
echo   python bot.py
echo.
echo 📝 Testuj v Discordu:
echo   /commands      # Seznam příkazů
echo   /diag          # Diagnostika
echo   /verse         # Náhodný verš
echo.
echo 📚 Dokumentace:
echo   docs\INSTALL.md         – Instalace a nastavení
echo   docs\TROUBLESHOOTING.md – Řešení problémů
echo.
echo 🥧 Raspberry Pi?
echo   Spusť na RPi: bash install.sh
echo.
echo Přáti vítězství! ✝️
echo.
pause
