@echo off
REM Ježíš Discord Bot – Instalace na Windows
REM Spuštění: install.bat
REM
REM Tento skript nainstaluje všechno co je potřeba:
REM   ✅ Python virtuální prostředí
REM   ✅ Python závislosti
REM   ✅ Discord bot nastavení

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
    echo ⚠️  FFmpeg není nainstalován (NePovinný na Windowsu)
    echo Bez FFmpeg nebudou fungovat voice/hudba!
    echo.
    echo Stáhni si: https://ffmpeg.org/download.html
    echo Přidej ffmpeg.exe do PATH nebo do složky bota.
    echo.
    set /p continue="Pokračovat bez FFmpeg? (y/n): "
    if /i not "!continue!"=="y" exit /b 1
) else (
    ffmpeg -version 2>&1 | findstr /R "version [0-9]" >nul
    for /f "tokens=2" %%i in ('ffmpeg -version 2^>^&1 ^| findstr /R "version"') do set FFMPEG_VER=%%i
    echo ✅ FFmpeg: !FFMPEG_VER!
)
echo.

REM 3. Vytvoř venv
echo 3️⃣  Vytváření virtuálního prostředí...
if exist venv (
    echo ℹ️  venv již existuje
) else (
    echo Čekám na vytvoření (může trvat 30 sekund)...
    python -m venv venv >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ❌ venv vytvoření selhalo!
        pause
        exit /b 1
    )
    echo ✅ venv vytvořen
)
echo.

REM 4. Aktivuj venv
echo 4️⃣  Aktivace venv...
call venv\Scripts\activate.bat >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ venv aktivace selhala!
    pause
    exit /b 1
)
echo ✅ venv aktivován
echo.

REM 5. Instaluj balíčky
echo 5️⃣  Instalace Python balíčků...
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

REM 6. Vytvoř .env
echo 6️⃣  Konfigurace .env...
if exist .env (
    echo ℹ️  .env již existuje
) else (
    if exist config\.env.example (
        type config\.env.example > .env
        echo ✅ .env vytvořen
    ) else (
        echo ❌ config\.env.example nenalezen!
        pause
        exit /b 1
    )
)
echo.

REM 7. Zkontroluj .env
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

REM 8. Testuj bota
echo 7️⃣  Test bota...
echo ⏳ Spouštím bota na 10 sekund...
timeout /t 2 /nobreak >nul
python bot.py >nul 2>&1 &
set BOT_PID=!ERRORLEVEL!
timeout /t 10 /nobreak >nul
taskkill /PID !BOT_PID! /F >nul 2>&1
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
echo   Způsob 1 (teď):
echo     python bot.py
echo.
echo   Způsob 2 (okno):
echo     Dvakrát klikni na: run.bat (pokud existuje)
echo.
echo 📝 Testuj v Discordu:
echo   !commands      # Seznam příkazů
echo   !diag          # Diagnostika
echo   !verš          # Náhodný verš
echo.
echo 📚 Dokumentace:
echo   docs\INSTALACE.md  – Podrobný guide
echo   docs\CHYBY.md      – Troubleshooting
echo   docs\RYCHLY_START.md – Rychlý start
echo.
echo 🥧 Raspberry Pi?
echo   Spusť na RPi: bash install.sh
echo.
echo Přáti vítězství! ✝️
echo.
pause
