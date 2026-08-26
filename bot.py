# ╔════════════════════════════════════════════════════════════════════════════╗
# ║  Ježíš Discord Bot v2.8.2 – Voice & Player Client Hotfix                   ║
# ║                     Kompletní přepis na slash commands                     ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# ═══════════════════════════════════════════════════════════════════════════════
#                              1. IMPORTS & SETUP
# ═══════════════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import datetime
import os
import requests
from dotenv import load_dotenv
import pytz
import asyncio
from collections import deque
from typing import Optional
import shutil
import time
import json
import pathlib
import platform
import re
from html import unescape as html_unescape
import xml.etree.ElementTree as ET

_yt_dlp = None

# ═══════════════════════════════════════════════════════════════════════════════
#                    2. RPi VOICE FIX (Error 4006 Handling)
# ═══════════════════════════════════════════════════════════════════════════════

def _is_arm_system():
    """Detekuj ARM systémy (RPi, atd)."""
    machine = platform.machine().lower()
    arm_variants = ['arm', 'armv6', 'armv7', 'aarch64', 'armv8']
    is_arm = any(variant in machine for variant in arm_variants)
    print(f"[RPi patch] Platform detection: machine={machine}, is_arm={is_arm}")
    return is_arm

def _patch_voice_client_for_rpi():
    """Aplikuj 4006-specific retry logiku na discord.VoiceClient._inner_connect()."""
    is_rpi = _is_arm_system()
    if not is_rpi:
        print("[RPi patch] Not on ARM - skipping patches")
        return
    
    try:
        import discord.voice_client
        original_inner_connect = discord.voice_client.VoiceClient._inner_connect
        
        async def patched_inner_connect(self):
            """Retry s exponential backoff na 4006 errors."""
            max_retries = 5
            retry_delays = [0.5, 1.0, 2.0, 3.0, 5.0]
            
            for attempt in range(max_retries):
                try:
                    print(f"[RPi patch] Voice _inner_connect attempt {attempt+1}/{max_retries}")
                    return await original_inner_connect(self)
                except Exception as e:
                    error_msg = str(e)
                    is_4006 = "4006" in error_msg or "Invalid Session Description" in error_msg
                    
                    if is_4006 and attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        print(f"[RPi patch] 4006 detected, retrying in {delay}s ({attempt+1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    if is_4006:
                        print(f"[RPi patch] 4006 persisted after {max_retries} attempts")
                    raise
            return None
        
        discord.voice_client.VoiceClient._inner_connect = patched_inner_connect
        print("[RPi patch] ✅ Applied to VoiceClient._inner_connect")
    except Exception as e:
        print(f"[RPi patch] ⚠️ Failed to patch _inner_connect: {e}")

def _patch_voice_connect_for_rpi():
    """Přidej resiliensi na ch.connect() s retry pro 4006."""
    is_rpi = _is_arm_system()
    if not is_rpi:
        return
    
    try:
        import discord.voice_client
        original_connect = discord.voice_client.VoiceClient.connect
        
        async def patched_connect(self, *, timeout=60.0, reconnect=False, self_deaf=False, self_mute=False, **kwargs):
            retry_count = 0
            max_retries = 4
            extended_timeout = 30.0
            base_delay = 0.5
            actual_timeout = extended_timeout if timeout == 60.0 else timeout
            
            while retry_count < max_retries:
                try:
                    print(f"[RPi patch] VoiceClient.connect() attempt {retry_count+1}/{max_retries} (timeout={actual_timeout}s)")
                    return await original_connect(
                        self, 
                        timeout=actual_timeout, 
                        reconnect=reconnect, 
                        self_deaf=self_deaf,
                        self_mute=self_mute,
                        **kwargs
                    )
                except asyncio.TimeoutError:
                    if retry_count < max_retries - 1:
                        delay = base_delay * (1.5 ** retry_count)
                        print(f"[RPi patch] Timeout, retrying in {delay}s ({retry_count+1}/{max_retries})")
                        retry_count += 1
                        await asyncio.sleep(delay)
                        continue
                    print(f"[RPi patch] Timeout persisted after {max_retries} attempts")
                    raise
                except Exception as e:
                    error_msg = str(e)
                    is_4006 = "4006" in error_msg or "WebSocket closed with 4006" in error_msg
                    
                    if is_4006 and retry_count < max_retries - 1:
                        delay = base_delay * (1.5 ** retry_count)
                        print(f"[RPi patch] 4006 in connect(), retrying in {delay}s")
                        retry_count += 1
                        await asyncio.sleep(delay)
                        continue
                    if is_4006:
                        print(f"[RPi patch] 4006 persisted after {max_retries} attempts")
                    raise
        
        discord.voice_client.VoiceClient.connect = patched_connect
        print("[RPi patch] ✅ Applied to VoiceClient.connect()")
    except Exception as e:
        print(f"[RPi patch] ❌ Failed to patch connect(): {e}")

_patch_voice_client_for_rpi()
_patch_voice_connect_for_rpi()

# ═══════════════════════════════════════════════════════════════════════════════
#                      3. BOT INITIALIZATION & INTENTS
# ═══════════════════════════════════════════════════════════════════════════════

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
# Spotify integrace byla z v2.8.1-beta dočasně odebrána (odloženo na pozdější verzi,
# viz docs/CHANGELOG.md) – kód najdeš v historii gitu, pokud ji budeš chtít vrátit.

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ═══════════════════════════════════════════════════════════════════════════════
#                    4. DATA STORAGE & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_FILE = pathlib.Path("bot_data.json")
DATA_BACKUP_FILE = pathlib.Path("bot_data_backup.json")
_data_lock = asyncio.Lock()

# Game blessing cooldown (user_id -> {game_name -> timestamp})
_game_blessing_cooldowns = {}
GAME_BLESSING_COOLDOWN = 3600  # 1 hodina v sekundách

def _load_data():
    """Načti data s fallbackem na backup (ochrana dat)."""
    try:
        if DATA_FILE.exists():
            data_text = DATA_FILE.read_text(encoding="utf-8")
            data = json.loads(data_text)
            # Validace: ověř že existují hlavní klíče
            required_keys = ["verse_streak", "game_activity", "user_xp", "stats"]
            for key in required_keys:
                if key not in data:
                    data[key] = {}
            return data
    except json.JSONDecodeError as e:
        print(f"[DATA] ⚠️ bot_data.json je poškozený: {e}")
        # Zkus načíst backup
        if DATA_BACKUP_FILE.exists():
            try:
                backup_data = json.loads(DATA_BACKUP_FILE.read_text(encoding="utf-8"))
                print("[DATA] ✅ Obnoven backup soubor")
                return backup_data
            except Exception as e2:
                print(f"[DATA] ❌ Backup je také poškozený: {e2}")
    except Exception as e:
        print(f"[DATA] ❌ Chyba při čtení dat: {e}")
    
    return {"verse_streak": {}, "game_activity": {}, "user_xp": {}, "stats": {}}

async def _save_data(db):
    """Ulož data s automatickým backupem (ochrana dat)."""
    async with _data_lock:
        try:
            # Nejdřív vytvoř backup starého souboru (pokud existuje)
            if DATA_FILE.exists():
                try:
                    old_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                    DATA_BACKUP_FILE.write_text(json.dumps(old_data, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as e:
                    print(f"[DATA] ⚠️ Backup selhal: {e}")
            
            # Validuj data před uložením
            if not isinstance(db, dict):
                raise ValueError("Data nejsou dict")
            
            # Ulož nová data
            DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[DATA] ❌ Chyba při ukládání dat: {e}")

def _g(db, gid, key, default):
    """Guild-specific data namespace"""
    return db.setdefault(str(gid), {}).setdefault(key, default)

def _can_send_game_blessing(user_id: int, game_name: str) -> bool:
    """Zkontroluj jestli je game blessing na cooldown."""
    now = time.time()
    
    # Inicializuj user v cooldownech
    if user_id not in _game_blessing_cooldowns:
        _game_blessing_cooldowns[user_id] = {}
    
    user_cooldowns = _game_blessing_cooldowns[user_id]
    
    # Zkontroluj jestli je hra na cooldownu
    if game_name in user_cooldowns:
        last_blessing_time = user_cooldowns[game_name]
        elapsed = now - last_blessing_time
        
        if elapsed < GAME_BLESSING_COOLDOWN:
            remaining = GAME_BLESSING_COOLDOWN - elapsed
            print(f"[game_blessing] {user_id} -> {game_name}: Cooldown - zbývá {remaining:.1f}s")
            return False
    
    # Blessing je povolený, zaznamenej čas
    user_cooldowns[game_name] = now
    return True

# ═══════════════════════════════════════════════════════════════════════════════
#                    SLEDOVÁNÍ KONČÍCÍCH HER (v2.6)
# ═══════════════════════════════════════════════════════════════════════════════
_free_games_cache = {}  # {"game_title": {"expires_at": timestamp, "source": "Epic", ...}}
_free_games_last_update = 0

def _check_expiring_games():
    """Kontroluj které hry brzy expirují (za <7 dní) a vrať je."""
    global _free_games_cache, _free_games_last_update
    
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    
    # Aktualizuj cache každých 6 hodin
    if now - _free_games_last_update < 21600:  # 6 hodin
        return {}
    
    # Příliš komplexní - raději se obejdem bez tracking expiration
    # (API to nevrací - museli bychom scrapovat stránky)
    # Zatím ignorujeme, stačí základní status per-source
    return {}

def _get_expiring_games_message():
    """Vrátí message pro upozornění na končící hry, pokud existují."""
    expiring = _check_expiring_games()
    if not expiring:
        return None
    
    msg = "⏰ **Upozornění na končící hry:**\n"
    for game, info in list(expiring.items())[:3]:
        days_left = (info.get("expires_at", 0) - datetime.datetime.now(datetime.timezone.utc).timestamp()) / 86400
        msg += f"- {game} ({info.get('source', 'Unknown')}): {int(days_left)} dní zbývá\n"
    return msg if len(expiring) > 0 else None

def _get_guild_all_config(db, gid: int) -> dict:
    """Vrátí kompletní konfiguraci pro guild z bot_data.json (v2.5)."""
    guild_data = _g(db, gid, "config", {})
    if "blessing_channel" not in guild_data:
        guild_data["blessing_channel"] = None
    if "freegames_channel" not in guild_data:
        guild_data["freegames_channel"] = None
    return guild_data

async def _save_guild_config_to_db(db, gid: int, channel_type: str, channel_id: Optional[int]):
    """Ulož channel konfiguraci do bot_data.json (v2.5)."""
    config = _get_guild_all_config(db, gid)
    channel_key = f"{channel_type}_channel"
    if channel_key in config:
        config[channel_key] = channel_id
        _g(db, gid, "config", config)
        await _save_data(db)
        print(f"[config] Guild {gid}: {channel_type} → {channel_id} (uloženo)")

# ═══════════════════════════════════════════════════════════════════════════════
#                      5. AUDIO DETECTION & SETUP
# ═══════════════════════════════════════════════════════════════════════════════

try:
    import nacl
    HAS_NACL = True
except Exception:
    HAS_NACL = False

import discord.opus as _opus
HAS_OPUS = _opus.is_loaded()
if not HAS_OPUS:
    for _name in ("libopus.so.0", "libopus.so", "opus"):
        try:
            _opus.load_opus(_name)
            HAS_OPUS = True
            break
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════════════════
#                  6. MUSIC SYSTEM VARIABLES & FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

music_queues = {}
now_playing = {}
bot_loop = None
voice_locks = {}
last_voice_channel = {}
recently_announced_games = set()
voice_inactivity_timers = {}  # {guild_id: asyncio.Task}
queue_urls_seen = {}  # {guild_id: set(urls)} – v2.4 blokace duplicit
song_durations = {}  # {song_url: duration_seconds} – v2.4 odhad času

# v2.8.1: YouTube od 2024/2025 vyžaduje pro spolehlivou extrakci vybrat "player klienty",
# které nepotřebují PO token (jinak hrozí "Sign in to confirm you're not a bot" / HTTP 403,
# nebo yt-dlp vrátí neplatný non-audio stream). Seznam klientů se čas od času mění podle
# toho, jak YouTube utahuje ochrany – proto je nastavitelný přes .env bez zásahu do kódu.
#
# v2.8.2 FIX: vynucené "android_vr,web_safari,tv" přestalo fungovat úplně (YouTube tyto
# klienty mezitím omezil – yt-dlp extrakce "uspěje", ale vrácené URL dá při stahování
# HTTP 403, ověřeno i přímo přes yt-dlp downloader, ne jen ffmpeg). Aktuální yt-dlp
# (2025.06+) si player klienty vybírá spolehlivě sám, takže default je teď prázdný
# (= necháme volbu na yt-dlp) a přepsání přes YTDLP_PLAYER_CLIENTS je jen nouzová záloha,
# kdyby YouTube zase něco změnil.
YTDLP_PLAYER_CLIENTS = [
    c.strip() for c in os.getenv("YTDLP_PLAYER_CLIENTS", "").split(",") if c.strip()
]
# Volitelný cookies.txt (Netscape formát) pro věkově omezená/přísněji blokovaná videa.
YTDLP_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "").strip()

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": None,
    "source_address": "0.0.0.0",
    "socket_timeout": 30,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
}
# Jen když admin výslovně nastaví YTDLP_PLAYER_CLIENTS v .env, přepiš volbu klienta –
# jinak necháme yt-dlp, ať si vybere sám (viz komentář výše, proč je to teď default).
if YTDLP_PLAYER_CLIENTS:
    YDL_OPTS["extractor_args"] = {"youtube": {"player_client": YTDLP_PLAYER_CLIENTS}}
if YTDLP_COOKIES_FILE:
    if pathlib.Path(YTDLP_COOKIES_FILE).exists():
        YDL_OPTS["cookiefile"] = YTDLP_COOKIES_FILE
        print(f"[yt-dlp] Používám cookies soubor: {YTDLP_COOKIES_FILE}")
    else:
        print(f"[yt-dlp] ⚠️ YTDLP_COOKIES_FILE je nastaveno, ale soubor neexistuje: {YTDLP_COOKIES_FILE}")

FFMPEG_RECONNECT = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -rw_timeout 5000000 -nostdin"
FFMPEG_OPTIONS = "-vn -ac 1 -b:a 128k -bufsize 256k"
FFMPEG_OPTIONS_RPi = "-vn -ac 1 -b:a 96k -bufsize 128k"

def get_ffmpeg_options():
    """Vrať optimalizované FFmpeg options (RPi má nižší bitrate)."""
    is_rpi = _is_arm_system()
    return FFMPEG_OPTIONS_RPi if is_rpi else FFMPEG_OPTIONS

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def _headers_str_from_info(info: dict) -> str:
    """Extrahuj HTTP headery z yt-dlp info dict."""
    headers = info.get("http_headers") or {}
    return "".join(f"{k}: {v}\r\n" for k, v in headers.items())

def make_before_options(headers_str: str) -> str:
    """Vytvoř before_options pro FFmpeg včetně HTTP headerů."""
    if not headers_str:
        return FFMPEG_RECONNECT
    safe = headers_str.replace('"', r'\"')
    return f'{FFMPEG_RECONNECT} -headers "{safe}"'

def ytdlp_extract(url: str):
    """Extrahuj URL a headery z YouTube/stream. Retry na timeout.

    POZOR: Toto je BLOKUJÍCÍ (synchronní) síťová operace – volej vždy přes
    `await asyncio.to_thread(ytdlp_extract, url)`, nikdy přímo z async funkce,
    jinak se zasekne celý bot (event loop) na všech serverech najednou.
    """
    max_retries = 2
    last_err = None

    for attempt in range(max_retries):
        try:
            with _yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
                if "entries" in info:
                    if not info["entries"]:
                        raise ValueError("Playlist je prázdný nebo žádné videa")
                    info = info["entries"][0]

                if not info.get("url"):
                    raise ValueError("Žádné audio URL v odpovědi yt-dlp")

                # v2.8.1: Ochrana proti staré/nekompatibilní verzi yt-dlp, která na dnešním
                # YouTube občas nevrátí chybu, ale místo audia potichu vybere neplatný
                # stream (např. "mhtml" storyboard náhledy bez zvuku).
                if info.get("ext") == "mhtml" or info.get("acodec") in (None, "none"):
                    raise ValueError(
                        "yt-dlp vrátil stream bez zvuku (pravděpodobně zastaralá verze yt-dlp). "
                        "Zkus: pip install -U yt-dlp"
                    )

                return {
                    "title": info.get("title", "Unknown"),
                    "url": info["url"],
                    "webpage_url": info.get("webpage_url") or url,
                    "headers": _headers_str_from_info(info),
                    "duration": info.get("duration") or 180,
                }
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                print(f"[yt-dlp extract attempt {attempt+1}] {type(e).__name__}: {e}")
                time.sleep(1)
            continue

    raise last_err

def _queue_for(guild_id: int) -> deque:
    if guild_id not in music_queues:
        music_queues[guild_id] = deque()
    return music_queues[guild_id]

def _guild_lock(gid: int) -> asyncio.Lock:
    if gid not in voice_locks:
        voice_locks[gid] = asyncio.Lock()
    return voice_locks[gid]

def _init_queue_urls_seen(guild_id: int):
    """Inicializuj set pro sledování URL v frontě (v2.4)."""
    if guild_id not in queue_urls_seen:
        queue_urls_seen[guild_id] = set()

def _is_url_in_queue(guild_id: int, url: str) -> bool:
    """Kontroluj, zda URL už je ve frontě (v2.4 – blokace duplicit)."""
    _init_queue_urls_seen(guild_id)
    return url in queue_urls_seen[guild_id]

def _add_url_to_queue(guild_id: int, url: str):
    """Přidej URL do setu - zabrání duplicitám (v2.4)."""
    _init_queue_urls_seen(guild_id)
    queue_urls_seen[guild_id].add(url)

def _remove_url_from_queue(guild_id: int, url: str):
    """Odeber URL ze setu když se vymaže z fronty (v2.4)."""
    _init_queue_urls_seen(guild_id)
    queue_urls_seen[guild_id].discard(url)

def _clear_queue_urls(guild_id: int):
    """Vyčisti URL set když se vymaže celá fronta (v2.4)."""
    if guild_id in queue_urls_seen:
        queue_urls_seen[guild_id].clear()

def _estimate_queue_duration(guild_id: int) -> tuple:
    """Odhad doby trvání fronty (v2.4). Vrátí (minuces, seconds, songs)."""
    queue = _queue_for(guild_id)
    total_seconds = 0
    
    for item in queue:
        url = item.get("url", "")
        # Fallback: 3 minuty pokud nemáme data
        duration = song_durations.get(url, 180)
        total_seconds += duration
    
    total_minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return (total_minutes, remaining_seconds, len(queue))

# v2.5 CONFIG HELPERS
def _get_channel_for_type(guild: discord.Guild, channel_type: str) -> Optional[discord.TextChannel]:
    """Vrátí channel objektu dle typu (blessing, freegames), nebo fallback na jméno."""
    # Načti konfiguraci z bot_data.json
    db = _load_data()
    config = _get_guild_all_config(db, guild.id)
    channel_id = config.get(f"{channel_type}_channel")
    
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            return channel
    
    # Fallback na staré hledání podle jména
    fallback_names = {
        "blessing": "požehnání🙏",
        "freegames": "hry_zdarma💵"
    }
    fallback_name = fallback_names.get(channel_type)
    if fallback_name:
        return discord.utils.get(guild.text_channels, name=fallback_name)
    
    return None

def _is_youtube_playlist(url: str) -> bool:
    """Detekuj zda je URL YouTube playlist (v2.4.1)."""
    return "youtube.com/playlist" in url or "youtu.be/playlist" in url or "list=" in url

def _shuffle_queue(guild_id: int):
    """Zamíchej frontu - zachovej první skladbu (v2.4.1)."""
    queue = _queue_for(guild_id)
    if len(queue) <= 1:
        return False
    
    # Vezmi první skladbu
    first = queue[0]
    # Vezmi zbytek a zamíchej
    rest = list(queue)[1:]
    random.shuffle(rest)
    # Rekonstruuj frontu
    queue.clear()
    queue.append(first)
    queue.extend(rest)
    return True

def _extract_playlist_tracks_sync(url: str) -> list:
    """Blokující (synchronní) část extrakce playlistu – volej jen přes asyncio.to_thread."""
    ydl_opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30
    }

    with _yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        tracks = []

        if info and "entries" in info:
            for entry in info.get("entries", []):
                if entry:
                    track_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                    track_title = entry.get("title", "Neznámá skladba")
                    tracks.append({"url": track_url, "title": track_title})

        return tracks

async def extract_playlist_tracks(url: str) -> list:
    """Extrahuj všechny skladby z YouTube playlistu (v2.4.1).

    v2.8.1: Běží v thread poolu (asyncio.to_thread), aby extrakce velkého
    playlistu neblokovala event loop (a tím celého bota na všech serverech).
    """
    try:
        return await asyncio.to_thread(_extract_playlist_tracks_sync, url)
    except Exception as e:
        print(f"[playlist] Error extracting tracks: {e}")
        return []

async def wait_until_connected(vc: Optional[discord.VoiceClient], tries: int = 15, delay: float = 0.3) -> bool:
    """Opakovaně zkontroluj, zda je voice skutečně připojený."""
    for i in range(tries):
        if vc and vc.is_connected():
            await asyncio.sleep(0.1)
            return True
        wait_time = delay * (i + 1) if i < 3 else delay * 3
        await asyncio.sleep(wait_time)
    return False

async def ensure_voice_by_guild(guild: discord.Guild, *, text_channel: Optional[discord.TextChannel] = None) -> Optional[discord.VoiceClient]:
    """Zajisti voice connection pro guild."""
    gid = guild.id
    async with _guild_lock(gid):
        existing_vc = discord.utils.get(bot.voice_clients, guild=guild)
        if existing_vc and existing_vc.is_connected():
            return existing_vc
        
        last_ch_id = last_voice_channel.get(gid)
        if last_ch_id:
            last_ch = guild.get_channel(last_ch_id)
            if last_ch and isinstance(last_ch, discord.VoiceChannel):
                try:
                    vc = await last_ch.connect(timeout=30.0, reconnect=True)
                    connected = await wait_until_connected(vc, tries=10, delay=0.3)
                    if connected:
                        print(f"[voice] Reconnected to {last_ch.name} in {guild.name}")
                        return vc
                except Exception as e:
                    print(f"[voice] Failed to reconnect to {last_ch.name}: {e}")
        return None

async def play_next(guild: discord.Guild, text_channel: discord.TextChannel):
    """Přehrávej další skladbu v frontě."""
    queue = _queue_for(guild.id)
    
    if not queue:
        print(f"[music] Queue empty in {guild.name}")
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if vc and vc.is_connected():
            now_playing[guild.id] = None
            # Nastav inactivity timer – odpoj se po 2 minutách
            gid = guild.id
            if gid in voice_inactivity_timers:
                voice_inactivity_timers[gid].cancel()
            
            async def disconnect_after_delay():
                await asyncio.sleep(120)  # 2 minuty
                try:
                    if vc.is_connected():
                        await vc.disconnect()
                        print(f"[music] Disconnected from {guild.name} after 2 min inactivity")
                except:
                    pass
            
            task = asyncio.create_task(disconnect_after_delay())
            voice_inactivity_timers[gid] = task
        return
    
    song = queue.popleft()
    
    # v2.4: Auto-clean – vymaž URL ze setu když se vymaže z fronty
    song_url = song.get("url", "")
    if song_url:
        _remove_url_from_queue(guild.id, song_url)
    
    try:
        print(f"[music] Extracting: {song['url']}")
        # v2.8.1: asyncio.to_thread – blokující yt-dlp extrakce nesmí zaseknout event loop
        extracted = await asyncio.to_thread(ytdlp_extract, song['url'])
        
        vc = await ensure_voice_by_guild(guild, text_channel=text_channel)
        if not vc:
            await text_channel.send("❌ Nelze se připojit k voice kanálu!")
            return
        
        # Zruš inactivity timer, protože se má co přehrávat
        gid = guild.id
        if gid in voice_inactivity_timers:
            voice_inactivity_timers[gid].cancel()
            del voice_inactivity_timers[gid]
        
        headers = extracted.get("headers", "")
        before_options = make_before_options(headers)
        source = discord.FFmpegOpusAudio(
            extracted["url"],
            before_options=before_options,
            options=get_ffmpeg_options()
        )
        
        # Použij uložený název ze song dictu, nebo fallback na extrahovaný
        title = song.get("title", extracted["title"])
        now_playing[guild.id] = title
        
        def after_play(error):
            if error:
                print(f"[music] Playback error: {error}")
            asyncio.run_coroutine_threadsafe(
                play_next(guild, text_channel),
                bot.loop
            )
        
        vc.play(source, after=after_play)
        
        # Inkrementuj counter přehraných skladeb (v2.7.1)
        increment_songs_played()
        
        embed = discord.Embed(title="🎵 Přehrávám", description=title, color=discord.Color.blue())
        
        # Přidej tlačítka pro ovládání
        class MusicControlView(discord.ui.View):
            def __init__(self, guild_id):
                super().__init__(timeout=None)
                self.guild_id = guild_id
            
            @discord.ui.button(label="⏭️", style=discord.ButtonStyle.blurple)
            async def next_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                guild = button_interaction.guild
                vc = discord.utils.get(bot.voice_clients, guild=guild)
                if vc and vc.is_playing():
                    vc.stop()
                    await button_interaction.response.defer()
                else:
                    await button_interaction.response.send_message("❌ Nic se nehraje!", ephemeral=True)
            
            @discord.ui.button(label="⏸️", style=discord.ButtonStyle.blurple)
            async def pause_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                guild = button_interaction.guild
                vc = discord.utils.get(bot.voice_clients, guild=guild)
                if vc and vc.is_playing():
                    vc.pause()
                    await button_interaction.response.defer()
                elif vc and vc.is_paused():
                    vc.resume()
                    await button_interaction.response.defer()
                else:
                    await button_interaction.response.send_message("❌ Nic se nehraje!", ephemeral=True)
            
            @discord.ui.button(label="🔀", style=discord.ButtonStyle.blurple)
            async def shuffle_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                guild = button_interaction.guild
                if guild.id in music_queues and len(music_queues[guild.id]) > 1:
                    queue = list(music_queues[guild.id])
                    if len(queue) > 1:
                        current = queue[0]
                        rest = queue[1:]
                        random.shuffle(rest)
                        music_queues[guild.id] = deque([current] + rest)
                    await button_interaction.response.defer()
                else:
                    await button_interaction.response.send_message("❌ Ve frontě méně než 2 skladby!", ephemeral=True)
        
        await text_channel.send(embed=embed, view=MusicControlView(guild.id))
        
    except Exception as e:
        now_playing[guild.id] = None
        await text_channel.send(f"❌ Chyba při přehrávání: {str(e)[:100]}")
        print(f"[music] Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                   7. VERSE STREAK TRACKING DATA
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_ps_article_image(item: ET.Element) -> str:
    """Z RSS itemu vytáhne obrázek články (media:content / media:thumbnail / enclosure / <img> v HTML)."""
    ns = {
        "media": "http://search.yahoo.com/mrss/",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }

    # 1) media:content
    media_content = item.find("media:content", ns)
    if media_content is not None:
        url = (media_content.attrib.get("url") or "").strip()
        if url:
            print(f"[extract_image] ✅ Našel media:content: {url[:80]}...")
            return url

    # 2) media:thumbnail
    media_thumb = item.find("media:thumbnail", ns)
    if media_thumb is not None:
        url = (media_thumb.attrib.get("url") or "").strip()
        if url:
            print(f"[extract_image] ✅ Našel media:thumbnail: {url[:80]}...")
            return url

    # 3) enclosure
    enclosure = item.find("enclosure")
    if enclosure is not None:
        url = (enclosure.attrib.get("url") or "").strip()
        typ = (enclosure.attrib.get("type") or "").lower()
        if url and ("image" in typ or url.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))):
            print(f"[extract_image] ✅ Našel enclosure: {url[:80]}...")
            return url

    # 4) content:encoded (HTML)
    content_encoded = item.find("content:encoded", ns)
    if content_encoded is not None and content_encoded.text:
        m = re.search(r'<img[^>]+src="([^"]+)"', content_encoded.text, flags=re.IGNORECASE)
        if m:
            url = m.group(1).strip()
            print(f"[extract_image] ✅ Našel img v content:encoded: {url[:80]}...")
            return url

    # 5) description (HTML)
    desc = item.find("description")
    if desc is not None and desc.text:
        m = re.search(r'<img[^>]+src="([^"]+)"', desc.text, flags=re.IGNORECASE)
        if m:
            url = m.group(1).strip()
            print(f"[extract_image] ✅ Našel img v description: {url[:80]}...")
            return url
    
    # 6) Zkus scrapeovat přímo z linku v artiklu
    link_el = item.find("link")
    if link_el is not None and link_el.text:
        article_url = link_el.text.strip()
        print(f"[extract_image] 🔍 Scrapeuju článek: {article_url}")
        try:
            r = requests.get(article_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                # Hledej og:image meta tag (Open Graph)
                m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', r.text, flags=re.IGNORECASE)
                if m:
                    img_url = m.group(1).strip()
                    if img_url:
                        print(f"[extract_image] ✅ Našel og:image: {img_url[:80]}...")
                        return img_url
                
                # Hledej libovolnou <img> značku v článku
                m = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', r.text, flags=re.IGNORECASE)
                if m:
                    img_url = m.group(1).strip()
                    if img_url and "pixel" not in img_url.lower():  # Skip pixel/tracking images
                        print(f"[extract_image] ✅ Našel img v HTML: {img_url[:80]}...")
                        return img_url
                
                print(f"[extract_image] ❌ Žádný obrázek v článku: {article_url}")
        except Exception as e:
            print(f"[extract_image] ❌ Chyba při scrapování {article_url}: {e}")

    print(f"[extract_image] ❌ Žádný obrázek nenalezen")
    return ""

def format_price_display(original_price: str) -> str:
    """Formátuje zobrazení ceny - přeškrtnuta původní + ZDARMA pod ní"""
    if original_price and original_price != "N/A" and original_price != "0" and original_price != "Zdarma":
        return f"~~{original_price}~~\n**ZDARMA**"
    return "**ZDARMA**"

def get_platform_icon(source: str) -> str:
    """Vrací emoji ikonu podle platformy/zdroje"""
    return "🎮"  # Jeden ovladač pro všechny platformy

def get_platform_logo_url(source: str) -> str:
    """Vrací URL na logo platformy pro embed thumbnail"""
    source_lower = source.lower()
    if "epic" in source_lower:
        # Epic Games logo - veřejný CDN
        return "https://cdn2.unrealengine.com/egs-site-favicon-32x32-1a2e4eb01ff7.ico"
    elif "steam" in source_lower:
        # Steam logo - veřejný CDN
        return "https://store.akamai.steamstatic.com/public/images/favicons/favicon-32x32.png"
    elif "playstation" in source_lower or "psn" in source_lower or "ps+" in source_lower:
        # PlayStation logo - veřejný CDN
        return "https://www.playstation.com/content/dam/corporate/images/logos/playstation-logo-icon.png"
    else:
        return ""


def get_free_games():
    """Sbírá zdarma hry z více zdrojů: Epic, Steam, PlayStation Plus.
    
    Vrací tuple: (list her s info, dict source_status)
    """
    games = []
    seen = set()
    source_status = {
        "epic": False,
        "steam": False,
        "playstation": False
    }

    # ═══ EPIC GAMES ═══
    try:
        epic_api = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        response = requests.get(epic_api, timeout=8)
        data = response.json()
        
        if response.status_code != 200:
            print(f"[freegames] Epic HTTP {response.status_code}")
        else:
            promotions = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            
            for element in promotions:
                try:
                    if not isinstance(element, dict):
                        continue
                    
                    # Kontrola je-li hra zdarma
                    price_info = element.get("price") or {}
                    if not isinstance(price_info, dict):
                        continue
                    
                    total_price = price_info.get("totalPrice") or {}
                    if not isinstance(total_price, dict):
                        continue
                    
                    discount_price = total_price.get("discountPrice")
                    is_free = element.get("promotions", {}).get("isFreeGame", False)
                    
                    if discount_price == 0 or is_free:
                        title = element.get("title", "Unknown")
                        product_slug = element.get("productSlug", "")
                        
                        # Filtruj entries s prázdným slugem
                        if not product_slug or isinstance(product_slug, (list, dict)):
                            continue
                        
                        if product_slug:
                            url = f"https://store.epicgames.com/p/{product_slug}"
                            
                            # Sbírá obrázek
                            image = ""
                            key_images = element.get("keyImages", [])
                            if key_images and isinstance(key_images, list) and len(key_images) > 0:
                                image_obj = key_images[0]
                                if isinstance(image_obj, dict):
                                    image = image_obj.get("url", "")
                            
                            # Datum vydání
                            release_date = "TBA"
                            if element.get("releaseDate"):
                                release_date = element.get("releaseDate", "TBA")
                            
                            # Kdy skončí být zdarma
                            expire_date = "Permanent"
                            # Zkus najít endDate v promotions
                            promo = element.get("promotions", {})
                            if promo:
                                promo_offers = promo.get("promotionalOffers", [])
                                if promo_offers and len(promo_offers) > 0:
                                    offers = promo_offers[0].get("promotionalOffers", [])
                                    if offers and len(offers) > 0:
                                        end_date = offers[0].get("endDate")
                                        if end_date:
                                            # Převeď ISO format na čitelnější
                                            from datetime import datetime as dt_class
                                            try:
                                                dt = dt_class.fromisoformat(end_date.replace('Z', '+00:00'))
                                                expire_date = dt.strftime("%d.%m.%Y %H:%M")
                                            except:
                                                expire_date = end_date
                            
                            key = (title, url)
                            if key not in seen:
                                seen.add(key)
                                
                                # Hledej slevu z promotions
                                reviews = "Zdarma"
                                promo = element.get("promotions", {})
                                if promo:
                                    promo_offers = promo.get("promotionalOffers", [])
                                    if promo_offers and len(promo_offers) > 0:
                                        offers = promo_offers[0].get("promotionalOffers", [])
                                        if offers and len(offers) > 0:
                                            discount = offers[0].get("discountSetting", {}).get("discountPercentage")
                                            # Discount procento se již nezobrazuje v Reviews poli
                                            reviews = ""
                                
                                # POZNÁMKA: Tahej původní cenu z fmtPrice
                                # OMEZENÍ: Pro free games vrací API všechny ceny jako 0
                                # fmtPrice.originalPrice = "0" nebo "Zdarma" 
                                # Nesmysluplné, takže raději používáme "Zdarma"
                                # Pokud chceme skutečnou cenu, musíme scrapovat web, což je komplikované
                                original_price = "Zdarma"
                                fmt_price = total_price.get("fmtPrice", {})
                                if isinstance(fmt_price, dict):
                                    orig_price_str = fmt_price.get("originalPrice", "")
                                    # Filtruj "0" a "Zdarma" hodnoty
                                    if orig_price_str and orig_price_str not in ("0", "Zdarma"):
                                        original_price = orig_price_str
                                
                                games.append({
                                    "title": title,
                                    "url": url,
                                    "source": "Epic Games",
                                    "image": image,
                                    "original_price": original_price,
                                    "expire_date": expire_date,
                                    "reviews": reviews,
                                    "platforms": "Multi-platform"
                                })
                                source_status["epic"] = True
                except Exception:
                    continue
    except Exception as e:
        print(f"[freegames] Epic error: {e}")

    # ═══ STEAM (limited-time free games via Reddit) ═══
    print("[freegames] Starting STEAM section...")
    try:
        # Použij Reddit API (nepotřebuje autentizaci pro read-only)
        reddit_url = "https://www.reddit.com/r/FreeGameFindings/new.json?limit=50"
        headers = {"User-Agent": "Mozilla/5.0 (Discord Bot - Jesus Bot)"}
        print(f"[freegames] STEAM: Connecting to {reddit_url}")
        r = requests.get(reddit_url, timeout=10, headers=headers)
        
        print(f"[freegames] Reddit HTTP {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            posts = data.get('data', {}).get('children', [])
            
            steam_count = 0
            for post in posts:
                try:
                    post_data = post.get('data', {})
                    title = post_data.get('title', '')
                    url = post_data.get('url', '')
                    permalink = f"https://www.reddit.com{post_data.get('permalink', '')}"
                    
                    # Filtruj pouze Steam posty s [Steam] tagem
                    if '[steam]' not in title.lower():
                        continue
                    
                    # Přeskoč PSA, Question, Other tagy
                    skip_tags = ['[psa]', '[question]', '[other]', '[expired]', '[ended]']
                    if any(tag in title.lower() for tag in skip_tags):
                        continue
                    
                    # Extrahuj název hry z titulu
                    game_name = title
                    
                    # Odstraň tagy
                    game_name = re.sub(r'\[.*?\]', '', game_name)
                    game_name = re.sub(r'\(.*?\)', '', game_name)
                    game_name = game_name.strip()
                    
                    # Pokud je název příliš dlouhý nebo prázdný, použij původní
                    if not game_name or len(game_name) > 80:
                        game_name = title[:80]
                    
                    # Zkus najít Steam store link v URL nebo v postu
                    steam_url = url
                    if 'steampowered.com' not in steam_url:
                        steam_url = permalink
                    
                    # Zkontroluj duplikáty
                    key = (game_name.lower(), steam_url)
                    if key in seen:
                        continue
                    
                    seen.add(key)
                    
                    # Zkus získat obrázek z Reddit preview
                    image = ""
                    preview = post_data.get('preview', {})
                    if preview:
                        images = preview.get('images', [])
                        if images and len(images) > 0:
                            source = images[0].get('source', {})
                            image = source.get('url', '')
                            image = html_unescape(image) if image else ""
                    
                    # Pokud není preview, zkus thumbnail
                    if not image:
                        thumbnail = post_data.get('thumbnail', '')
                        if thumbnail and thumbnail.startswith('http'):
                            image = thumbnail
                    
                    # Získej čas vytvoření
                    created_utc = post_data.get('created_utc', 0)
                    if created_utc:
                        created_date = datetime.datetime.fromtimestamp(created_utc)
                        time_ago = datetime.datetime.now() - created_date
                        
                        if time_ago.days > 0:
                            expire_str = f"Posted {time_ago.days}d ago"
                        elif time_ago.seconds >= 3600:
                            expire_str = f"Posted {time_ago.seconds // 3600}h ago"
                        else:
                            expire_str = f"Posted {time_ago.seconds // 60}m ago"
                    else:
                        expire_str = "Check post"
                    
                    # Získej upvotes
                    score = post_data.get('score', 0)
                    num_comments = post_data.get('num_comments', 0)
                    reviews = f"👍 {score} | 💬 {num_comments}"
                    
                    games.append({
                        "title": game_name,
                        "url": steam_url,
                        "source": "Steam (Reddit)",
                        "image": image,
                        "original_price": "Zdarma",
                        "expire_date": expire_str,
                        "reviews": reviews,
                        "platforms": "PC"
                    })
                    source_status["steam"] = True
                    steam_count += 1
                    
                    # Limit na 5 Steam giveaways
                    if steam_count >= 5:
                        break
                
                except Exception as post_error:
                    print(f"[freegames] Error parsing Reddit post: {post_error}")
                    continue
            
            print(f"[freegames] Found {steam_count} Steam giveaways from Reddit")
            if steam_count > 0:
                source_status["steam"] = True
        
        else:
            print(f"[freegames] Reddit HTTP {r.status_code}")

    except Exception as e:
        print(f"[freegames] Steam (Reddit) error: {e}")
        source_status["steam"] = False

    print(f"\n[DEBUG] After STEAM: total games = {len(games)}, steam_status = {source_status['steam']}")
    print(f"[DEBUG] Games list:")
    for i, g in enumerate(games):
        print(f"  {i+1}. {g.get('source', 'N/A')}: {g.get('title', 'N/A')}")
    
    # ═══ PLAYSTATION PLUS ═══
    try:
        ps_feed = "https://blog.playstation.com/tag/playstation-plus/feed/"
        r = requests.get(ps_feed, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            try:
                root = ET.fromstring(r.content)
                items = root.findall('.//item')
                count = 0

                for item in items[:12]:
                    title_el = item.find('title')
                    link_el = item.find('link')

                    title = title_el.text.strip() if title_el is not None and title_el.text else 'PlayStation Plus announcement'
                    link = link_el.text.strip() if link_el is not None and link_el.text else 'https://blog.playstation.com'

                    # ✅ vytáhni obrázek přímo z článku
                    image = _extract_ps_article_image(item)
                    
                    # Fallback: pokud helper nic nenajde, vrať PS logo
                    if not image:
                        image = "https://www.playstation.com/content/dam/corporate/images/logos/playstation-logo.png"

                    key = (title, link)
                    if key not in seen and count < 8:
                        seen.add(key)
                        pubdate_el = item.find('pubDate')
                        release_date = "Monthly Update"
                        if pubdate_el is not None and pubdate_el.text:
                            try:
                                import email.utils
                                parsed_date = email.utils.parsedate_to_datetime(pubdate_el.text)
                                release_date = parsed_date.strftime("%d. %B %Y")
                            except:
                                release_date = "Monthly Update"
                        
                        games.append({
                            "title": title,
                            "url": link,
                            "source": "PlayStation Plus",
                            "image": image,
                            "original_price": "Zdarma",
                            "expire_date": release_date,
                            "reviews": "PS Plus (Included)",
                            "platforms": "PlayStation"
                        })
                        source_status["playstation"] = True
                        count += 1

            except Exception as e:
                print(f"[freegames] PlayStation parse error: {e}")
        else:
            print(f"[freegames] PlayStation HTTP {r.status_code}")
    except Exception as e:
        print(f"[freegames] PlayStation error: {e}")

    return games, source_status

verse_streak = {}  # {user_id: {"count": int, "last_date": date}}
streak_messages = {
    0: "🎯 Začínáš svou cestu k Bohu! Veď ji s vírou.",
    1: "✨ 1 den! Pokračuj v modlitbě.",
    3: "🌟 3 dny! Bůh tě vidí a chválí.",
    7: "⭐ Týden! Tvá věrnost je krásná.",
    14: "💫 Dva týdny! Sláva tobě věrnému!",
    30: "🏆 Měsíc věry! Bůh tě požehná.",
    60: "👑 Dva měsíce! Jsi příkladem víry.",
    90: "🎖️ Tři měsíce! Nebeské vojska tě chválí!",
    365: "🌈 Rok! Tvá věrnost je vzorem pro všechny!",
}

# ═══════════════════════════════════════════════════════════════════════════════
#                 8. BIBLICKÉ VERŠE (55 kousků)
# ═══════════════════════════════════════════════════════════════════════════════

verses = [
    '"Bůh je láska, a kdo zůstává v lásce, zůstává v Bohu a Bůh v něm." (1 Jan 4,16)',
    '"Pán je můj pastýř, nebudu mít nedostatek." (Žalm 23,1–2)',
    '"Všechno mohu v Kristu, který mi dává sílu." (Filipským 4,13)',
    '"Neboj se, neboť já jsem s tebou." (Izajáš 41,10)',
    '"Žádejte, a bude vám dáno." (Matouš 7,7)',
    '"Ať se vaše srdce nechvějí!" (Jan 14,1)',
    '"Ve světě máte soužení, ale důvěřujte." (Jan 16,33)',
    '"Milujte své nepřátele." (Lukáš 6,27)',
    '"Radujte se v Pánu vždycky!" (Filipským 4,4)',
    '"Láska je trpělivá, láska je dobrotivá." (1 Korintským 13,4)',
    '"Požehnaný člověk, který doufá v Hospodina." (Jeremjáš 17,7)',
    '"Věř v Pána celým svým srdcem." (Přísloví 3,5)',
    '"Neboj se, jen věř." (Marek 5,36)',
    '"Já jsem světlo světa." (Jan 8,12)',
    '"Boží milosrdenství je věčné." (Žalm 136,1)',
    '"Nebuďte úzkostliví o svůj život." (Matouš 6,25)',
    '"Modlete se bez přestání." (1 Tesalonickým 5,17)',
    '"On uzdravuje ty, kdo mají zlomené srdce." (Žalm 147,3)',
    '"Já jsem s vámi po všechny dny." (Matouš 28,20)',
    '"Pane, nauč nás modlit se." (Lukáš 11,1)',
    '"Hledejte nejprve Boží království." (Matouš 6,33)',
    '"Tvá víra tě uzdravila." (Marek 5,34)',
    '"Buď silný a odvážný." (Jozue 1,9)',
    '"Žádná zbraň, která se proti tobě připraví, neuspěje." (Izajáš 54,17)',
    '"Jsem cesta, pravda i život." (Jan 14,6)',
    '"Pán je blízko všem, kdo ho vzývají." (Žalm 145,18)',
    '"Odpouštějte, a bude vám odpuštěno." (Lukáš 6,37)',
    '"Každý dobrý dar je shůry." (Jakub 1,17)',
    '"S radostí budete čerpat vodu ze studnic spásy." (Izajáš 12,3)',
    '"Neboť u Boha není nic nemožného." (Lukáš 1,37)',
    '"Hospodin je moje světlo a moje spása." (Žalm 27,1)',
    '"Milost vám a pokoj od Boha Otce našeho." (Filipským 1,2)',
    '"Ježíš Kristus je tentýž včera, dnes i navěky." (Židům 13,8)',
    '"Bůh sám bude s nimi." (Zjevení 21,3)',
    '"Kdo v něj věří, nebude zahanben." (Římanům 10,11)',
    '"Ať se radují všichni, kdo se k tobě utíkají." (Žalm 5,12)',
    '"Jeho milosrdenství je nové každé ráno." (Pláč 3,23)',
    '"Dej nám dnes náš denní chléb." (Matouš 6,11)',
    '"Neskládejte poklady na zemi." (Matouš 6,19)',
    '"Zůstaňte v mé lásce." (Jan 15,9)',
    '"Síla a krása jsou v jeho chrámu." (Žalm 29,4)',
    '"Blahoslavený ten, kdo slyší slovo Boží a střeží ho." (Lukáš 11,28)',
    '"Proměňujte se obnovou své mysli." (Římanům 12,2)',
    '"Neboť věčná slava je mnohem větší..." (2 Korintským 4,17)',
    '"Vaše tělo je chrámem Ducha svatého." (1 Korintským 6,19)',
    '"Být slabý – to je být silný v Kristu." (2 Korintským 12,10)',
    '"Věci, které vidíš, nejsou věčné; věci neviditelné jsou věčné." (2 Korintským 4,18)',
    '"Nic vás nemůže oddálit od Boží lásky." (Římanům 8,39)',
    '"Snad jsem vám psát smutný dopis..." (1 Tesalonickými 5,16–18)',
    '"Ten, kdo je v Kristu, je nové stvoření." (2 Korintským 5,17)',
    '"Běžte sebou v určené běh s vytrvalostí." (Židům 12,1)',
    '"Nezapomínejte na pohostinnost!" (Židům 13,2)',
    '"Bůh není Bůh těch mrtvých, ale živých." (Marek 12,27)',
    '"Jako otec se slitovává nad dětmi, tak se Pán slitovává nad těmi, kdo ho bojí." (Žalm 103,13)',
    '"Boží slovo je světlo mé noze a lampa mé stezce." (Žalm 119,105)',
    '"Voláš-li si mě, půjdu s tebou." (Izajáš 43,2)',
    '"Mám vám sdělit svůj pokoj, abyste byli v klidu." (Jan 14,27)',
    '"Nosim vás v životě, a budu vás nést až do stáří." (Izajáš 46,4)',
    '"Jeden den u Hospodina je lepší než tisíc jinde." (Žalm 84,11)',
    '"Dav modlitby se ozývá v jeho sluch." (Žalm 34,16)',
    '"Všechno vám bude odpuštěno, když věříte." (Marek 11,24)',
    '"Bůh ti dává sílu na každý den, který přijde." (Exodus 16,4)',
    '"Já jsem воскресení a život." (Jan 11,25)',
    '"Tvá věrnost tě neopustí." (Přísloví 20,22)'
]

# ═══════════════════════════════════════════════════════════════════════════════
#              9. GAME BLESSINGS DICTIONARY (53 her)
# ═══════════════════════════════════════════════════════════════════════════════

game_blessings = {
    "League of Legends": "Ať tě **toxicita** mine obloukem ↩️ a spoluhráči konečně pochopí, že **věž se nepushuje sama**! 🏰",
    "Counter-Strike 2": "Ať ti sedne **AIM** 🎯 a nenarazíš na žádnýho **bota** 🤖.",
    "Satisfactory": "Ať ti **továrna** jede plynule ⚙️ a ne jako by ji stavěl nějakej **ožrala**! 🍺",
    "Minecraft": "Ať **diamanty** 💎 najdeš dřív než ztratíš **trpělivost** s těma creeperama. 💥",
    "Mafia": "Pamatuj, **Přátelství je sračka** 🤫. Buď jako Tommy. **Čest** je to jediný, co tě drží nad vodou. 👔",
    "Mafia II": "Vítej v **rodině** 🤝. Ať ti mafiánský život v Empire Bay vydrží co nejdýl.",
    "Resident Evil 2": "Ať máš v Raccoon City **dost nábojů** 🔫 a ten G-Virus tě nechá na pokoji. 🧟",
    "Resident Evil 3": "Ať **Nemesis** dá pokoj a jde otravovat někoho, kdo o to fakt stojí. **STARS!** 🏃‍♀️",
    "Resident Evil 4": "Ať tě **Ashley nesere** 😠 nechodí ti do rány.",
    "Resident Evil 7": "Ať noc u **Bakerů** přežiješ s co nejmenším **psychickým poškozením** 🧠. Vítej v rodině... zase. 🏚️",
    "Resident Evil 8": "Ať tě **paní Dimitrescu** nenechá na pokoji 😩.",
    "KLETKA": "Ať ti **benzín nikdy nedojde** ⛽. V téhle díře bys zůstat nechtěl, věř mi.",
    "КЛЕТЬ Демо": "Ať tě **soused** radši ignoruje. Přejeme ti co nejdelší život. 🤞",
    "Ready or Not": "Ať máš **klidnou hlavu** 🧘. Jeden špatný pohyb a víš, jak to končí. **Clear!** 🚨",
    "Roblox": "Ať tě napadají jen ty **dobrý nápady** ✨ a radost ze hry ti vydrží dlouho. **Tvoř!**",
    "Counter-Strike: Global Offensive": "Ať tě **AIM** podrží 🎯 a tvůj **tým** nestojí za **hovno**! 💩",
    "Dota 2": "Ať tvůj **draft** drží pohromadě 🛡️ a **chat** zůstane tišejší než obvykle. **GG WP.**",
    "Cyberpunk 2077": "Pamatuj, **Johnny není vždycky zmrd** 🤘. Užij si Night City, V.",
    "Elden Ring": "Ať **boss** padne dřív, než ti stihne zlomit vůli 💔. **YOU DIED.**",
    "Team Fortress 2": "Ať ti **nostalgie** zabíjí míň než nepřátelská **Pyro** 🔥. *Mmmph Mmmph!*",
    "Rust": "Ať ti **základna** drží 🧱 a sousedi nejsou **psychopati s raketometem** 🚀.",
    "ARK: Survival Evolved": "Ať tě **dinosauři** spíš respektují než konzumují. **Tame all the things!** 🦖",
    "Grand Theft Auto V": "Ať **nenarazíš na moddery** 🚫 a tvoje peněženka zůstane plná. 💵",
    "Fall Guys": "Ať tě to **nevyhodí** na poslední překážce. **Koruna čeká!** 👑",
    "Terraria": "Ať tvoje **podzemí** skrývá víc **pokladů** 💰 než pastí. 罠",
    "Phasmophobia": "Ať **duchové** jen šeptají do mikrofonu 🎤 a ne do duše. **Evidence!**",
    "Valheim": "Ať tě **vítr** 🌬️ vede správným směrem a loď ti neodjede bez tebe. **Skål!** 🍻",
    "Among Us": "Ať tě **impostor** neodpráskne hned po startu 🔪 a posádka používá **mozek**! 🧠",
    "Rocket League": "Ať ti to lítá do **brány** 🥅 a ne naprosto mimo stadion. **Calculated!**",
    "The Witcher 3": "Ať cesta za **Ciri** je klidná, **rozhodnutí rozumná** 🧐 a Gwent ti jde líp než všem hospodskejm dohromady. 🃏",
    "Red Dead Redemption 2": "Ať si udržíš **čest** ✨ a koně ti nikdy **nesestřelí náhodný idiot** v lese. 🐴",
    "Hades": "Ať se **Zagreus** konečně dostane **nahoru** ⬆️ bez dalších pater agrese. **Chthonic!**",
    "Tom Clancy's Rainbow Six Siege X": "Ať ti **taktika** sedne 🛡️ a **drony** ukážou všechno, co mají. **Pew pew!**",
    "Skyrim": "Ať tě **draci** nechají v klidu 🐉 a **Fus Ro Dah** používáš jen, když opravdu **chceš** 📢.",
    "The Binding of Isaac: Rebirth": "Ať **RNG** konečně jednou stojí na tvojí straně. **Bůh ti žehnej!** 🙏",
    "Dead by Daylight": "Ať tě **Killer** míjí 🔪 a tvoje **loopování** má styl. **Run!** 🏃",
    "Project Zomboid": "Ať přežiješ další den 🗓️ a **nemrtví** ti nerozbijou barák na cihly. **Společnost!** 🧟",
    "Half-Life": "Ať tě nic nesežere 👽 a **Freeman** by se za tebe nemusel stydět. 🔬",
    "Half-Life 2": "Ať jdeš dopředu stejně tiše a **efektivně** jako **Gordon** 💥.",
    "Half-Life: Alyx": "Ať **Combine** neví, že existuješ, dokud není **pozdě** 💥.",
    "VALORANT": "Ať ti **AIM drží** 🎯 a **economia** se nezhroutí během dvou kol. **Jistota!**",
    "Arena Breakout: Infinite": "Ať **extrahueš s lootem** 💰 a vrátíš se bez jedinýho škrábance. **PMC master!**",
    "Fallout": "Ať tě **pustina nezlomí** 💔 a **atomovky** zůstanou jen na ozdobu. ☢️",
    "Fallout 2": "Ať tvoje cesta končí spíš **úsměvem** 😊 než velkým **bum**! 💣",
    "Fallout 3": "Ať **Project Purity** konečně udělá svět **lepším místem** 💧.",
    "Fallout: New Vegas": "Ať ti **plán vyjde** 🤞 a **Vegas** je opravdu tvoje. **The Strip!** 🎰",
    "Fallout 4": "Ať najdeš, co hledáš 👀, a **Commonwealth** dáš do kupy. 🛠️",
    "Fallout 76": "Ať potkáš víc **lidí** 🤝 než prázdných baráků. **Welcome home!**",
    "Kingdom Come: Deliverance": "Ať tvoje jízdy na **Šedivce** 🐴 neskončí držkou v blátě. **Jindřich!** 🛡️",
    "Kingdom Come: Deliverance II": "Ať se **Jindra** dočká **klidu** a ty nepadáš v každým souboji. **Bojuj!** ⚔️",
    "Outlast": "Ať tě **Chris Walker** nikdy nechytí 🏃. *Shut up, little piggy.* 🐷",
    "Outlast 2": "BŮH CHCE TO DÍTĚ, BŮH CHCE TO DÍTĚ! 🙏 Ať přežiješ tuhle **šílenou jízdu** .",
    "The Outlast Trials": "Ať **přežiješ testy** 🧪 se všemi **končetinami** na místě. **Reagent!**",
    "Escape from Tarkov": "Ať tě nezastřelí týpek s **TOZkou přes půl mapy** 🚫 a extrahuješ dřív, než ti dojde **krev** 🩸.",
    "The Last of Us": "Ať tě **svět nezlomí** a každý krok stojí za to. **Přežij!** 🦠",
    "Dark Souls III": "Ať **boss padne** dřív, než ty padneš **psychicky** 😵. **Praise the Sun!** 🌞",
    "Starfield": "Ať tvůj **vesmír** 🌌 není prázdnější než půlka galaxií, co jsi už viděl. **Discovery!**",
    "Forza Horizon 5": "Ať ti to **klouže** jen když chceš 🏎️, ne když to zrovna nejmíň potřebuješ. **Drift master!**",
    "Genshin Impact": "Ať jsou tvé **denní krystaly** 🔮 vždy plné a ať ti Pán zabrání farmiť **Artifacty** s těmi nejhoršími staty. 😇",
    "Schedule I": "Ať ti **kontraband** projde pod nosem fízlů 🚔 a tvoje **impérium** roste. 💊",
    "Geometry Dash": "Ať tvůj **click** sedne na milisekundu přesně 🔊 a ten poslední **triple spike** nezlomí nervy. 🔺",
    "ARC Raiders": "Ať se ti **roboti** vyhýbají 🤖 a tvůj **loot** stojí za ten risk. **Scavenge or die!** 🛠️",
    "The Forest": "Ať tvůj **barák na stromě** vydrží nájezdy mutantů 🌲 a ten malej **Timmy** tě jednou fakt najde. 🦴",
    "Sons Of The Forest": "Ať ti **Kelvin** nekácí stromy na hlavu a **Virginia** ti kryje záda, když jde do tuhého. 🔫",
    "Fortnite": "přeji nejvíce **Victory Royale!** 👑",
}

# ═══════════════════════════════════════════════════════════════════════════════
#                  10. BOT EVENTS – STARTUP & READY
# ═══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    """Bot startup event – synchronizuj slash commands a spusť scheduled tasks."""
    print(f"✅ Bot je přihlášen jako {bot.user}")
    
    # 🔧 Inicializuj prázdný JSON pokud neexistuje (bezpečnost)
    db = _load_data()
    if not db:
        db = {"verse_streak": {}, "game_activity": {}, "user_xp": {}, "stats": {}}
        await _save_data(db)
        print("[init] ✅ Vytvořen nový bot_data.json")
    
    # Načti verse streak z storage
    await load_verse_streak_from_storage()
    
    # Načti game activity z storage
    await load_game_activity_from_storage()
    
    # Načti statistics z storage (v2.7.1)
    await load_stats_from_storage()
    
    # Validuj game activity data - pokud jsou poškozená, resetuj
    game_reset_needed = False
    for user_id, game_data in list(game_activity.items()):
        if not isinstance(game_data.get("games", {}), dict):
            print(f"[game-fix] Poškozená game data pro user {user_id}. Resetuji...")
            game_reset_needed = True
            break
        # Také zkontroluj, aby všechny hodiny byly čísla
        for game_name, hours in game_data.get("games", {}).items():
            try:
                if float(hours) < 0:
                    print(f"[game-fix] Negativní čas pro {game_name} (user {user_id}). Resetuji...")
                    game_reset_needed = True
                    break
            except (ValueError, TypeError):
                print(f"[game-fix] Chybný typ pro hodiny (user {user_id}). Resetuji...")
                game_reset_needed = True
                break
        if game_reset_needed:
            break
    
    if game_reset_needed:
        game_activity.clear()
        await save_game_activity_to_storage()
        print("[game-fix] ✅ game_activity resetován (poškozená data)")
    
    # Načti user XP z storage
    await load_user_xp_from_storage()
    
    # 🔧 FIX v2.3.1: Validuj XP data - pokud jsou anomální, resetuj
    # (ochrana proti poškozením dat z budoucích bugů)
    xp_reset_needed = False
    for user_id, xp_data in list(user_xp.items()):
        xp_value = xp_data.get("xp", 0)
        # Pokud má někdo > 100 000 XP (nemožné - to by byla 6667 vítězství v versfight)
        if xp_value > 100000:
            print(f"[xp-fix] Anomální XP: user {user_id} má {xp_value} XP. Resetuji...")
            xp_reset_needed = True
            break
    
    if xp_reset_needed:
        user_xp.clear()
        await save_user_xp_to_storage()
        print("[xp-fix] ✅ user_xp resetován (anomální data)")
    
    try:
        synced = await bot.tree.sync()
        print(f"[commands] Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"[commands] Sync error: {e}")
    
    send_morning_message.start()
    send_night_message.start()
    send_free_games.start()
    voice_watchdog.start()
    update_bot_presence.start()
    clear_recent_announcements.start()
    send_weekly_summary.start()
    track_game_activity_periodic.start()

# ═══════════════════════════════════════════════════════════════════════════════
#                10b. V2.7 – SERVER ANALYTICS & SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="serverstats", description="Přehled aktivit, hudby, miniher na serveru")
async def serverstats_command(interaction: discord.Interaction):
    """Server-wide analytics – aktivita, hudba, minihry (v2.7.1)."""
    try:
        await interaction.response.defer()
        guild = interaction.guild
        
        # Sbírání dat
        total_users = guild.member_count
        active_users = 0
        total_xp = 0
        games_played = {}
        
        for user_id, xp_data in user_xp.items():
            total_xp += xp_data.get("xp", 0)
            if xp_data.get("xp", 0) > 0:
                active_users += 1
        
        for user_id, game_data in game_activity.items():
            games = game_data.get("games", {})
            for game_name, hours in games.items():
                if hours > 0:
                    if game_name not in games_played:
                        games_played[game_name] = 0
                    games_played[game_name] += hours
        
        # Odhad přehraných skladeb z global counter (v2.7.1)
        songs_played = stats_data.get("songs_played_total", 0)
        
        # Top 5 her
        top_games = sorted(games_played.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Build embed
        embed = discord.Embed(
            title="📊 **Server Analytics – v2.7.1**",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="👥 Uživatelé",
            value=f"Celkem: **{total_users}**\nAktivní: **{active_users}**",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Experience",
            value=f"Celkové XP: **{total_xp:,}**",
            inline=True
        )
        
        embed.add_field(
            name="🎵 Hudba",
            value=f"Přehrané: **{songs_played}** skladeb",
            inline=True
        )
        
        if top_games:
            top_str = "\n".join([f"🎮 **{game}**: {hours:.1f}h" for game, hours in top_games])
            embed.add_field(name="🏆 Top hry", value=top_str, inline=False)
        else:
            embed.add_field(name="🏆 Top hry", value="Zatím žádné", inline=False)
        
        embed.set_footer(text="v2.7.1 Analytics | Jesus Bot")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba: {str(e)[:100]}")
        print(f"[serverstats] Error: {e}")

@bot.tree.command(name="leaderboard", description="Leaderboard hráčů podle XP a hodin")
async def leaderboard_command(interaction: discord.Interaction):
    """Dva leaderboards - XP a hodin (v2.7.2 s error handlingem)."""
    try:
        await interaction.response.defer()
        guild = interaction.guild
        
        # ============ LEADERBOARD 1: PODLE XP ============
        sorted_xp = sorted(user_xp.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
        
        embed_xp = discord.Embed(
            title="🏆 **Leaderboard – Top 10 podle XP**",
            color=discord.Color.gold()
        )
        
        xp_str = ""
        for idx, (user_id, xp_data) in enumerate(sorted_xp, 1):
            try:
                user = await bot.fetch_user(user_id)
                username = user.name
            except Exception as e:
                username = f"User {user_id}"
                print(f"[leaderboard] ⚠️ Nemohl jsem fetch user {user_id}: {e}")
            
            xp = max(0, xp_data.get("xp", 0))
            level = xp_data.get("level", "🟩 Věřící")
            
            # Přidej streak informaci
            streak_data = verse_streak.get(user_id, {})
            streak = max(0, streak_data.get("count", 0))
            
            xp_str += f"{idx}. **{username}**\n   ⭐ {xp}XP ({level}) | 🔥 Streak: {streak}\n"
        
        if xp_str:
            embed_xp.add_field(name="🏆 Žebříček podle XP na serveru", value=xp_str, inline=False)
        else:
            embed_xp.add_field(name="🏆 Žebříček podle XP na serveru", value="Zatím žádní hráči", inline=False)
        
        embed_xp.set_footer(text="v2.7.2 Leaderboard | Jesus Bot")
        
        # ============ LEADERBOARD 2: PODLE HODIN ============
        # Seřaď hráče podle celkových hodin
        hours_data = {}
        for user_id, game_data in game_activity.items():
            try:
                games = game_data.get("games", {})
                if isinstance(games, dict):
                    total_hours = sum(float(h) for h in games.values() if isinstance(h, (int, float)) and h > 0)
                    if total_hours > 0:
                        hours_data[user_id] = total_hours
            except Exception as e:
                print(f"[leaderboard] ⚠️ Chyba při výpočtu hodin pro user {user_id}: {e}")
        
        sorted_hours = sorted(hours_data.items(), key=lambda x: x[1], reverse=True)[:10]
        
        embed_hours = discord.Embed(
            title="⏰ **Leaderboard – Top 10 podle Hodin**",
            color=discord.Color.blurple()
        )
        
        hours_str = ""
        for idx, (user_id, total_hours) in enumerate(sorted_hours, 1):
            try:
                user = await bot.fetch_user(user_id)
                username = user.name
            except Exception as e:
                username = f"User {user_id}"
                print(f"[leaderboard] ⚠️ Nemohl jsem fetch user {user_id}: {e}")
            
            # Počet her
            game_data = game_activity.get(user_id, {"games": {}})
            num_games = len(game_data.get("games", {}))
            
            if isinstance(total_hours, (int, float)) and total_hours > 0:
                hours_str += f"{idx}. **{username}**\n   🎮 {total_hours:.1f}h ({num_games} her)\n"
        
        if hours_str:
            embed_hours.add_field(name="⏱️ Žebříček podle času stráveného hraním", value=hours_str, inline=False)
        else:
            embed_hours.add_field(name="⏱️ Žebříček podle času stráveného hraním", value="Zatím žádná data", inline=False)
        
        embed_hours.set_footer(text="v2.7.2 Leaderboard | Jesus Bot")
        
        # Pošli oba embedy
        await interaction.followup.send(embed=embed_xp)
        await interaction.followup.send(embed=embed_hours)
        print(f"[leaderboard] ✅ Leaderboard odeslán pro {interaction.user.name}")
        
    except Exception as e:
        error_msg = f"❌ Chyba: {str(e)[:100]}"
        print(f"[leaderboard] ❌ Chyba: {e}")
        try:
            await interaction.followup.send(error_msg)
        except Exception as send_err:
            print(f"[leaderboard] ⚠️ Nemohl jsem odeslat error message: {send_err}")



@bot.tree.command(name="weeklysummary", description="Týdenní shrnutí aktivit (TOP hráčů, her, eventů)")
async def weeklysummary_command(interaction: discord.Interaction):
    """Weekly summary – top players, games, trends (v2.7.3 s per-user tracking)."""
    try:
        await interaction.response.defer()
        
        now = datetime.datetime.now()
        
        # v2.7.3: Použij weekly_user_hours pro správná týdenní data per-user
        weekly_users = {uid: hours for uid, hours in weekly_user_hours.items() if hours > 0}
        total_playtime = stats_data.get('weekly_game_hours', 0.0)
        weekly_songs = stats_data.get('weekly_songs_played', 0)
        weekly_xp = stats_data.get('weekly_xp_gained', 0)
        
        print(f"[weeklysummary] 📊 Týdenní data: {total_playtime:.1f}h, {len(weekly_users)} hráčů, {weekly_songs} skladeb, {weekly_xp} XP")
        
        # Top hráči týdne (seřazeno podle skutečných týdenních hodin)
        top_weekly = sorted(weekly_users.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Build embed
        embed = discord.Embed(
            title="📅 **Týdenní Shrnutí – v2.7.3**",
            description=f"Období: {(now - datetime.timedelta(days=7)).strftime('%d.%m')} – {now.strftime('%d.%m.%Y')}",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="⏱️ Celkový čas hrání",
            value=f"**{total_playtime:.1f}** hodin",
            inline=True
        )
        
        embed.add_field(
            name="👥 Aktivní hráči",
            value=f"**{len(weekly_users)}** hráčů",
            inline=True
        )
        
        embed.add_field(
            name="🎵 Skladby / ⭐ XP",
            value=f"**{weekly_songs}** skladeb\n**{weekly_xp:,}** XP",
            inline=True
        )
        
        # Top hráči
        if top_weekly:
            top_str = ""
            for idx, (user_id, playtime) in enumerate(top_weekly, 1):
                try:
                    user = await bot.fetch_user(user_id)
                    username = user.name
                except Exception as e:
                    username = f"User {user_id}"
                    print(f"[weeklysummary] ⚠️ Nemohl jsem fetch user {user_id}: {e}")
                
                if isinstance(playtime, (int, float)) and playtime > 0:
                    top_str += f"{idx}. **{username}** – {playtime:.1f}h\n"
            
            if top_str:
                embed.add_field(name="🏆 Top hráči týdne", value=top_str, inline=False)
            else:
                embed.add_field(name="🏆 Top hráči týdne", value="Žádní hráči v datech", inline=False)
        else:
            embed.add_field(name="🏆 Top hráči týdne", value="Žádná data dostupná", inline=False)
        
        embed.set_footer(text="v2.7.3 Weekly Summary | Jesus Bot")
        await interaction.followup.send(embed=embed)
        print(f"[weeklysummary] ✅ Weekly summary odeslán pro {interaction.user.name}")
        
    except Exception as e:
        error_msg = f"❌ Chyba: {str(e)[:100]}"
        print(f"[weeklysummary] ❌ Chyba: {e}")
        try:
            await interaction.followup.send(error_msg)
        except Exception as send_err:
            print(f"[weeklysummary] ⚠️ Nemohl jsem odeslat error message: {send_err}")

# ═══════════════════════════════════════════════════════════════════════════════
#                11. SLASH COMMANDS – HUDBA / MUSIC
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="yt", description="Přidej skladbu do fronty a přehrávej z YouTube")
async def yt_command(interaction: discord.Interaction, url: str):
    """Slash command /yt – přehrávání hudby z YouTube. v2.4.1: Také playlisty!"""
    await interaction.response.defer()
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("❌ Musíš být na serveru!")
        return
    
    # Zjisti, ve kterém voice kanálu je uživatel
    user_voice_state = interaction.user.voice
    if not user_voice_state or not user_voice_state.channel:
        await interaction.followup.send("❌ Musíš být v voice kanálu!")
        return
    
    user_channel = user_voice_state.channel
    
    # Zjisti, zda je bot už v nějakém voice kanálu
    vc = discord.utils.get(bot.voice_clients, guild=guild)
    
    # Pokud bot není připojený, připoj ho do kanálu uživatele
    if not vc or not vc.is_connected():
        try:
            vc = await user_channel.connect(timeout=30.0, reconnect=True)
            last_voice_channel[guild.id] = user_channel.id
            await asyncio.sleep(0.5)
        except Exception as e:
            await interaction.followup.send(f"❌ Nemohu se připojit k voice kanálu: {str(e)[:100]}")
            return
    
    # v2.4.1: Detekuj playlist
    is_playlist = _is_youtube_playlist(url)
    
    if is_playlist:
        # PLAYLIST MODE – v2.4.1
        await interaction.followup.send("⏳ Načítám playlist... To může chvíli trvat...")
        
        try:
            tracks = await extract_playlist_tracks(url)
            
            if not tracks:
                await interaction.followup.send("❌ Playlist je prázdný nebo nedostupný!")
                return
            
            added_count = 0
            skipped_count = 0
            
            for track in tracks:
                track_url = track.get("url", "")
                track_title = track.get("title", "Neznámá skladba")
                
                # v2.4: Blokace duplicit
                if _is_url_in_queue(guild.id, track_url):
                    skipped_count += 1
                    continue
                
                # v2.4.1: Rychlý import - bez extrakce detailu (výchozí duration 180s)
                song_durations[track_url] = 180
                
                # Přidej do fronty
                _queue_for(guild.id).append({"url": track_url, "title": track_title})
                _add_url_to_queue(guild.id, track_url)
                added_count += 1
            
            # Spusť přehrávání pokud se nic nehraje
            if not vc.is_playing() and added_count > 0:
                await play_next(guild, interaction.channel)
            
            # Shrnutí
            summary = f"✅ **Playlist importován!**\n"
            summary += f"✓ Přidáno: {added_count} skladeb\n"
            if skipped_count > 0:
                summary += f"⊘ Duplikáty přeskočeny: {skipped_count}\n"
            
            mins, secs, total = _estimate_queue_duration(guild.id)
            summary += f"⏱️ Celkový čas fronty: ~{mins}m {secs}s ({total} skladeb)"
            
            await interaction.followup.send(summary)
            
            # ✨ Přidej XP za hudební aktivitu
            if added_count > 0:
                await add_xp_to_user(interaction.user.id, reason="music_command")
        
        except Exception as e:
            print(f"[yt] Playlist error: {e}")
            await interaction.followup.send(f"❌ Chyba při načítání playlistu: {str(e)[:100]}")
    
    else:
        # SINGLE TRACK MODE – Původní v2.4 logika (NEZMĚNÍ SE!)
        try:
            title = "Načítám..."
            # v2.8.1: asyncio.to_thread – blokující yt-dlp extrakce nesmí zaseknout event loop
            extracted = await asyncio.to_thread(ytdlp_extract, url)
            title = extracted.get("title", "Neznámá skladba")
            duration = extracted.get("duration", 180)  # v2.4: ulož dobu trvání
            song_durations[url] = duration
        except Exception as e:
            title = "Chyba při načítání názvu"
            print(f"[yt] Error extracting title: {e}")
        
        # v2.4: Blokace duplicit v frontě
        if _is_url_in_queue(guild.id, url):
            await interaction.followup.send(f"⚠️ **{title}** je už ve frontě! Přeskakuji duplikát.")
            return
        
        _queue_for(guild.id).append({"url": url, "title": title})
        _add_url_to_queue(guild.id, url)  # v2.4: přidej do setu
        
        if not vc.is_playing():
            await play_next(guild, interaction.channel)
            await interaction.followup.send(f"▶️ Začínám přehrávat: **{title}**\n{url}")
        else:
            # v2.4: Ukaž odhad času
            mins, secs, count = _estimate_queue_duration(guild.id)
            duration_str = f" (~{mins}m {secs}s, {count} skladeb v frontě)" if count > 0 else ""
            await interaction.followup.send(f"✅ Přidáno do fronty: **{title}**\n{url}{duration_str}")
            
            # ✨ Přidej XP za hudební aktivitu
            await add_xp_to_user(interaction.user.id, reason="music_command")

@bot.tree.command(name="skip", description="Přeskoč na další skladbu")
async def skip_command(interaction: discord.Interaction):
    """Skip current song."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nic se nehraje!")
            return
        vc.stop()
        await interaction.response.send_message("⏭️ Přeskočeno!")
        
        # ✨ Přidej XP za hudební aktivitu
        await add_xp_to_user(interaction.user.id, reason="music_command")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="pause", description="Pozastav přehrávání")
async def pause_command(interaction: discord.Interaction):
    """Pause playback."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nic se nehraje!")
            return
        vc.pause()
        await interaction.response.send_message("⏸️ Pozastaveno!")
        
        # ✨ Přidej XP za hudební aktivitu
        await add_xp_to_user(interaction.user.id, reason="music_command")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="resume", description="Obnoví přehrávání")
async def resume_command(interaction: discord.Interaction):
    """Resume playback."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc:
            await interaction.response.send_message("❌ Bot není v voice!")
            return
        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Pokračuju!")
            
            # ✨ Přidej XP za hudební aktivitu
            await add_xp_to_user(interaction.user.id, reason="music_command")
        else:
            await interaction.response.send_message("❌ Nic není pozastaveno!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="stop", description="Zastaví přehrávání a vyčistí frontu")
async def stop_command(interaction: discord.Interaction):
    """Stop playback and clear queue."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc:
            await interaction.response.send_message("❌ Bot není v voice!")
            return
        if vc.is_playing():
            vc.stop()
        _queue_for(guild.id).clear()
        _clear_queue_urls(guild.id)  # v2.4: čistit URL set
        now_playing[guild.id] = None
        await interaction.response.send_message("⏹️ Zastaveno! Fronta smazána.")
        
        # ✨ Přidej XP za hudební aktivitu
        await add_xp_to_user(interaction.user.id, reason="music_command")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="leave", description="Opustí voice kanál")
async def leave_command(interaction: discord.Interaction):
    """Leave voice channel."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc:
            await interaction.response.send_message("❌ Bot není v voice!")
            return
        if vc.is_playing():
            vc.stop()
        _queue_for(guild.id).clear()
        now_playing[guild.id] = None
        await vc.disconnect()
        await interaction.response.send_message("👋 Odešel jsem z voice kanálu.")
        
        # ✨ Přidej XP za hudební aktivitu
        await add_xp_to_user(interaction.user.id, reason="music_command")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="np", description="Zobraz právě hranou skladbu")
async def np_command(interaction: discord.Interaction):
    """Show now playing with music controls (icons only)."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nic se nehraje!")
            return
        title = now_playing.get(guild.id, "Unknown")
        embed = discord.Embed(title="🎵 Právě hraje", description=title, color=discord.Color.blue())
        
        # Music control buttons (icons only)
        class MusicControlView(discord.ui.View):
            def __init__(self, guild_id):
                super().__init__(timeout=300)
                self.guild_id = guild_id
            
            @discord.ui.button(label="⏭️", style=discord.ButtonStyle.blurple)
            async def next_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                guild = button_interaction.guild
                vc = discord.utils.get(bot.voice_clients, guild=guild)
                if vc and vc.is_playing():
                    vc.stop()  # Spustí after_play callback který zavolá play_next()
                    await button_interaction.response.defer()
                else:
                    await button_interaction.response.send_message("❌ Nic se nehraje!", ephemeral=True)
            
            @discord.ui.button(label="⏸️", style=discord.ButtonStyle.blurple)
            async def pause_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                guild = button_interaction.guild
                vc = discord.utils.get(bot.voice_clients, guild=guild)
                if vc and vc.is_playing():
                    vc.pause()
                    await button_interaction.response.defer()
                elif vc and vc.is_paused():
                    vc.resume()
                    await button_interaction.response.defer()
                else:
                    await button_interaction.response.send_message("❌ Nic se nehraje!", ephemeral=True)
            
            @discord.ui.button(label="🔀", style=discord.ButtonStyle.blurple)
            async def shuffle_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                guild = button_interaction.guild
                if guild.id in music_queues and len(music_queues[guild.id]) > 1:
                    # Zachovat aktuálně hrající a zamíchat zbytek
                    queue = list(music_queues[guild.id])
                    if len(queue) > 1:
                        current = queue[0]
                        rest = queue[1:]
                        random.shuffle(rest)
                        music_queues[guild.id] = deque([current] + rest)
                    await button_interaction.response.defer()
                else:
                    await button_interaction.response.send_message("❌ Ve frontě méně než 2 skladby!", ephemeral=True)
        
        await interaction.response.send_message(embed=embed, view=MusicControlView(guild.id))
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="queue", description="Zobraz frontu skladeb")
async def queue_command(interaction: discord.Interaction):
    """Show music queue."""
    try:
        guild = interaction.guild
        queue = _queue_for(guild.id)
        if not queue:
            await interaction.response.send_message("❌ Fronta je prázdná!")
            return
        
        # Formatuj frontu s názvy a linky
        items = []
        for i, item in enumerate(list(queue)[:10], 1):
            title = item.get("title", "Neznámá skladba")
            url = item.get("url", "")
            items.append(f"{i}. {title}\n{url}")
        
        description = "\n\n".join(items)
        
        # v2.4: Odhad času trvání
        mins, secs, count = _estimate_queue_duration(guild.id)
        duration_info = f"\n\n⏱️ Odhad: ~{mins}m {secs}s ({count} skladeb)" if count > 0 else ""
        
        embed = discord.Embed(title="🎵 Fronta", description=description + duration_info, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")


@bot.tree.command(name="voicetest", description="Test hlasového připojení")
async def voicetest_command(interaction: discord.Interaction):
    """Test voice connection."""
    await interaction.response.defer()
    guild = interaction.guild
    vc = discord.utils.get(bot.voice_clients, guild=guild)
    if not vc or not vc.is_connected():
        await interaction.followup.send("❌ Bot není v voice kanálu!")
        return
    try:
        # v2.8.1 FIX: `FFmpegOpusAudio` nemá parametr `stdin=` (TypeError při každém volání)
        # a `pipe:` bez zápisu dat by ffmpeg stejně navěky blokovalo. Navíc `anullsrc`
        # je TICHO, ne tón – i kdyby to "fungovalo", nešlo by nic slyšet.
        # Správně: lavfi vstup přímo jako `source` (žádné piping), `sine` = skutečný 440Hz tón.
        source = discord.FFmpegOpusAudio(
            "sine=frequency=440:sample_rate=48000:duration=3",
            before_options="-f lavfi",
            options=get_ffmpeg_options()
        )
        vc.play(source)
        await interaction.followup.send("🔊 Hraju 3 sekundový tón (440Hz)...")
        await asyncio.sleep(3.5)
        if vc.is_playing():
            vc.stop()
        await interaction.followup.send("✅ Voice test úspěšný!")
    except Exception as e:
        await interaction.followup.send(f"❌ Voice test selhalo: {str(e)[:100]}")

@bot.tree.command(name="shuffle", description="Zamíchej frontu (v2.4.1)")
async def shuffle_command(interaction: discord.Interaction):
    """Shuffle music queue while preserving currently playing song."""
    try:
        guild = interaction.guild
        queue = _queue_for(guild.id)
        
        if len(queue) <= 1:
            await interaction.response.send_message("❌ Ve frontě je málo skladeb na zamíchání!")
            return
        
        # Zamíchej frontu
        shuffled = _shuffle_queue(guild.id)
        
        if shuffled:
            # Ukaž prvních pár skladeb po shuffle
            items = []
            for i, item in enumerate(list(queue)[:5], 1):
                title = item.get("title", "Neznámá skladba")[:50]
                items.append(f"{i}. {title}")
            
            items_str = "\n".join(items)
            mins, secs, count = _estimate_queue_duration(guild.id)
            
            embed = discord.Embed(title="🔀 Fronta zamíchána!", description=items_str, color=discord.Color.blue())
            embed.add_field(name="Celkem", value=f"{count} skladeb (~{mins}m {secs}s)", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Chyba při zamíchávání!")
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

# ═══════════════════════════════════════════════════════════════════════════════
#              12. SLASH COMMANDS – OSTATNÍ / OTHER
# ═══════════════════════════════════════════════════════════════════════════════

async def load_verse_streak_from_storage():
    """Načti verse streak z persistent storage (bot_data.json)."""
    global verse_streak
    try:
        db = _load_data()
        if "verse_streak" in db:
            # Konvertuj string keys na int a dates na datetime.date
            streak_data = db["verse_streak"]
            for user_id_str, data in streak_data.items():
                user_id = int(user_id_str)
                last_date = None
                if data.get("last_date"):
                    try:
                        last_date = datetime.datetime.strptime(data["last_date"], "%Y-%m-%d").date()
                    except:
                        last_date = None
                verse_streak[user_id] = {
                    "count": data.get("count", 0),
                    "last_date": last_date
                }
            print(f"[verse] Loaded verse streak for {len(verse_streak)} users")
    except Exception as e:
        print(f"[verse] Failed to load verse streak: {e}")

async def save_verse_streak_to_storage():
    """Ulož verse streak do persistent storage (bot_data.json)."""
    try:
        db = _load_data()
        # Konvertuj datetime.date na string
        streak_data = {}
        for user_id, data in verse_streak.items():
            last_date_str = None
            if data["last_date"]:
                last_date_str = data["last_date"].isoformat()
            streak_data[str(user_id)] = {
                "count": data["count"],
                "last_date": last_date_str
            }
        db["verse_streak"] = streak_data
        await _save_data(db)
    except Exception as e:
        print(f"[verse] Failed to save verse streak: {e}")

async def load_game_activity_from_storage():
    """Načti game activity z persistent storage (bot_data.json)."""
    global game_activity
    try:
        db = _load_data()
        if "game_activity" in db:
            activity_data = db["game_activity"]
            for user_id_str, data in activity_data.items():
                user_id = int(user_id_str)
                last_update = None
                if data.get("last_update"):
                    try:
                        last_update = datetime.datetime.fromisoformat(data["last_update"])
                    except:
                        last_update = datetime.datetime.now()
                else:
                    last_update = datetime.datetime.now()
                
                # Ověř, že games je dict
                games_data = data.get("games", {})
                if not isinstance(games_data, dict):
                    print(f"[game_activity] CHYBA: user {user_id} má poškozená data, resetuji")
                    games_data = {}
                
                game_activity[user_id] = {
                    "games": games_data,
                    "last_update": last_update
                }
            print(f"[game_activity] Loaded game data for {len(game_activity)} users")
    except Exception as e:
        print(f"[game_activity] Failed to load: {e}")

async def save_game_activity_to_storage():
    """Ulož game activity do persistent storage (bot_data.json) - VŽDY KONTROLUJ DATA (v2.7.2)."""
    try:
        db = _load_data()
        activity_data = {}
        error_count = 0
        
        for user_id, data in game_activity.items():
            last_update_str = None
            if data.get("last_update"):
                try:
                    last_update_str = data["last_update"].isoformat()
                except Exception as e:
                    print(f"[game_activity] ⚠️ Chyba při konverzi last_update pro user {user_id}: {e}")
                    last_update_str = datetime.datetime.now().isoformat()
            
            # Validuj games dict
            games_dict = data.get("games", {})
            if not isinstance(games_dict, dict):
                print(f"[game_activity] ❌ User {user_id} má poškozená games data! Resetuji...")
                games_dict = {}
                error_count += 1
            
            # Validuj všechny hodnoty jsou čísla
            clean_games = {}
            for game_name, hours in games_dict.items():
                try:
                    hours_float = float(hours)
                    if hours_float < 0:
                        print(f"[game_activity] ⚠️ Negativní čas {game_name} pro user {user_id}. Resetuji na 0...")
                        clean_games[game_name] = 0
                    else:
                        clean_games[game_name] = hours_float
                except (ValueError, TypeError) as e:
                    print(f"[game_activity] ⚠️ Chybný typ hodin pro {game_name} (user {user_id}): {type(hours)}. Ignoruji...")
                    error_count += 1
                    continue
            
            activity_data[str(user_id)] = {
                "games": clean_games,
                "last_update": last_update_str
            }
        
        db["game_activity"] = activity_data
        await _save_data(db)
        
        if error_count > 0:
            print(f"[game_activity] ℹ️ Opraveno {error_count} chyb při ukládání")
    except Exception as e:
        print(f"[game_activity] ❌ Kritická chyba při ukládání: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                 STATISTICS TRACKING (v2.7.1)
# ═══════════════════════════════════════════════════════════════════════════════

stats_data = {
    # All-time metrics
    "songs_played_total": 0,       # Celkový počet přehraných skladeb
    "xp_total": 0,                  # Celkové XP (všichni hráči)
    "game_hours_total": 0,          # Celkové hodiny her (všichni hráči)
    # Weekly metrics (resetují se každý týden)
    "weekly_songs_played": 0,       # Skladby za tento týden
    "weekly_xp_gained": 0,          # XP získáno tento týden
    "weekly_game_hours": 0,         # Hodiny her tento týden
    "last_weekly_reset": None       # Čas posledního resetu weekly stats
}

# Týdenní hodiny per-user (pro žebříček) - resetuje se každý týden
weekly_user_hours: dict[int, float] = {}

async def load_stats_from_storage():
    """Načti statistiky z bot_data.json (v2.7.1)."""
    global stats_data, weekly_user_hours
    try:
        db = _load_data()
        stats = db.get("stats", {})
        stats_data["songs_played_total"] = stats.get("songs_played_total", 0)
        stats_data["xp_total"] = stats.get("xp_total", 0)
        stats_data["game_hours_total"] = stats.get("game_hours_total", 0)
        stats_data["weekly_songs_played"] = stats.get("weekly_songs_played", 0)
        stats_data["weekly_xp_gained"] = stats.get("weekly_xp_gained", 0)
        stats_data["weekly_game_hours"] = stats.get("weekly_game_hours", 0)
        stats_data["last_weekly_reset"] = stats.get("last_weekly_reset", None)
        
        # Načti weekly_user_hours (v2.7.3)
        saved_weekly_users = db.get("weekly_user_hours", {})
        weekly_user_hours = {int(uid): float(hours) for uid, hours in saved_weekly_users.items()}
        
        print(f"[stats] Loaded: {stats_data['songs_played_total']} songs, {stats_data['xp_total']} total XP, {stats_data['game_hours_total']:.1f}h games, {len(weekly_user_hours)} weekly users")
    except Exception as e:
        print(f"[stats] Error loading stats: {e}")

async def save_stats_to_storage():
    """Ulož statistiky do bot_data.json s validací (v2.7.3)."""
    try:
        db = _load_data()
        
        # Validuj všechny statistiky
        stats_to_save = {
            "songs_played_total": max(0, int(stats_data.get("songs_played_total", 0))),
            "xp_total": max(0, int(stats_data.get("xp_total", 0))),
            "game_hours_total": max(0.0, float(stats_data.get("game_hours_total", 0))),
            "weekly_songs_played": max(0, int(stats_data.get("weekly_songs_played", 0))),
            "weekly_xp_gained": max(0, int(stats_data.get("weekly_xp_gained", 0))),
            "weekly_game_hours": max(0.0, float(stats_data.get("weekly_game_hours", 0))),
            "last_weekly_reset": stats_data.get("last_weekly_reset", None)
        }
        
        db["stats"] = stats_to_save
        
        # Ulož weekly_user_hours (v2.7.3)
        db["weekly_user_hours"] = {str(uid): hours for uid, hours in weekly_user_hours.items()}
        
        await _save_data(db)
    except Exception as e:
        print(f"[stats] ❌ Chyba při ukládání statistik: {e}")

def increment_songs_played_by(count: int):
    """Inkrementuj počet skladeb o zadaný počet (v2.8)."""
    global stats_data
    if count <= 0:
        return
    stats_data["songs_played_total"] += count
    stats_data["weekly_songs_played"] += count
    try:
        asyncio.create_task(save_stats_to_storage())
    except RuntimeError:
        pass

def increment_songs_played():
    """Inkrementuj počet přehraných skladeb (v2.7.1)."""
    increment_songs_played_by(1)

def increment_xp_stats(xp_amount: int):
    """Inkrementuj XP statistiky (v2.7.1)."""
    global stats_data
    stats_data["xp_total"] += xp_amount
    stats_data["weekly_xp_gained"] += xp_amount
    try:
        asyncio.create_task(save_stats_to_storage())
    except RuntimeError:
        pass

def increment_game_hours(hours: float, user_id: int = None):
    """Inkrementuj hodiny her (v2.7.3 - per-user tracking)."""
    global stats_data, weekly_user_hours
    stats_data["game_hours_total"] += hours
    stats_data["weekly_game_hours"] += hours
    
    # Přidej per-user weekly tracking (v2.7.3)
    if user_id is not None:
        if user_id not in weekly_user_hours:
            weekly_user_hours[user_id] = 0.0
        weekly_user_hours[user_id] += hours
    
    try:
        asyncio.create_task(save_stats_to_storage())
    except RuntimeError:
        pass

def reset_weekly_stats():
    """Resetuj všechny weekly stats po týdnu (v2.7.3 - per-user tracking)."""
    global stats_data, weekly_user_hours
    import datetime
    stats_data["weekly_songs_played"] = 0
    stats_data["weekly_xp_gained"] = 0
    stats_data["weekly_game_hours"] = 0
    stats_data["last_weekly_reset"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Reset per-user weekly hours (v2.7.3)
    weekly_user_hours.clear()
    
    try:
        asyncio.create_task(save_stats_to_storage())
    except RuntimeError:
        pass

async def load_user_xp_from_storage():
    """Načti user XP z persistent storage (bot_data.json)."""
    global user_xp
    try:
        db = _load_data()
        if "user_xp" in db:
            xp_data = db["user_xp"]
            for user_id_str, data in xp_data.items():
                user_id = int(user_id_str)
                user_xp[user_id] = {
                    "xp": data.get("xp", 0),
                    "level": data.get("level", "🔰 Učedník")
                }
            print(f"[xp] Loaded XP for {len(user_xp)} users")
    except Exception as e:
        print(f"[xp] Failed to load XP: {e}")

async def save_user_xp_to_storage():
    """Ulož user XP do persistent storage (bot_data.json) s validací (v2.7.2)."""
    try:
        db = _load_data()
        xp_data = {}
        error_count = 0
        
        for user_id, data in user_xp.items():
            xp_value = data.get("xp", 0)
            
            # Validuj XP
            try:
                xp_value = max(0, int(xp_value))
            except (ValueError, TypeError):
                print(f"[xp] ⚠️ Neplatné XP pro user {user_id}: {xp_value}. Resetuji na 0")
                xp_value = 0
                error_count += 1
            
            level = data.get("level", "🔰 Učedník")
            if not isinstance(level, str):
                level = "🔰 Učedník"
            
            xp_data[str(user_id)] = {
                "xp": xp_value,
                "level": level
            }
        
        db["user_xp"] = xp_data
        await _save_data(db)
        
        if error_count > 0:
            print(f"[xp] ℹ️ Opraveno {error_count} chyb")
    except Exception as e:
        print(f"[xp] ❌ Chyba při ukládání XP: {e}")

@bot.tree.command(name="verse", description="Random biblický verš")
async def verse_command(interaction: discord.Interaction):
    """Send random Bible verse with daily streak tracking."""
    try:
        user_id = interaction.user.id
        today = datetime.date.today()
        if user_id not in verse_streak:
            verse_streak[user_id] = {"count": 0, "last_date": None}
        user_streak = verse_streak[user_id]
        if user_streak["last_date"] == today:
            streak_count = user_streak["count"]
            selected = random.choice(verses)
            message = f"📖 Už si dnes vzal verš! Tvoje série: **{streak_count}** dní"
            embed = discord.Embed(title="Biblický Verš", description=selected, color=discord.Color.gold())
            embed.add_field(name="🔥 Série", value=message, inline=False)
            await interaction.response.send_message(embed=embed)
            return
        yesterday = today - datetime.timedelta(days=1)
        if user_streak["last_date"] == yesterday:
            user_streak["count"] += 1
        else:
            user_streak["count"] = 1
        user_streak["last_date"] = today
        streak_count = user_streak["count"]
        milestone_msg = ""
        for days in sorted(streak_messages.keys(), reverse=True):
            if streak_count >= days:
                milestone_msg = f"\n\n🎉 {streak_messages[days]}"
                break
        selected = random.choice(verses)
        embed = discord.Embed(title="📖 Biblický Verš", description=selected, color=discord.Color.gold())
        embed.add_field(name="🔥 Tvoje série", value=f"**{streak_count}** dní\n{milestone_msg}", inline=False)
        await interaction.response.send_message(embed=embed)
        
        # Ulož streak do storage
        await save_verse_streak_to_storage()
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="freegames", description="Free games – Epic Games, Steam, PlayStation Plus")
async def freegames_command(interaction: discord.Interaction):
    """Show free games with individual embeds like PatchBot."""
    await interaction.response.defer()
    try:
        free_games, source_status = get_free_games()
        
        print(f"[freegames] Obtained {len(free_games)} total games")
        print(f"[freegames] Source status: {source_status}")
        
        if not free_games:
            await interaction.followup.send("❌ Žádné zdarma hry nenalezeny")
            return
        
        # Oddělení her od PSN článků
        regular_games = [g for g in free_games if "playstation" not in g.get("source", "").lower()]
        psn_articles = [g for g in free_games if "playstation" in g.get("source", "").lower()]
        
        print(f"\n[DEBUG COMMAND] Regular games: {len(regular_games)}, PSN articles: {len(psn_articles)}")
        print(f"[DEBUG COMMAND] Regular games sources:")
        for i, g in enumerate(regular_games):
            print(f"  {i+1}. {g.get('source', 'N/A')}: {g.get('title', 'N/A')}")
        
        for i, g in enumerate(regular_games[:5]):
            print(f"  Game {i+1}: {g.get('title', 'N/A')} from {g.get('source', 'N/A')}")
        
        # Pošli max 10 her (aby to nebyl spam)
        sent = 0
        for game in regular_games[:10]:
            try:
                title = game.get("title", "Unknown")
                url = game.get("url", "")
                source = game.get("source", "Unknown")
                image = game.get("image", "")
                original_price = game.get("original_price", "N/A")
                expire_date = game.get("expire_date", "")
                release_date = game.get("release_date", "N/A")
                reviews = game.get("reviews", "N/A")
                platforms = game.get("platforms", "N/A")
                
                # Urči barvu podle zdroje
                if "epic" in source.lower():
                    color = discord.Color.from_rgb(75, 0, 130)
                    logo = "🟣"
                elif "steam" in source.lower():
                    color = discord.Color.from_rgb(0, 0, 0)
                    logo = "🎮"
                elif "gog" in source.lower():
                    color = discord.Color.from_rgb(255, 215, 0)
                    logo = "⭐"
                elif "amazon" in source.lower() or "prime" in source.lower():
                    color = discord.Color.from_rgb(255, 153, 0)
                    logo = "🔶"
                else:
                    color = discord.Color.purple()
                    logo = "🎁"
                
                # Vytvoř embed s emoji logem v titulu
                embed = discord.Embed(
                    title=f"{logo} {title}",
                    url=url,
                    color=color,
                    description=source
                )
                
                # Přidej logo platformy jako thumbnail (vpravo nahoře)
                logo_url = get_platform_logo_url(source)
                print(f"[freegames] Logo for {source}: {logo_url}")
                if logo_url and isinstance(logo_url, str) and len(logo_url) > 10 and logo_url.startswith("http"):
                    try:
                        embed.set_thumbnail(url=logo_url)
                        print(f"[freegames] ✅ Logo set for {source}")
                    except Exception as e:
                        print(f"[freegames] ❌ Logo URL error for {source}: {e}")
                
                # Cena a Datum vydání vedle sebe
                price_text = format_price_display(original_price)
                embed.add_field(name="💰 Price:", value=price_text, inline=True)
                
                if release_date and release_date != "N/A" and release_date != "TBA":
                    embed.add_field(name="📅 Release Date:", value=release_date, inline=True)
                
                # Posted info
                if expire_date:
                    embed.add_field(name="⏰ Posted:", value=expire_date, inline=True)
                
                # Hodnocení pouze pro Epic Games a PS Plus, ne pro Steam
                if reviews and reviews != "N/A" and "reddit" not in source.lower():
                    embed.add_field(name="All Reviews:", value=reviews, inline=True)
                
                # Obrázek dolů (full-width)
                if image:
                    embed.set_image(url=image)
                
                embed.set_footer(text=f"Click to view on {source}")
                
                await interaction.followup.send(embed=embed)
                sent += 1
            except Exception as e:
                print(f"[freegames] Error sending game embed: {e}")
                continue
        
        # Pošli všechny PSN články dohromady v jednom embedu
        if psn_articles:
            try:
                # Vytvoř seznam PSN článků s links
                psn_list = ""
                for article in psn_articles[:8]:
                    title = article.get("title", "Unknown")
                    url = article.get("url", "")
                    # Zkrátit dlouhé názvy
                    if len(title) > 70:
                        title = title[:67] + "..."
                    psn_list += f"• [{title}]({url})\n"
                
                # Vezmi obrázek z dat - už ho máme z RSS feedu
                featured_image = psn_articles[0].get("image", "") if psn_articles else ""
                
                # Vytvoř embed
                embed = discord.Embed(
                    title="🎯 PlayStation Plus",
                    color=discord.Color.from_rgb(0, 112, 209),
                    description=psn_list
                )
                
                # Obrázek jen když existuje (bez fallback loga)
                if featured_image:
                    embed.set_image(url=featured_image)
                
                # Vezmi data z prvního článku (všechny mají stejné)
                first_article = psn_articles[0] if psn_articles else {}
                original_price = first_article.get("original_price", "FREE")
                release_date = first_article.get("release_date", "Monthly Update")
                
                # Stejné pole jako u ostatních her
                price_text = format_price_display(original_price)
                embed.add_field(name="💰 Price:", value=price_text, inline=True)
                
                if release_date and release_date != "N/A":
                    embed.add_field(name="📅 Release Date:", value=release_date, inline=True)
                
                embed.add_field(name="👥 Status:", value="For PS+ members", inline=True)
                embed.add_field(name="💻 Platforms:", value="PlayStation", inline=True)
                embed.set_footer(text=f"{len(psn_articles)} items • Click titles to view")
                
                await interaction.followup.send(embed=embed)
                sent += 1
            except Exception as e:
                print(f"[freegames] Error sending PSN embed: {e}")
        
        print(f"[freegames] Sent {sent} items total")
        
    except Exception as e:
        print(f"[freegames] Command error: {type(e).__name__}: {e}")
        try:
            await interaction.followup.send(f"❌ Chyba: {str(e)[:100]}")
        except Exception as send_error:
            print(f"[freegames] Failed to send error message: {send_error}")


@bot.tree.command(name="bless", description="Požehnání pro uživatele")
async def bless_command(interaction: discord.Interaction, user: discord.User = None):
    """Send blessing to user."""
    try:
        target = user or interaction.user
        all_blessings = list(game_blessings.values()) + [
            f"🙏 {target.mention}, Bůh tě požehná v každém kroku!",
            f"✝️ {target.mention}, síla a láska Boží jsou s tebou!",
            f"💫 {target.mention}, přeji ti pokoj a radost v Kristu!",
        ]
        selected = random.choice(all_blessings)
        if target.mention not in selected:
            selected = f"{target.mention}, {selected}"
        embed = discord.Embed(description=selected, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="version", description="Verze bota a info")
async def version_command(interaction: discord.Interaction):
    """Show bot version and changelog."""
    try:
        embed = discord.Embed(
            title="ℹ️ Ježíš Discord Bot – v2.8.2",
            description="Voice & Player Client Hotfix",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="⏱️ Version",
            value="v2.8.2\nVoice & Player Client Hotfix",
            inline=True
        )

        embed.add_field(
            name="📅 Release",
            value="2026-08-26",
            inline=True
        )
        
        embed.add_field(
            name="🎵 Music Features",
            value="""🎵 YouTube & Playlist support
📊 Queue duration estimate
🚫 Duplicate blocking""",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Gaming & XP",
            value="""⭐ XP system s levely
🎯 Minihry (kviz, duel)
🔥 Verse streak tracking
📈 Game activity logging""",
            inline=True
        )
        
        embed.add_field(
            name="📊 v2.7 Analytics (NEW)",
            value="""🏆 `/leaderboard` – Top 10 hráči
📊 `/serverstats` – Server aktivita
📈 `/profile` – Tvůj profil
📅 `/weeklysummary` – Týdenní trend""",
            inline=True
        )
        
        embed.add_field(
            name="🎁 Free Games",
            value="""🟣 Epic Games
🎮 Steam (Reddit)
🎪 PlayStation Plus""",
            inline=True
        )

        embed.add_field(
            name="🔧 v2.8.2 Bugfixy (NEW)",
            value="""🔊 Voice spojení opraveno (DAVE/discord.py 2.7.1)
🎥 yt-dlp player klienti – zpět na auto-výběr
⚡ Přehrávání už neblokuje celého bota
🩺 `/diag` – živý yt-dlp self-test""",
            inline=True
        )

        embed.add_field(
            name="📚 Dokumentace",
            value="[GitHub](https://github.com/Braska-botmaker/Chatbot-discord-JESUS) | [Docs](https://github.com/Braska-botmaker/Chatbot-discord-JESUS/tree/main/docs)",
            inline=False
        )
        
        embed.set_footer(text="🙏 Jesus Bot – Made with ❤️")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}")

@bot.tree.command(name="commands", description="Zobraz všechny dostupné příkazy")
async def commands_command(interaction: discord.Interaction):
    """Show all available commands organized by category."""
    try:
        # Embed 1: Music & Voice
        embed1 = discord.Embed(
            title="🎵 HUDBA & VOICE",
            color=discord.Color.blurple(),
            description="Příkazy pro přehrávání hudby a voice chat"
        )
        
        embed1.add_field(
            name="/yt <url>",
            value="Přidej skladbu nebo playlist do fronty\n🆙 **+1-2 XP**",
            inline=False
        )
        embed1.add_field(
            name="/skip | /pause | /resume | /stop",
            value="Ovládání přehrávání\n🆙 **+1-2 XP za skip**",
            inline=False
        )
        embed1.add_field(
            name="/np | /queue",
            value="Zobraz právě hrající skladbu / frontu",
            inline=False
        )
        embed1.add_field(
            name="/shuffle | /leave | /voicetest",
            value="Zamíchej frontu / Odejdi / Ověř voice\n🆙 **+1-2 XP za shuffle**",
            inline=False
        )
        
        # Embed 2: Bible & Minigames
        embed2 = discord.Embed(
            title="📖 BIBLE & MINIHRY",
            color=discord.Color.purple(),
            description="Biblické příkazy a interaktivní minihry"
        )
        
        embed2.add_field(
            name="/verse",
            value="Náhodný biblický verš",
            inline=False
        )
        embed2.add_field(
            name="/bless [@user]",
            value="Požehnání pro hráče (1h cooldown)",
            inline=False
        )
        embed2.add_field(
            name="/biblicquiz",
            value="Biblický trivia kviz – 10 otázek\n🆙 **+1-2 XP za vítězství**",
            inline=False
        )
        embed2.add_field(
            name="/versfight @user",
            value="Veršový duel s jiným hráčem\n🆙 **+15 XP za vítězství**",
            inline=False
        )
        embed2.add_field(
            name="/rollblessing",
            value="RNG požehnání hra (1h cooldown)\n🆙 **+5 XP za vítězství**",
            inline=False
        )
        
        # Embed 3: Analytics (NEW v2.7)
        embed3 = discord.Embed(
            title="📊 SERVER ANALYTICS (v2.7 NEW)",
            color=discord.Color.green(),
            description="Statistiky a leaderboardy serveru"
        )
        
        embed3.add_field(
            name="/serverstats",
            value="Přehled serverových aktivit\n👥 Uživatelé | ⭐ XP | 🎵 Hudba | 🏆 Top hry",
            inline=False
        )
        embed3.add_field(
            name="/leaderboard",
            value="Top 10 hráčů podle XP\n📊 Level | 🔥 Verse Streak | 🏆 Pořadí",
            inline=False
        )
        embed3.add_field(
            name="/profile",
            value="Tvůj osobní profil\n⭐ XP & Level | 🔥 Streak | 🎯 Top hry | 🏅 Dosažení",
            inline=False
        )
        embed3.add_field(
            name="/weeklysummary",
            value="Týdenní shrnutí\n📅 Poslední 7 dní | ⏱️ Čas hrání | 🏆 Top hráči týdne",
            inline=False
        )
        
        # Embed 4: Other
        embed4 = discord.Embed(
            title="🎁 OSTATNÍ & ADMIN",
            color=discord.Color.orange(),
            description="Další příkazy a nastavení"
        )
        
        embed4.add_field(
            name="/freegames",
            value="Hry zdarma z 3 zdrojů\n🟣 Epic Games | 🎮 Steam | 🎪 PlayStation Plus",
            inline=False
        )
        embed4.add_field(
            name="/setchannel <typ> <kanál>",
            value="Nastav kanál pro požehnání nebo hry (ADMIN)",
            inline=False
        )
        embed4.add_field(
            name="/config",
            value="Zobraz konfiguraci serveru (ADMIN)",
            inline=False
        )
        embed4.add_field(
            name="/diag",
            value="Diagnostika bota (Debug info)",
            inline=False
        )
        
        embed4.add_field(
            name="/version",
            value="Info o verzi bota",
            inline=False
        )
        
        embed4.add_field(
            name="/commands",
            value="Tento seznam příkazů",
            inline=False
        )
        
        # Send all embeds
        await interaction.response.send_message(embeds=[embed1, embed2, embed3, embed4])
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="diag", description="Diagnostika bota")
async def diag_command(interaction: discord.Interaction):
    """Show bot diagnostics."""
    await interaction.response.defer()
    embed = discord.Embed(title="🩺 Diagnostika", color=discord.Color.green())
    machine = platform.machine()
    is_rpi = _is_arm_system()
    embed.add_field(name="💻 System", value=f"Machine: {machine}\nARM: {'✅' if is_rpi else '❌'}", inline=True)
    ffmpeg_ok = "✅" if has_ffmpeg() else "❌"
    opus_ok = "✅" if HAS_OPUS else "❌"
    nacl_ok = "✅" if HAS_NACL else "❌"
    embed.add_field(name="🔊 Audio", value=f"FFmpeg: {ffmpeg_ok}\nOpus: {opus_ok}\nNaCl: {nacl_ok}", inline=True)
    voice_count = len(bot.voice_clients)
    embed.add_field(name="🎤 Voice", value=f"Connected: {voice_count}", inline=True)
    if bot.user:
        embed.add_field(name="⏱️ Version", value="v2.8.2\nVoice & Player Client Hotfix", inline=True)

    # v2.8.1: Živý test yt-dlp/YouTube extrakce – nejrychlejší způsob, jak zjistit
    # jestli je problém v zastaralém yt-dlp, nebo jinde.
    yt_dlp_version = "❌ Nenačteno"
    yt_test = "⚠️ Neotestováno"
    try:
        if _yt_dlp:
            yt_dlp_version = getattr(_yt_dlp.version, "__version__", "?")
            test_info = await asyncio.to_thread(ytdlp_extract, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            yt_test = f"✅ OK ({test_info.get('title', '?')[:40]})"
    except Exception as e:
        yt_test = f"❌ {str(e)[:150]}"
    embed.add_field(name="🎥 yt-dlp", value=f"Verze: {yt_dlp_version}\nTest: {yt_test}\nKlienti: {', '.join(YTDLP_PLAYER_CLIENTS)}", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="setchannel", description="Nastav kanál pro požehnání nebo hry zdarma")
@app_commands.choices(type=[
    app_commands.Choice(name="Blessings 🙏", value="blessing"),
    app_commands.Choice(name="Free games 💵", value="freegames"),
])
async def setchannel_command(interaction: discord.Interaction, type: str, channel: discord.TextChannel):
    """Nastav channel pro specifický účel (v2.5 – Channel Config Pack)."""
    try:
        # Kontroluj, že je uživatel admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an administrator!")
            return
        
        # Ulož konfiguraci do bot_data.json
        db = _load_data()
        await _save_guild_config_to_db(db, interaction.guild.id, type, channel.id)
        
        # Potvrzení
        type_name = {"blessing": "Blessings", "freegames": "Free Games"}.get(type, type)
        embed = discord.Embed(
            title="✅ Channel set!",
            description=f"**{type_name}** → {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        print(f"[config] Guild {interaction.guild.id}: {type} → {channel.id} (saved)")
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}")

@bot.tree.command(name="config", description="Zobraz konfiguraci serveru")
async def config_command(interaction: discord.Interaction):
    """Show current server configuration (v2.5 – Channel Config Pack)."""
    try:
        # Kontroluj, že je uživatel admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an administrator!")
            return
        
        # Načti konfiguraci z bot_data.json
        db = _load_data()
        config = _get_guild_all_config(db, interaction.guild.id)
        
        # Přeformátuj na jména kanálů
        blessing_channel = interaction.guild.get_channel(config.get("blessing_channel"))
        freegames_channel = interaction.guild.get_channel(config.get("freegames_channel"))
        
        blessing_str = f"✅ {blessing_channel.mention}" if blessing_channel else "❌ Not set"
        freegames_str = f"✅ {freegames_channel.mention}" if freegames_channel else "❌ Not set"
        
        embed = discord.Embed(
            title="⚙️ Server Configuration",
            color=discord.Color.blue()
        )
        embed.add_field(name="🙏 Blessings", value=blessing_str, inline=False)
        embed.add_field(name="💵 Free Games", value=freegames_str, inline=False)
        embed.add_field(
            name="💡 Tip",
            value="Use `/setchannel` to change channels",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}")

# ═══════════════════════════════════════════════════════════════════════════════
#                13. SCHEDULED TASKS – AUTOMATICKÉ ZPRÁVY
# ═══════════════════════════════════════════════════════════════════════════════

@tasks.loop(minutes=5)
async def track_game_activity_periodic():
    """Měř čas hry každých 5 minut pro všechny online hráče (v2.7.2 s error handlingem)."""
    try:
        error_count = 0
        success_count = 0
        
        for guild in bot.guilds:
            try:
                for member in guild.members:
                    try:
                        if member.bot or member.status != discord.Status.online:
                            continue
                        
                        # Pokud hraje hru, zaznamenej čas
                        if member.activity and member.activity.type == discord.ActivityType.playing:
                            track_user_activity(member)
                            success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"[track_periodic] ⚠️ Chyba pro {member}: {e}")
            except Exception as e:
                print(f"[track_periodic] ⚠️ Chyba v guild {guild.name}: {e}")
        
        # Ulož data do storage po každém updatu
        try:
            await save_game_activity_to_storage()
        except Exception as e:
            print(f"[track_periodic] ❌ Chyba při ukládání game_activity: {e}")
        
        # Ulož také XP data (bezpečnost - nechceme ztratit XP pokud se bot spadne)
        try:
            await save_user_xp_to_storage()
        except Exception as e:
            print(f"[track_periodic] ❌ Chyba při ukládání user_xp: {e}")
        
        if error_count > 0:
            print(f"[track_periodic] ℹ️ Zpracováno: {success_count} OK, {error_count} chyb")
    except Exception as e:
        print(f"[track_periodic] ❌ Kritická chyba: {e}")

@track_game_activity_periodic.before_loop
async def before_track_periodic():
    await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def send_morning_message():
    """Odeslat ranní zprávu v 09:00 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 9 and now.minute == 0:
        for guild in bot.guilds:
            # v2.5: Použij nový config system s fallbackem na staré hledání
            channel = _get_channel_for_type(guild, "blessing")
            if channel:
                verse = random.choice(verses)
                embed = discord.Embed(title="🌅 Dobré ráno!", description="Nechť tě Bůh požehná v novém dni!", color=discord.Color.orange())
                embed.add_field(name="📖 Dnešní verš", value=verse, inline=False)
                try:
                    await channel.send(embed=embed)
                    print(f"[morning] Sent to {guild.name}")
                except Exception as e:
                    print(f"[morning] Error in {guild.name}: {e}")

@tasks.loop(minutes=1)
async def send_night_message():
    """Odeslat noční zprávu v 22:00 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 22 and now.minute == 0:
        for guild in bot.guilds:
            # v2.5: Použij nový config system s fallbackem na staré hledání
            channel = _get_channel_for_type(guild, "blessing")
            if channel:
                embed = discord.Embed(title="🌙 Dobrou noc!", description="Spi v pokoji Kristově. Zítřka tě čeká nový den plný příležitostí.", color=discord.Color.dark_blue())
                try:
                    await channel.send(embed=embed)
                    print(f"[night] Sent to {guild.name}")
                except Exception as e:
                    print(f"[night] Error in {guild.name}: {e}")

@tasks.loop(minutes=1)
async def send_free_games():
    """Odeslat zdarma hry v 20:10 CET – stejné jako /freegames."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 20 and now.minute == 10:
        for guild in bot.guilds:
            channel = _get_channel_for_type(guild, "freegames")
            if not channel:
                continue
            
            try:
                free_games, source_status = get_free_games()
                
                if not free_games:
                    try:
                        await channel.send("❌ Žádné zdarma hry nenalezeny")
                    except Exception as e:
                        print(f"[send_free_games] Error sending empty message: {e}")
                    continue
                
                # Oddělení her od PSN článků
                regular_games = [g for g in free_games if "playstation" not in g.get("source", "").lower()]
                psn_articles = [g for g in free_games if "playstation" in g.get("source", "").lower()]
                
                # Pošli max 10 regulárních her (aby to nebyl spam)
                sent = 0
                for game in regular_games[:10]:
                    try:
                        title = game.get("title", "Unknown")
                        url = game.get("url", "")
                        source = game.get("source", "Unknown")
                        image = game.get("image", "")
                        original_price = game.get("original_price", "N/A")
                        expire_date = game.get("expire_date", "")
                        release_date = game.get("release_date", "N/A")
                        reviews = game.get("reviews", "N/A")
                        platforms = game.get("platforms", "N/A")
                        
                        # Urči barvu podle zdroje
                        if "epic" in source.lower():
                            color = discord.Color.from_rgb(75, 0, 130)
                            logo = "🟣"
                        elif "steam" in source.lower():
                            color = discord.Color.from_rgb(0, 0, 0)
                            logo = "🎮"
                        elif "gog" in source.lower():
                            color = discord.Color.from_rgb(255, 215, 0)
                            logo = "⭐"
                        elif "amazon" in source.lower() or "prime" in source.lower():
                            color = discord.Color.from_rgb(255, 153, 0)
                            logo = "🔶"
                        else:
                            color = discord.Color.purple()
                            logo = "🎁"
                        
                        # Vytvoř embed s emoji logem v titulu
                        embed = discord.Embed(
                            title=f"{logo} {title}",
                            url=url,
                            color=color,
                            description=source
                        )
                        
                        # Přidej logo platformy jako thumbnail (vpravo nahoře)
                        logo_url = get_platform_logo_url(source)
                        if logo_url and isinstance(logo_url, str) and len(logo_url) > 10 and logo_url.startswith("http"):
                            try:
                                embed.set_thumbnail(url=logo_url)
                            except Exception as e:
                                print(f"[send_free_games] Logo URL error for {source}: {e}")
                        
                        # Cena a Datum vydání vedle sebe
                        price_text = format_price_display(original_price)
                        embed.add_field(name="💰 Price:", value=price_text, inline=True)
                        
                        if release_date and release_date != "N/A" and release_date != "TBA":
                            embed.add_field(name="📅 Release Date:", value=release_date, inline=True)
                        
                        # Posted info
                        if expire_date:
                            embed.add_field(name="⏰ Posted:", value=expire_date, inline=True)
                        
                        # Hodnocení pouze pro Epic Games a PS Plus, ne pro Steam
                        if reviews and reviews != "N/A" and "reddit" not in source.lower():
                            embed.add_field(name="All Reviews:", value=reviews, inline=True)
                        
                        # Obrázek dolů (full-width)
                        if image:
                            embed.set_image(url=image)
                        
                        embed.set_footer(text=f"Click to view on {source}")
                        
                        await channel.send(embed=embed)
                        sent += 1
                    except Exception as e:
                        print(f"[send_free_games] Error sending game embed: {e}")
                        continue
                
                # Pošli všechny PSN články dohromady v jednom embedu
                if psn_articles:
                    try:
                        # Vytvoř seznam PSN článků s links
                        psn_list = ""
                        for article in psn_articles[:8]:
                            title = article.get("title", "Unknown")
                            url = article.get("url", "")
                            # Zkrátit dlouhé názvy
                            if len(title) > 70:
                                title = title[:67] + "..."
                            psn_list += f"• [{title}]({url})\n"
                        
                        # Vezmi obrázek z dat - už ho máme z RSS feedu
                        featured_image = psn_articles[0].get("image", "") if psn_articles else ""
                        
                        # Vytvoř embed
                        embed = discord.Embed(
                            title="🎯 PlayStation Plus",
                            color=discord.Color.from_rgb(0, 112, 209),
                            description=psn_list
                        )
                        
                        # Obrázek jen když existuje (bez fallback loga)
                        if featured_image:
                            embed.set_image(url=featured_image)
                        
                        # Vezmi data z prvního článku
                        first_article = psn_articles[0] if psn_articles else {}
                        ps_original_price = first_article.get("original_price", "FREE")
                        ps_release_date = first_article.get("release_date", "Monthly Update")
                        
                        # Stejné pole jako u ostatních her
                        ps_price_text = format_price_display(ps_original_price)
                        embed.add_field(name="💰 Price:", value=ps_price_text, inline=True)
                        
                        if ps_release_date and ps_release_date != "N/A":
                            embed.add_field(name="📅 Release Date:", value=ps_release_date, inline=True)
                        
                        embed.add_field(name="👥 Status:", value="For PS+ members", inline=True)
                        embed.add_field(name="💻 Platforms:", value="PlayStation", inline=True)
                        embed.set_footer(text=f"{len(psn_articles)} items • Click titles to view")
                        
                        await channel.send(embed=embed)
                        sent += 1
                    except Exception as e:
                        print(f"[send_free_games] Error sending PSN embed: {e}")
                
                print(f"[send_free_games] Sent {sent} items to {guild.name}")
                
            except Exception as e:
                print(f"[send_free_games] Error in {guild.name}: {type(e).__name__}: {e}")
                try:
                    await channel.send(f"⚠️ Chyba: {str(e)[:100]}")
                except Exception as send_error:
                    print(f"[send_free_games] Failed to send error in {guild.name}: {send_error}")

@tasks.loop(minutes=5)
async def voice_watchdog():
    """Monitoruj voice connections."""
    for guild_id, vc in list((vc.guild.id, vc) for vc in bot.voice_clients):
        if not vc.is_connected():
            _queue_for(guild_id).clear()
            now_playing[guild_id] = None

@tasks.loop(seconds=5)
async def update_bot_presence():
    """Aktualizuj bot's presence (status) - když hraje hudbu vs. normální stav."""
    try:
        # Zkontroluj, jestli nějaký voice client hraje hudbu
        is_playing_music = False
        
        for vc in bot.voice_clients:
            if vc.is_playing():
                is_playing_music = True
                break
        
        # Nastav presence podle stavu
        if is_playing_music:
            # Playing music
            activity = discord.Activity(type=discord.ActivityType.listening, name="/yt")
            await bot.change_presence(status=discord.Status.online, activity=activity)
        else:
            # Default status
            activity = discord.Activity(type=discord.ActivityType.watching, name="JESUS /commands")
            await bot.change_presence(status=discord.Status.online, activity=activity)
    
    except Exception as e:
        print(f"[presence] Error updating presence: {e}")

@tasks.loop(hours=1)
async def clear_recent_announcements():
    """Vyčisti staré oznámení každou hodinu."""
    global recently_announced_games
    recently_announced_games.clear()

@tasks.loop(minutes=1)
async def send_weekly_summary():
    """Pošli týdenní shrnutí aktivit do configured kanálu (v2.7.3) – každou neděli v 19:00 CET."""
    global stats_data, weekly_user_hours
    import datetime as dt
    
    try:
        # Kontrola: spusť pouze v neděli v 19:00 CET
        now_cet = dt.datetime.now(pytz.timezone("Europe/Prague"))
        # 6 = Sunday, hour = 19, minute = 0
        if not (now_cet.weekday() == 6 and now_cet.hour == 19 and now_cet.minute == 0):
            return
        
        print("[weekly_summary] 🔄 Spouštím týdenní shrnutí...")
        
        # ✅ Ulož všechny weekly stats PŘED resetem (ochrana dat)
        weekly_songs = max(0, stats_data.get('weekly_songs_played', 0))
        weekly_xp = max(0, stats_data.get('weekly_xp_gained', 0))
        weekly_hours = max(0.0, stats_data.get('weekly_game_hours', 0.0))
        
        now = dt.datetime.now(dt.timezone.utc)
        
        # v2.7.3: Použij weekly_user_hours pro správná týdenní data per-user
        # Tato data se sbírají průběžně během týdne a resetují se po odeslání
        weekly_users = {uid: hours for uid, hours in weekly_user_hours.items() if hours > 0}
        
        print(f"[weekly_summary] 📊 Týdenní data: {weekly_hours:.1f}h celkem, {len(weekly_users)} aktivních hráčů")
        
        # Top hráči týdne (seřazeno podle skutečných týdenních hodin)
        top_weekly = sorted(weekly_users.items(), key=lambda x: x[1], reverse=True)[:5]
        
        sent_count = 0
        error_count = 0
        
        # Pošli do všech serverů do configured blessing channelu
        for guild in bot.guilds:
            try:
                # Najdi blessing channel
                channel = _get_channel_for_type(guild, "blessing")
                if not channel:
                    print(f"[weekly_summary] ⚠️ {guild.name}: Žádný blessing kanál")
                    continue
                
                # Build embed
                embed = discord.Embed(
                    title="📅 **Týdenní Shrnutí Aktivit – v2.7.2**",
                    description=f"Období: {(now - dt.timedelta(days=7)).strftime('%d.%m')} – {now.strftime('%d.%m.%Y')}",
                    color=discord.Color.orange()
                )
                
                # Přidej statistiky
                embed.add_field(
                    name="⏱️ Čas hrání",
                    value=f"**{weekly_hours:.1f}** h",
                    inline=True
                )
                
                embed.add_field(
                    name="⭐ XP v týdnu",
                    value=f"**{weekly_xp:,}** XP",
                    inline=True
                )
                
                embed.add_field(
                    name="🎵 Skladby",
                    value=f"**{weekly_songs}** skladeb",
                    inline=True
                )
                
                # Top hráči
                if top_weekly:
                    top_str = ""
                    for idx, (user_id, playtime) in enumerate(top_weekly, 1):
                        try:
                            user = await bot.fetch_user(user_id)
                            username = user.name
                        except Exception as e:
                            username = f"User {user_id}"
                            print(f"[weekly_summary] ⚠️ Nemohl jsem fetch user {user_id}: {e}")
                        
                        # Ověř že playtime je číslo
                        if isinstance(playtime, (int, float)) and playtime > 0:
                            top_str += f"{idx}. **{username}** – {playtime:.1f}h\n"
                    
                    if top_str:
                        embed.add_field(name="🏆 Top hráči týdne", value=top_str, inline=False)
                    else:
                        embed.add_field(name="🏆 Top hráči týdne", value="Žádní hráči v datech", inline=False)
                else:
                    embed.add_field(name="🏆 Top hráči týdne", value="Žádná data dostupná", inline=False)
                
                embed.set_footer(text="v2.7.3 Weekly Summary | Jesus Bot")
                
                await channel.send(embed=embed)
                sent_count += 1
                print(f"[weekly_summary] ✅ Poslán {guild.name}")
                
            except discord.Forbidden:
                error_count += 1
                print(f"[weekly_summary] ❌ {guild.name}: Nemám práva na psaní")
            except Exception as e:
                error_count += 1
                print(f"[weekly_summary] ❌ {guild.name}: {e}")
        
        # ✅ Reset všech weekly stats PO odeslání všech zpráv (ochrana – jen pokud se podařilo)
        if sent_count > 0:
            reset_weekly_stats()
            print(f"[weekly_summary] ✅ RESET: Odesláno {sent_count}/{len(bot.guilds)} serverů (chyby: {error_count}) | All-time: {stats_data['songs_played_total']} songs, {stats_data['xp_total']} XP, {stats_data['game_hours_total']:.1f}h")
        else:
            print(f"[weekly_summary] ⚠️ Žádný server nebyl zpracován!")
    
    except Exception as e:
        print(f"[weekly_summary] ❌ KRITICKÁ CHYBA: {e}")

@send_weekly_summary.before_loop
async def before_weekly_summary():
    """Čekej na ready před spuštěním weekly summary."""
    await bot.wait_until_ready()

@send_morning_message.before_loop
async def before_morning():
    await bot.wait_until_ready()

@send_night_message.before_loop
async def before_night():
    await bot.wait_until_ready()

@send_free_games.before_loop
async def before_free_games():
    await bot.wait_until_ready()

@voice_watchdog.before_loop
async def before_watchdog():
    await bot.wait_until_ready()

@update_bot_presence.before_loop
async def before_presence():
    await bot.wait_until_ready()

@clear_recent_announcements.before_loop
async def before_clear():
    await bot.wait_until_ready()

# ═══════════════════════════════════════════════════════════════════════════════
#                15. GAME PRESENCE TRACKING – AUTOMATICKÉ BLESSINGS
# ═══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_presence_update(before, after):
    """Detekuj, kdy uživatel začne/skončí hrát hru a odeslij požehnání."""
    def is_game_activity(activity):
        return activity.type == discord.ActivityType.playing

    # Přeskoč guild nebo bot users
    if not after.guild or after.bot:
        return

    before_game = next((a for a in before.activities if is_game_activity(a)), None)
    after_game = next((a for a in after.activities if is_game_activity(a)), None)

    # Hra začala
    if before_game is None and after_game is not None:
        game_name = after_game.name
        print(f"[presence] {after.name} started playing: {game_name}")
        
        # V2.3.1 TRACKING: Zaznamenej hry JEN když hra ZAČNE (reset_on_new_game=True!)
        # Tímto způsobem resetujeme last_update a NEpočítáme čas od staré aktualizace
        track_user_activity(after, reset_on_new_game=True)
        await assign_game_roles(after)
        
        # Zkontroluj game blessing cooldown (1 hodina na hru)
        # Pokud je hra na cooldownu, neposílej blessing
        if not _can_send_game_blessing(after.id, game_name):
            print(f"[presence] {game_name} blessing na cooldownu pro {after.name}, přeskakuji")
            return
        
        # Vyber blessing
        if game_name in game_blessings:
            blessing = game_blessings[game_name]
        else:
            # Fallback na náhodný generický blessing
            blessing = random.choice([
                "Bůh tě provede hraním a dej to všechno!",
                "Zábava s vírou – ať ti to jde!",
                "Vychutnej si hru a bůh tě chrání!",
            ])
        
        # Najdi kanál a odeslij blessing
        # v2.5: Použij nový config system s fallbackem na staré hledání
        channel = _get_channel_for_type(after.guild, "blessing")
        if channel and channel.permissions_for(after.guild.me).send_messages:
            msg = f"{after.name} právě hraje **{game_name}**. {blessing}"
            embed = discord.Embed(description=msg, color=discord.Color.gold())
            print(f"[presence] Sending to {channel.name}: {msg}")
            try:
                await channel.send(embed=embed)
                print(f"[presence] Message sent!")
            except Exception as send_err:
                print(f"[presence] Failed to send: {send_err}")
        else:
            print(f"[presence] Channel 'blessing' not found or no permissions")
    
    # Hra skončila
    elif before_game is not None and after_game is None:
        print(f"[presence] {after.name} stopped playing: {before_game.name}")

# ═══════════════════════════════════════════════════════════════════════════════
#                 13b. VOICE STATE UPDATE – XP ZA VOICE AKTIVITU
# ═══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_voice_state_update(member, before, after):
    """Detekuj voice aktivitu a přiděluj XP když bot hraje hudbu."""
    # Přeskoč boty
    if member.bot:
        return
    
    guild = member.guild
    
    # Uživatel se připojil k voice kanálu
    if before.channel is None and after.channel is not None:
        # Čekej chvíli aby se bot připojil
        await asyncio.sleep(1)
        
        # Zjisti jestli bot v tom kanálu hraje hudbu
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if vc and vc.is_connected() and vc.channel == after.channel and vc.is_playing():
            # ✨ Přidej XP za voice aktivitu s aktivním botem
            success = await add_xp_to_user(member.id, reason="voice_active")
            if success:
                print(f"[xp] Voice: {member.name} +XP pro aktivitu s music botem")

# ═══════════════════════════════════════════════════════════════════════════════
#                 14. MINIHRY & INTERAKCE (v2.2)
# ═══════════════════════════════════════════════════════════════════════════════

# XP tracking a role progression
user_xp = {}  # {user_id: {"xp": int, "level": str}}
xp_cooldown = {}  # {user_id: timestamp} - Anti-cheat: prevence spam XP

# ═══ XP GAIN HELPER FUNKCE ═══
async def add_xp_to_user(user_id: int, xp_amount: int = 0, reason: str = ""):
    """Přidej XP uživateli s anti-cheat ochranou.
    
    Důvody:
    - "interaction" : Slash command (1-3 XP, 30s cooldown)
    - "voice_active" : Voice chat s aktivním music botem (2-5 XP, 60s cooldown)
    - "music_command" : Používání hudebních commandů (1-2 XP, 20s cooldown)
    """
    if user_id not in user_xp:
        user_xp[user_id] = {"xp": 0, "level": "🟩 Věřící"}
    
    # Anti-cheat: cooldown check
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    last_xp_time = xp_cooldown.get(user_id, 0)
    cooldown_seconds = {
        "interaction": 30,
        "voice_active": 60,
        "music_command": 20
    }
    
    required_cooldown = cooldown_seconds.get(reason, 0)
    if now - last_xp_time < required_cooldown:
        return False  # Cooldown nebyl ještě splnit
    
    # Přidej randomizované XP (anti-cheat: nepředvídatelné)
    if xp_amount == 0:
        xp_ranges = {
            "interaction": (1, 3),
            "voice_active": (2, 5),
            "music_command": (1, 2)
        }
        min_xp, max_xp = xp_ranges.get(reason, (1, 1))
        xp_amount = random.randint(min_xp, max_xp)
    
    user_xp[user_id]["xp"] += xp_amount
    xp_cooldown[user_id] = now
    
    # Inkrementuj weekly stats (v2.7.1)
    increment_xp_stats(xp_amount)
    
    # Uložit data
    await save_user_xp_to_storage()
    
    return True
xp_multiplier = 10  # 10 XP per win
biblical_quiz_questions = [
    {
        "question": "Kolik je všech 66 knih Bible?",
        "options": ["60", "66", "72", "50"],
        "correct": 1
    },
    {
        "question": "Kdo je autorem nejvíce psalmů?",
        "options": ["Mojžíš", "David", "Salomon", "Ježíš"],
        "correct": 1
    },
    {
        "question": "Jaký je název první knihy Bible?",
        "options": ["Exodus", "Genesis", "Leviticus", "Čísla"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval Kristův učitel během dospělosti?",
        "options": ["Jan", "Petr", "Moisés", "Jan Křtitel"],
        "correct": 3
    },
    {
        "question": "Kolik apostolů měl Ježíš?",
        "options": ["10", "11", "12", "13"],
        "correct": 2
    },
    {
        "question": "V kterém městě se Ježíš narodil?",
        "options": ["Jeruzalém", "Nazaret", "Betlém", "Jericho"],
        "correct": 2
    },
    {
        "question": "Kolik dní Ježíš postil v poušti?",
        "options": ["30", "40", "50", "7"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval největší apoštol Ježíšův?",
        "options": ["Matouš", "Petr", "Jakub", "Jan"],
        "correct": 1
    },
    {
        "question": "Co dělal Zákchej?",
        "options": ["Rybář", "Celtář", "Horář", "Lékař"],
        "correct": 1
    },
    {
        "question": "Kolik let Izraelci bloudili pouští?",
        "options": ["30", "40", "50", "60"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval první muž?",
        "options": ["Noe", "Abraham", "Adam", "Mojžíš"],
        "correct": 2
    },
    {
        "question": "Kolik přikázání dal Bůh Mojžíšovi?",
        "options": ["8", "10", "12", "15"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval velký otec Davida?",
        "options": ["Obed", "Jaj", "Boaz", "Ruben"],
        "correct": 2
    },
    {
        "question": "Kolik slov měla Nejkratší modlitba Ježíše? (Otče náš...)",
        "options": ["52", "66", "71", "88"],
        "correct": 2
    },
    {
        "question": "Kolik let bylo Noeovi když začala potopa?",
        "options": ["500", "600", "700", "800"],
        "correct": 1
    },
    {
        "question": "Jaké bylo celé jméno Matouše apoštola?",
        "options": ["Matouš Levita", "Levi", "Matouš Zákchej", "Matouš Šimon"],
        "correct": 0
    },
    {
        "question": "Kolik věrozvěstů měl Ježíš?",
        "options": ["4", "5", "7", "12"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval farizeský učitel, který navštívil Ježíše?",
        "options": ["Gamaliel", "Nikodém", "Annas", "Kajfáš"],
        "correct": 1
    },
    {
        "question": "V kterém věku zemřel Ježíš?",
        "options": ["30", "33", "36", "40"],
        "correct": 1
    },
    {
        "question": "Jaké bylo původní jméno Pavla před obrácením?",
        "options": ["Saul", "Šimon", "Judáš", "Timotej"],
        "correct": 0
    },
    {
        "question": "Kolik knih napsal apoštol Jan?",
        "options": ["1", "3", "5", "7"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval největší chrám v Jeruzalémě?",
        "options": ["Chram Božího Syna", "Chram Šolomounův", "Chram Heroda", "Chram Davida"],
        "correct": 2
    },
    {
        "question": "Kolik rozmnožovacích zázraků měl Ježíš v evangeliích?",
        "options": ["1", "2", "3", "4"],
        "correct": 2
    },
    {
        "question": "Které město bylo Thomášovým domovem?",
        "options": ["Jeruzalém", "Betánie", "Kafarnaum", "Jericho"],
        "correct": 2
    },
    {
        "question": "Kolik písní je v bibli sepsáno?",
        "options": ["100", "150", "200", "300"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval nejstarší syn Noeův?",
        "options": ["Sem", "Cham", "Jáfet", "Kain"],
        "correct": 0
    },
    {
        "question": "Kolik plasmů byla Elišova bolest po Eliášově nanebevzetí?",
        "options": ["Jednou", "Dvakrát", "Třikrát", "Čtyřikrát"],
        "correct": 1
    },
    {
        "question": "Jak dlouho se Ježíš modlil v Getsemanské zahradě?",
        "options": ["1 hodinu", "2 hodiny", "3 hodiny", "Celou noc"],
        "correct": 0
    },
    {
        "question": "Kolik let bylo Saraině když porodila Izáka?",
        "options": ["70", "80", "90", "100"],
        "correct": 2
    },
    {
        "question": "V kterém městě se narodil Pavel?",
        "options": ["Terasa", "Tarsos", "Tarsus", "Tébé"],
        "correct": 2
    },
    {
        "question": "Kolik bratrů měl Ježíš?",
        "options": ["1", "2", "3", "4"],
        "correct": 3
    },
    {
        "question": "Jaké bylo poslední slovo Ježíše na kříži?",
        "options": ["Otče", "Gotě", "Hotovo", "Amen"],
        "correct": 2
    }
]

def get_user_level(xp: int) -> str:
    """Vrátí level na základě XP."""
    if xp < 50:
        return "🌱 Nováček"
    elif xp < 100:
        return "🔰 Učedník"
    elif xp < 200:
        return "📖 Věřící"
    elif xp < 350:
        return "📜 Prorok"
    elif xp < 500:
        return "⚔️ Bojovník"
    elif xp < 750:
        return "🦁 Lev Judův"
    elif xp < 1000:
        return "👑 Apoštol"
    else:
        return "💎 Messiáš"

@bot.tree.command(name="biblicquiz", description="Biblický trivia kviz")
async def biblicquiz_command(interaction: discord.Interaction):
    """Biblický trivia kviz s interaktivními buttony."""
    user_id = interaction.user.id
    
    # Inicializuj XP
    if user_id not in user_xp:
        user_xp[user_id] = {"xp": 0, "level": "🔰 Učedník"}
    
    score = 0
    questions_used = random.sample(biblical_quiz_questions, min(10, len(biblical_quiz_questions)))
    
    await interaction.response.defer()
    
    for i, q in enumerate(questions_used, 1):
        # Vytvoř buttony pro odpovědi
        class QuizView(discord.ui.View):
            def __init__(self, q_data):
                super().__init__(timeout=30)
                self.q_data = q_data
                self.answered = False
                self.correct = False
                
                for idx, option in enumerate(q_data["options"]):
                    button = discord.ui.Button(
                        label=option,
                        style=discord.ButtonStyle.blurple,
                        custom_id=f"q_{idx}"
                    )
                    button.callback = self.button_callback
                    self.add_item(button)
            
            async def button_callback(self, button_interaction: discord.Interaction):
                if button_interaction.user.id != user_id:
                    await button_interaction.response.send_message(
                        "❌ Toto není tvůj kviz!",
                        ephemeral=True
                    )
                    return
                
                if self.answered:
                    await button_interaction.response.send_message(
                        "Už jsi odpověděl na tuto otázku!",
                        ephemeral=True
                    )
                    return
                
                # Určuj správnost
                answer_idx = int(button_interaction.data["custom_id"].split("_")[1])
                self.correct = (answer_idx == self.q_data["correct"])
                self.answered = True
                
                # Zobraz výsledek
                if self.correct:
                    await button_interaction.response.send_message(
                        f"✅ Správně! '{self.q_data['options'][self.q_data['correct']]}'",
                        ephemeral=True
                    )
                else:
                    await button_interaction.response.send_message(
                        f"❌ Špatně! Správná odpověď: '{self.q_data['options'][self.q_data['correct']]}'",
                        ephemeral=True
                    )
                
                self.stop()
        
        # Pošli otázku
        options_text = "\n".join([f"{j+1}️⃣ {opt}" for j, opt in enumerate(q["options"])])
        question_embed = discord.Embed(
            title=f"Otázka {i}/10",
            description=f"**{q['question']}**\n\n{options_text}",
            color=discord.Color.blue()
        )
        
        view = QuizView(q)
        await interaction.followup.send(embed=question_embed, view=view)
        
        # Čekej na odpověď
        await view.wait()
        
        if view.correct:
            score += 1
        
        # Krátkých pauza mezi otázkami
        await asyncio.sleep(0.5)
    
    # Přidej XP přes centralizovanou funkci (s anti-cheat)
    xp_gain = score * xp_multiplier
    await add_xp_to_user(user_id, xp_amount=xp_gain, reason="interaction")
    
    result_embed = discord.Embed(
        title="🎉 Výsledky Kvizu",
        description=f"**Skóre:** {score}/10\n**XP:** +{xp_gain}\n**Celkem XP:** {user_xp[user_id]['xp']}\n**Level:** {user_xp[user_id]['level']}",
        color=discord.Color.green() if score >= 7 else discord.Color.orange()
    )
    await interaction.followup.send(embed=result_embed)

@bot.tree.command(name="versfight", description="Veršový duel s jiným hráčem")
async def versfight_command(interaction: discord.Interaction, opponent: discord.User):
    """Veršový duel – náhodné verše, hlasování."""
    await interaction.response.defer()
    
    if opponent.bot:
        await interaction.followup.send("❌ Nemůžeš se duellovat s botem!")
        return
    
    user_id = interaction.user.id
    opponent_id = opponent.id
    
    if user_id not in user_xp:
        user_xp[user_id] = {"xp": 0, "level": "🔰 Učedník"}
    if opponent_id not in user_xp:
        user_xp[opponent_id] = {"xp": 0, "level": "🔰 Učedník"}
    
    # Vyber náhodné verše
    verse1 = random.choice(verses)
    verse2 = random.choice(verses)
    
    embed = discord.Embed(
        title="⚔️ Veršový Duel",
        description=f"{interaction.user.mention} vs {opponent.mention}",
        color=discord.Color.red()
    )
    embed.add_field(name=f"🔴 {interaction.user.name}", value=verse1, inline=False)
    embed.add_field(name=f"🔵 {opponent.name}", value=verse2, inline=False)
    
    msg = await interaction.followup.send(embed=embed)
    
    # Přidej emojis pro hlasování
    await msg.add_reaction("🔴")
    await msg.add_reaction("🔵")
    
    await asyncio.sleep(15)  # 15 sekund na hlasování
    
    # Spočítej hlasy
    try:
        msg = await interaction.channel.fetch_message(msg.id)
        red_votes = next((r.count for r in msg.reactions if r.emoji == "🔴"), 0) - 1
        blue_votes = next((r.count for r in msg.reactions if r.emoji == "🔵"), 0) - 1
        
        winner = interaction.user if red_votes > blue_votes else opponent if blue_votes > red_votes else None
        
        if winner:
            xp_gain = 50
            user_xp[winner.id]["xp"] += xp_gain
            user_xp[winner.id]["level"] = get_user_level(user_xp[winner.id]["xp"])
            
            # Ulož XP do storage
            await save_user_xp_to_storage()
            
            result = discord.Embed(
                title="🏆 Vítěz!",
                description=f"{winner.mention} vítězí!\n\n**Hlasy:** 🔴{red_votes} vs 🔵{blue_votes}\n**XP:** +{xp_gain}",
                color=discord.Color.gold()
            )
        else:
            result = discord.Embed(
                title="🤝 Remíza!",
                description=f"Obě strany byly stejně dobré!\n\n**Hlasy:** 🔴{red_votes} vs 🔵{blue_votes}",
                color=discord.Color.blue()
            )
        
        await interaction.followup.send(embed=result)
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba při počítání hlasů: {str(e)[:80]}")

# Cooldown tracking pro rollblessing
rollblessing_cooldown = {}

@bot.tree.command(name="rollblessing", description="RNG požehnání s cooldown 1h")
async def rollblessing_command(interaction: discord.Interaction):
    """Náhodné RNG požehnání s cooldown."""
    user_id = interaction.user.id
    now = datetime.datetime.now()
    
    # Zkontroluj cooldown
    if user_id in rollblessing_cooldown:
        last_used = rollblessing_cooldown[user_id]
        cooldown_time = last_used + datetime.timedelta(hours=1)
        if now < cooldown_time:
            remaining = cooldown_time - now
            minutes = remaining.total_seconds() / 60
            await interaction.response.send_message(f"⏳ Počkej ještě **{int(minutes)} minut** na další roll!")
            return
    
    # Generuj náhodné požehnání
    all_blessings = list(game_blessings.values()) + [
        "🙏 Bůh tě vidí a vidí tvou věrnost!",
        "✨ Tvá duše je jako hvězda na nebi – bez ceny!",
        "💫 Ať tě Bůh provede každým krokem!",
        "🌟 Nic není nemožné, když věříš!",
        "🔥 Buď silný v Kristu a zvítězíš!",
        "📿 Modlitba je nejsilnější zbraň!",
        "⛪ Sláva Bohu za jeho milost!",
        "👼 Andělé tě střeží v každém momentu!",
    ]
    
    blessing = random.choice(all_blessings)
    
    # Ulož cooldown
    rollblessing_cooldown[user_id] = now
    
    embed = discord.Embed(
        title="🎲 RNG Požehnání",
        description=f"{interaction.user.mention}\n\n{blessing}",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="Zobraz svůj profil s XP, levelem a hrami (v2.3.1)")
async def profile_command(interaction: discord.Interaction, user: discord.User = None):
    """Zobraz kompletní profil hráče s XP, levelem a game statistikami."""
    target = user or interaction.user
    user_id = target.id
    guild = interaction.guild
    
    # ═══ XP DATA ═══
    if user_id not in user_xp:
        user_xp[user_id] = {"xp": 0, "level": "🔰 Učedník"}
    
    xp_data = user_xp[user_id]
    xp = xp_data["xp"]
    level = xp_data["level"]
    
    # Kalkuluj progress k dalšímu levelu
    if xp < 100:
        next_milestone = 100
    elif xp < 300:
        next_milestone = 300
    else:
        next_milestone = xp + 100
    
    progress = ((xp % (next_milestone // 2)) / (next_milestone // 2)) * 100
    progress_bar = "█" * int(progress // 10) + "░" * (10 - int(progress // 10))
    
    # ═══ GAME DATA (v2.3.1) ═══
    user_game_data = get_game_data(user_id)
    sorted_games = sorted(user_game_data["games"].items(), key=lambda x: x[1], reverse=True)
    top_5 = sorted_games[:5]
    total_hours = sum(hours for _, hours in sorted_games)
    
    games_text = ""
    if top_5:
        games_text = "\n".join([f"• **{game}**: {hours:.1f}h" for game, hours in top_5])
    else:
        games_text = "Zatím žádné hry nejsou zaznamenány."
    
    # ═══ RANKING (v2.3.1) ═══
    ranking_text = "❌ Žádná data"
    if guild:
        player_stats = []
        for member in guild.members:
            if member.bot:
                continue
            member_game_data = get_game_data(member.id)
            member_hours = sum(member_game_data["games"].values())
            if member_hours > 0:
                player_stats.append((member.id, member_hours))
        
        if player_stats:
            player_stats.sort(key=lambda x: x[1], reverse=True)
            rank = next((i+1 for i, (mid, _) in enumerate(player_stats) if mid == user_id), None)
            if rank:
                ranking_text = f"#{rank} z {len(player_stats)} hráčů"
    
    # ═══ EMBED ═══
    embed = discord.Embed(
        title=f"👤 Profil – {target.name}",
        color=discord.Color.gold()
    )
    
    # XP sekce
    embed.add_field(name="🏅 Level", value=level, inline=True)
    embed.add_field(name="⭐ XP", value=f"{xp}", inline=True)
    embed.add_field(name="📊 Progres", value=f"{progress_bar} {int(progress)}%", inline=False)
    
    # Game sekce
    embed.add_field(name="🎮 TOP 5 Her", value=games_text, inline=False)
    embed.add_field(name="⏱️ Celkem", value=f"{total_hours:.1f}h", inline=True)
    embed.add_field(name="🏆 Ranking", value=ranking_text, inline=True)
    
    # Role sekce
    member_obj = guild.get_member(user_id) if guild else None
    if member_obj:
        roles_earned = []
        if total_hours >= 1:
            roles_earned.append("🎮 Gamer")
        if member_obj.activity and datetime.datetime.now().hour >= 23:
            roles_earned.append("🌙 Night Warrior")
        if member_obj.activity and datetime.datetime.now().weekday() >= 5:
            roles_earned.append("⛪ Weekend Crusader")
        
        roles_text = " ".join(roles_earned) if roles_earned else "Žádné speciální role"
        embed.add_field(name="🎖️ Role (v2.3.1)", value=roles_text, inline=False)
    
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
    
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════════════════════════════════════════════
#                 13. V2.3.1 – MULTI-SERVER THREAD-SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

# Tracking hraných her
game_activity = {}  # {user_id: {"games": {game_name: hours}, "last_update": timestamp}}
                     # GLOBÁLNÍ data - sdílena mezi všemi servery (logické, user má stejné hry všude)
guild_role_locks = {}  # {guild_id: asyncio.Lock} - zabránit race conditions při vytváření rolí

def get_guild_role_lock(guild_id: int) -> asyncio.Lock:
    """Vrátí lock pro guild - zabránit race conditions."""
    if guild_id not in guild_role_locks:
        guild_role_locks[guild_id] = asyncio.Lock()
    return guild_role_locks[guild_id]

def get_game_data(user_id: int):
    """Vrátí nebo vytvoří data hry pro uživatele."""
    if user_id not in game_activity:
        game_activity[user_id] = {"games": {}, "last_update": datetime.datetime.now()}
    return game_activity[user_id]

def track_user_activity(member: discord.Member, reset_on_new_game: bool = False):
    """Sleduj hry které člen hraje.
    
    Args:
        member: Discord member object
        reset_on_new_game: Pokud True, resetne last_update (používá se když hra ZAČNE)
    """
    if not member.activity or member.activity.type != discord.ActivityType.playing:
        return
    
    game_name = member.activity.name
    user_data = get_game_data(member.id)
    
    if game_name not in user_data["games"]:
        user_data["games"][game_name] = 0
    
    # Přidej čas hraní (pokud to není nová hra)
    now = datetime.datetime.now()
    if not reset_on_new_game:
        # Normální tracking - přičti čas od poslední aktualizace
        last_update = user_data["last_update"]
        time_delta = (now - last_update).total_seconds() / 3600
        user_data["games"][game_name] += time_delta
        
        # Inkrementuj weekly game hours s per-user tracking (v2.7.3)
        increment_game_hours(time_delta, member.id)
    
    # Aktualizuj last_update na teď (bez ohledu na reset_on_new_game)
    user_data["last_update"] = now


# ═══════════════════════════════════════════════════════════════════════════════
#                 15. V2.3.1 – MULTI-SERVER THREAD-SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

# Tracking hraných her

async def assign_game_roles(member: discord.Member):
    """Přiřaď role na základě her - THREAD-SAFE s guild lock."""
    if member.bot:
        return
    
    guild = member.guild
    user_data = get_game_data(member.id)
    
    # Najdi nebo vytvoř role - s lockem aby se nekonfliktovaly
    role_names = {
        "gamer": "🎮 Gamer",
        "hardcore_gamer": "🔥 Hardcore Gamer",
        "night_warrior": "🌙 Night Warrior",
        "weekend_crusader": "⛪ Weekend Crusader",
        "no_lifer": "💀 No Lifer",
        "collector": "🎯 Collector"
    }
    
    # Kalkuluj game hours a přiřaď role
    total_hours = sum(user_data["games"].values())
    
    try:
        # Použij lock pro guild - zabránit race conditions
        async with get_guild_role_lock(guild.id):
            # 🎮 Gamer role (1+ hodina hraní)
            if total_hours >= 1:
                role = discord.utils.get(guild.roles, name=role_names["gamer"])
                if not role:
                    try:
                        role = await guild.create_role(name=role_names["gamer"], color=discord.Color.blue())
                        print(f"[roles] Created 🎮 Gamer role in {guild.name}")
                    except discord.Forbidden:
                        print(f"[roles] ❌ No permission to create role in {guild.name}")
                        return
                    except Exception as e:
                        print(f"[roles] Error creating role: {e}")
                        return
                
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(f"[roles] Error adding role: {e}")
            
            # 🔥 Hardcore Gamer role (10+ hodin hraní)
            if total_hours >= 10:
                role = discord.utils.get(guild.roles, name=role_names["hardcore_gamer"])
                if not role:
                    try:
                        role = await guild.create_role(name=role_names["hardcore_gamer"], color=discord.Color.red())
                        print(f"[roles] Created 🔥 Hardcore Gamer role in {guild.name}")
                    except Exception as e:
                        print(f"[roles] Error creating Hardcore Gamer role: {e}")
                
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(f"[roles] Error adding Hardcore Gamer role: {e}")
            
            # 💀 No Lifer role (70+ hodin hraní dohromady)
            if total_hours >= 70:
                role = discord.utils.get(guild.roles, name=role_names["no_lifer"])
                if not role:
                    try:
                        role = await guild.create_role(name=role_names["no_lifer"], color=discord.Color.darker_gray())
                        print(f"[roles] Created 💀 No Lifer role in {guild.name}")
                    except Exception as e:
                        print(f"[roles] Error creating No Lifer role: {e}")
                
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(f"[roles] Error adding No Lifer role: {e}")
            
            # 🎯 Collector role (10+ různých her)
            num_games = len(user_data["games"])
            if num_games >= 10:
                role = discord.utils.get(guild.roles, name=role_names["collector"])
                if not role:
                    try:
                        role = await guild.create_role(name=role_names["collector"], color=discord.Color.gold())
                        print(f"[roles] Created 🎯 Collector role in {guild.name}")
                    except Exception as e:
                        print(f"[roles] Error creating Collector role: {e}")
                
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(f"[roles] Error adding Collector role: {e}")
            
            # 🌙 Night Warrior role (hrajou po 23:00)
            if member.activity and datetime.datetime.now().hour >= 23:
                role = discord.utils.get(guild.roles, name=role_names["night_warrior"])
                if not role:
                    try:
                        role = await guild.create_role(name=role_names["night_warrior"], color=discord.Color.dark_gray())
                        print(f"[roles] Created 🌙 Night Warrior role in {guild.name}")
                    except Exception as e:
                        print(f"[roles] Error creating Night Warrior role: {e}")
                
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(f"[roles] Error adding Night Warrior role: {e}")
            
            # ⛪ Weekend Crusader role (hrajou o víkendu)
            if member.activity and datetime.datetime.now().weekday() >= 5:
                role = discord.utils.get(guild.roles, name=role_names["weekend_crusader"])
                if not role:
                    try:
                        role = await guild.create_role(name=role_names["weekend_crusader"], color=discord.Color.gold())
                        print(f"[roles] Created ⛪ Weekend Crusader role in {guild.name}")
                    except Exception as e:
                        print(f"[roles] Error creating Weekend Crusader role: {e}")
                
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(f"[roles] Error adding Weekend Crusader role: {e}")
    
    except Exception as e:
        print(f"[v2.3.1] Unexpected error in assign_game_roles: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                   16. MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        import yt_dlp
        _yt_dlp = yt_dlp
    except ImportError:
        print("❌ yt-dlp není nainstalován! pip install yt-dlp")
        exit(1)
    
    if not TOKEN:
        print("❌ DISCORD_TOKEN není v .env!")
        exit(1)
    
    bot.run(TOKEN)
