# 🩺 Řešení problémů

Než cokoliv jiného, spusť v Discordu **`/diag`** – ukáže stav FFmpeg/Opus/PyNaCl, počet
připojení do voice a živý test yt-dlp (přesně tam, kde se nejčastěji něco rozbije).

Pak najdi svůj problém níže.

---

## 🎥 YouTube nehraje / žádný zvuk

**Nejčastější příčina zdaleka: zastaralá verze `yt-dlp`.** YouTube si s ochranami proti
botům pravidelně (klidně i každý měsíc) zahrává, takže i pár týdnů starý `yt-dlp` může
najednou přestat fungovat – ať už chybovou hláškou, nebo (hůř) tichým "přehráváním" beze
zvuku.

```bash
cd /opt/discordbot   # nebo kam máš bota
source .venv/bin/activate
pip install -U yt-dlp
sudo systemctl restart discordbot
```

Pak zkontroluj přes `/diag` (má vestavěný živý test) nebo ručně:

```
/yt https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### „Sign in to confirm you're not a bot" / HTTP 403 / video se "přehraje" 0 sekund

- Ujisti se, že `yt-dlp` je aktuální (viz výše) – tohle samo řeší většinu případů.
- **Chybí JavaScript runtime (v2.8.3).** YouTube od ~2026.08 vyžaduje k extrakci JS engine.
  Zkontroluj `/diag` řádek **„JS runtime"** – pokud je `❌ chybí`, nainstaluj Node.js
  (`sudo apt-get install -y nodejs`, dá `/usr/bin/node` i pro ARM) a restartuj službu.
  V logu při startu pak musí být `[yt-dlp] JS runtime: node (/usr/bin/node)`. Když `node`
  existuje, ale bot ho nevidí, běží nejspíš pod systemd s ořezaným `PATH` – přidej do
  unit souboru `Environment="PATH=/opt/discordbot/.venv/bin:/usr/local/bin:/usr/bin:/bin"`,
  nebo nastav `YTDLP_JS_RUNTIME=/usr/bin/node` v `.env`.
- `YTDLP_PLAYER_CLIENTS` v `.env` nech **prázdné** – od v2.8.2 si `yt-dlp` vybírá klienta
  sám a je to spolehlivější, než cokoliv vynucovat. Vyplň ho jen dočasně jako pokus, pokud
  se problém opakuje i s aktuálním `yt-dlp` (viz [CHANGELOG](CHANGELOG.md) v2.8.1/v2.8.2,
  kde je popsáno, proč vynucená kombinace klientů dřív nebo později přestane fungovat).
- Pro věkově omezená videa nastav `YTDLP_COOKIES_FILE` na `cookies.txt` vyexportovaný
  z prohlížeče přihlášeného na YouTube (např. rozšířením "Get cookies.txt").
- Zkontroluj logy: `journalctl -u discordbot -f | grep -i "yt-dlp\|youtube"`

### Soukromé video / video není dostupné

Video je soukromé, smazané nebo geo-blokované – zkus jiné. Tohle bot ovlivnit nemůže.

---

## 🎙️ Voice se nepřipojí

### WebSocket closed with 4017

**Příčina:** Discord od poloviny 2026 vyžaduje pro voice spojení protokol DAVE
(End-to-End Encrypted Voice). Starší `discord.py` ho neumí a spojení padá s
nedokumentovaným kódem 4017 – ještě předtím, než se vůbec dostane k YouTube.

**Řešení:**

```bash
source .venv/bin/activate
pip install -U "discord.py[voice]"
sudo systemctl restart discordbot
```

`[voice]` extra doinstaluje povinnou závislost `davey` a srovná `PyNaCl` na kompatibilní
verzi. Wheely jsou prebuilt i pro ARM (Raspberry Pi) – není potřeba nic kompilovat.

### WebSocket closed with 4006 / „Timeout na ch.connect"

**Příčina:** Problém s UDP handshake (typicky na ARM/Raspberry Pi).

1. Zkontroluj, že jsi **ve stejném voice kanálu**, kam má bot přijít
2. Ověř oprávnění kanálu: **Connect** a **Speak**
3. Zkus jiný voice kanál
4. Restartuj bota: `sudo systemctl restart discordbot`
5. Zkontroluj UDP buffery (RPi):
   ```bash
   cat /proc/sys/net/core/rmem_default   # mělo by být ≥ 212992
   ```
   Pokud je nižší:
   ```bash
   echo "net.core.rmem_default=1048576" | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```
6. Bot má vestavěný retry pro 4006 na ARM systémech – v logu uvidíš `[RPi patch] 4006 in connect(), retrying`. Pokud přetrvává i po 5 pokusech, jde o síť/UDP, ne o bota.

### `/voicetest` selže

- Musíš být sám ve voice kanálu, než spustíš `/voicetest`.
- Ověř práva **Connect** + **Speak**.
- Zkontroluj, že je FFmpeg nainstalovaný: `which ffmpeg`
- Funkční test = bot 3 sekundy zahraje slyšitelný tón 440Hz. Pokud je ticho, nejde o
  Discord problém, ale o FFmpeg/Opus na tvém systému – pokračuj níže.

### „Nelze se připojit: chybí PyNaCl" / „nenačtená knihovna Opus"

```bash
# PyNaCl
pip install -U PyNaCl

# Opus (Linux/RPi)
sudo apt install -y libopus0

# Ověření
python3 -c "import discord.opus; print(discord.opus.is_loaded())"   # má vrátit True
```

Na Windows stáhni Opus z [xiph/opus releases](https://github.com/xiph/opus/releases).

---

## 🚀 Bot se nespustí

| Chyba | Příčina a řešení |
|---|---|
| `ModuleNotFoundError: No module named 'discord'` | Závislosti nejsou nainstalované: `pip install -r config/requirements.txt` |
| Bot spadne hned po startu, chybí token | `.env` neexistuje nebo nemá `DISCORD_TOKEN=...` – zkontroluj `cat .env` |
| `PrivilegedIntentsRequired` | V Developer Portalu → Bot nejsou zapnuté **Presence**, **Server Members** a **Message Content** Intents |
| Bot se přihlásí, ale nic nedělá | Stejné jako výše – zkontroluj Intents, pak restartuj |
| Systemd služba se nespustí | `sudo journalctl -u discordbot -n 50 --no-pager` a `sudo systemd-analyze verify /etc/systemd/system/discordbot.service` |

Reset Discord tokenu: Developer Portal → tvá aplikace → **Bot** → **Reset Token** → vlož nový do `.env` → restart.

---

## 🥧 Raspberry Pi – výkon

```bash
vcgencmd measure_temp     # mělo by být < 60 °C
free -h                   # mělo by zbývat > 500 MB volné paměti
sudo systemctl is-enabled discordbot   # mělo by vrátit "enabled" (autostart po rebootu)
```

Pokud bot dlouhodobě žere 50–100 % CPU, restartuj (`sudo systemctl restart discordbot`) a
pokud se to opakuje, nahlaš to jako bug.

---

## 📝 Logy

```bash
journalctl -u discordbot -f                          # živě
journalctl -u discordbot -n 50 --no-pager             # posledních 50 řádků
journalctl -u discordbot --priority=3                 # jen chyby
journalctl -u discordbot -f | grep -iE "error|4006|4017|timeout|yt-dlp"
```

| Hláška v logu | Co znamená |
|---|---|
| `Bot je přihlášen jako ...` | ✅ Bot je online |
| `[yt-dlp] JS runtime: node (/usr/bin/node)` | ✅ JS runtime nalezen (v2.8.3) |
| `[yt-dlp] ⚠️ Žádný JS runtime ... nenalezen` | ❌ Doinstaluj `nodejs`, jinak YouTube neteče |
| `[RPi patch] Platform detection: ... is_arm=True` | ✅ ARM patch aktivní (Raspberry Pi) |
| `[RPi patch] 4006 in connect(), retrying` | Automatický retry na chybu 4006 |
| `[music] Extracting: ...` | Bot začal extrahovat skladbu přes yt-dlp |
| `[yt-dlp extract attempt ...]` | yt-dlp extrakce selhala a zkouší to znovu |
| `[FFmpeg error]` | FFmpeg proces skončil s chybou |

---

## ✅ Rychlá kontrola, že je vše v pořádku

```bash
sudo systemctl status discordbot --no-pager
```

V Discordu:

```
/diag       # kompletní diagnostika vč. yt-dlp self-testu
/voicetest  # 3s tón – ověří voice+FFmpeg
/yt https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Všechno zelené? Bot je v pořádku. 🎉 Jinak viz [docs/INSTALL.md](INSTALL.md) nebo
[docs/CHANGELOG.md](CHANGELOG.md) pro známé problémy konkrétních verzí.
