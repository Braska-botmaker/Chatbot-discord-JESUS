# ╔════════════════════════════════════════════════════════════════════════════╗
# ║           Ježíš Discord Bot v2.2.1 – Enhanced Queue Display             ║
# ║                     Kompletní přepis na slash commands                      ║
# ║                  s Czech názvy pro maximální unikalitu                      ║
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
_data_lock = asyncio.Lock()

def _load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

async def _save_data(db):
    async with _data_lock:
        DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def _g(db, gid, key, default):
    """Guild-specific data namespace"""
    return db.setdefault(str(gid), {}).setdefault(key, default)

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
    }
}

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
    """Extrahuj URL a headery z YouTube/stream. Retry na timeout."""
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
                
                return {
                    "title": info.get("title", "Unknown"),
                    "url": info["url"],
                    "webpage_url": info.get("webpage_url") or url,
                    "headers": _headers_str_from_info(info),
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
    
    try:
        print(f"[music] Extracting: {song['url']}")
        extracted = ytdlp_extract(song['url'])
        
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
        embed = discord.Embed(title="🎵 Přehrávám", description=title, color=discord.Color.blue())
        await text_channel.send(embed=embed)
        
    except Exception as e:
        now_playing[guild.id] = None
        await text_channel.send(f"❌ Chyba při přehrávání: {str(e)[:100]}")
        print(f"[music] Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                   7. VERSE STREAK TRACKING DATA
# ═══════════════════════════════════════════════════════════════════════════════

def get_free_games():
    """Sbírá zdarma hry z více zdrojů: Epic, Steam (free na 0), PlayStation Blog.
    
    Vrací seznam dict s 'title' a 'url'. Deduplikuje podle (title, url).
    """
    games = []
    seen = set()

    # ═══ EPIC GAMES ═══
    try:
        epic_api = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        response = requests.get(epic_api, timeout=5)
        data = response.json()
        
        if isinstance(data, dict):
            data_section = data.get("data")
            if isinstance(data_section, dict):
                catalog = data_section.get("Catalog")
                if isinstance(catalog, dict):
                    search_store = catalog.get("searchStore")
                    if isinstance(search_store, dict):
                        elements = search_store.get("elements", [])
                        if isinstance(elements, list):
                            for game in elements:
                                if not isinstance(game, dict):
                                    continue
                                try:
                                    if game.get("price", {}).get("totalPrice", {}).get("discountPrice") == 0:
                                        title = game.get("title", "Unknown").strip()
                                        mappings = game.get("catalogNs", {}).get("mappings", [])
                                        if mappings and isinstance(mappings, list) and len(mappings) > 0:
                                            slug = mappings[0].get("pageSlug", "")
                                            if slug:
                                                url = f"https://store.epicgames.com/p/{slug}"
                                                key = (title, url)
                                                if key not in seen:
                                                    seen.add(key)
                                                    games.append({"title": title, "url": url})
                                except Exception:
                                    continue
    except Exception as e:
        print(f"[freegames] Epic error: {e}")

    # ═══ STEAM ═══
    try:
        # Steam special discounts na 0 - hledáme hry slevněné z nějaké ceny na 0
        steam_url = "https://store.steampowered.com/search/?maxprice=0&specials=1"
        r = requests.get(steam_url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text
        
        # Hledej search_result_row s titulem a URL
        pattern = re.compile(
            r'<a[^>]+class="search_result_row[^"]*"[^>]+href="(?P<href>[^"]+)"[^>]*>.*?<span class="title">(?P<title>.*?)</span>',
            re.DOTALL
        )
        count = 0
        for m in pattern.finditer(html):
            title = re.sub(r"\s+", " ", m.group('title')).strip()
            title = html_unescape(title)
            href = m.group('href').split('?')[0]
            key = (title, href)
            if key not in seen and count < 12:
                seen.add(key)
                games.append({"title": title, "url": href})
                count += 1
    except Exception as e:
        print(f"[freegames] Steam error: {e}")

    # ═══ PLAYSTATION PLUS ═══
    try:
        ps_feed = "https://blog.playstation.com/tag/playstation-plus/feed/"
        r = requests.get(ps_feed, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            try:
                root = ET.fromstring(r.content)
                items = root.findall('.//item')
                for item in items[:6]:
                    title_el = item.find('title')
                    link_el = item.find('link')
                    title = title_el.text if title_el is not None else 'PlayStation Plus announcement'
                    link = link_el.text if link_el is not None else 'https://blog.playstation.com'
                    key = (title, link)
                    if key not in seen:
                        seen.add(key)
                        games.append({"title": title, "url": link})
            except Exception as e:
                print(f"[freegames] PlayStation parse error: {e}")
    except Exception as e:
        print(f"[freegames] PlayStation error: {e}")

    return games

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
    '"Bůh není Bůh těch mrtvých, ale živých." (Marek 12,27)'
]

# ═══════════════════════════════════════════════════════════════════════════════
#              9. GAME BLESSINGS DICTIONARY (53 her)
# ═══════════════════════════════════════════════════════════════════════════════

game_blessings = {
    "League of Legends": "Ať tě neodvede do pokušení toxicit, ale zbaví tě feederů.",
    "Counter-Strike 2": "Ať jsou tvé reflexy rychlé a spoluhráči nejsou AFK.",
    "Satisfactory": "Ať jsou tvé továrny efektivní a pásy nikdy nezaseknou.",
    "Minecraft": "Ať draka prdel nakopeš!",
    "Mafia": "Pamatuj – rodina je všechno. Ať tě ochrání před každým podrazem.",
    "Mafia II": "Buď jako Vito – čestný mezi nečestnými. Ať tě nezasáhne zrada.",
    "Resident Evil 2": "Ať ti nikdy nedojdou náboje v Raccoon City.",
    "Resident Evil 3": "Ať tě Nemesis mine obloukem.",
    "Resident Evil 4": "Ať tě El Gigante nezašlápne.",
    "Resident Evil 7": "Ať přežiješ noc v domě Bakers.",
    "Resident Evil 8": "Ať tě paní Dimitrescu nenajde pod sukní.",
    "KLETKA": "Dej bacha, ať ti nedojde benzín, bratře.",
    "КЛЕТЬ Демо": "Dej bacha na souseda.",
    "Ready or Not": "Ať tě Pán vede v každé akci a dá ti klidnou hlavu v boji za spravedlnost.",
    "Roblox": "Ať tvá kreativita roste a radost z hraní tě nikdy neopustí.",
    "Counter-Strike: Global Offensive": "Ať je tvůj AIM přesný a týmoví kamarádi pevní.",
    "Dota 2": "Ať tvůj draft vede k vítězství a toxicita tě míjí.",
    "Cyberpunk 2077": "Ať tě budoucnost obohatí a ne zaženou noční můry.",
    "Elden Ring": "Ať ten boss padne co nejrychleji bratře",
    "Team Fortress 2": "Ať ti nostalgie nezahltí mozek",
    "Rust": "Ať tě nikdo nezradí, jako mě kdysi",
    "ARK: Survival Evolved": "Ať tvůj kmen přežije ve světě dinosaurů.",
    "Grand Theft Auto V": "Ať tě nezavřou",
    "Fall Guys": "Ať skončíš na trůnu a ne na posledním místě.",
    "Terraria": "Ať tvé podzemí oplývá poklady a dobrodružstvím.",
    "Phasmophobia": "Ať duchové zůstanou jen legendou a vy se vrátíte v klidu domů.",
    "Valheim": "Ať tě Odin provede světy plnými výzev.",
    "Among Us": "Ať vás bude hodně a zrada vyloučena.",
    "Rocket League": "Ať tvůj tým střílí góly jako z evangelia radosti.",
    "Black Desert Online": "Ať tvé cestování bohatě obohatí duchovní i materiální život.",
    "The Witcher 3": "Ať tvá cesta po Ciri vedena moudrostí a milosrdenstvím.",
    "Red Dead Redemption 2": "Ať tvá čest je silnější než touha po penězích",
    "Hades": "Ať tvoje cesta z podsvětí vede k osvobození a odpuštění.",
    "Tom Clancy's Rainbow Six Siege X": "Ať tvá taktika zachrání životy, ne přidá zármutek.",
    "Skyrim": "Ať dračí křídla nevzbudí zlo, a tvé srdce zůstane silné.",
    "The Binding of Isaac: Rebirth": "Ať ti rng bůh přeje a přinese ti všechny tier 4 předměty, které si přeješ.",
    "Dead by Daylight": "Ať tě temnota nepohltí bratře v kristu.🙏",
    "Project Zomboid": "Ať to ve zombie apokalypse zvládneš co nejdýl a najdeš aspoň trochu bezpečný barák, kde ti to nerozbijou nemrtví.",
    "Half-Life": "Ať tě Freeman provede Borderworldem bez toho, aby tě cokoliv sežralo nebo rozdrtilo.",
    "Half-Life 2": "Buď jako Gordon – tichej, ale všechno kolem tebe padá k zemi. Prostě efektivní jak prase.",
    "Half-Life: Alyx": "Ať tě Combine nechytí a celá Alyxina mise dopadne tak epicky, jak si zaslouží.",
    "VALORANT": "Ať tvůj aim lítá jak laser a týmová ekonomika se ti nerozsype po dvou kolech.",
    "Arena Breakout: Infinite": "Ať v té betonce najdeš tu nejlepší lootárnu a exit zvládneš bez toho, aby tě někdo sundal.",
    "Fallout": "Válka se fakt nemění… ale ty klidně můžeš a pěkně jim to tam nalož.",
    "Fallout 2": "Ať tvoje cesta mezi Vault Dwellery skončí spíš oslavou než atomovým ohňostrojem.",
    "Fallout 3": "Ať Project Purity fakt zachrání svět a neskončí to jen dalším radioaktivním fiaskem.",
    "Fallout: New Vegas": "Ať už půjdeš s Yes Manem, NCR nebo Caesarovými blázny, ať ti to padne do noty a Vegas je tvoje.",
    "Fallout 4": "Ať najdeš svého potomka a Commonwealth dáš dohromady dřív, než ho někdo vyhodí do vzduchu.",
    "Fallout 76": "Ať v pustině narazíš na živý lidi a ne jen na mrtvý servery a prázdný lokace.",
    "Kingdom Come: Deliverance": "Ať tvoje jízdy na Šedivce kolem Ratají skončí vždycky na sedle, ne na zemi.",
    "Kingdom Come: Deliverance II": "Ať se Jindra dočká své odvety a království zůstane v bezpečí.",
    "Outlast": "Ať tě Chris Walker nikdy nedostane.",
    "Outlast 2": "Ať tě basketbalistka nikdy nedostane.",
    "The Outlast Trials": "Ať testy přežiješ se všemi končetinami a žaludkem na místě.",
}

# ═══════════════════════════════════════════════════════════════════════════════
#                  10. BOT EVENTS – STARTUP & READY
# ═══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    """Bot startup event – synchronizuj slash commands a spusť scheduled tasks."""
    print(f"✅ Bot je přihlášen jako {bot.user}")
    
    # Načti verse streak z storage
    await load_verse_streak_from_storage()
    
    try:
        synced = await bot.tree.sync()
        print(f"[commands] Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"[commands] Sync error: {e}")
    
    send_morning_message.start()
    send_night_message.start()
    send_free_games.start()
    voice_watchdog.start()
    clear_recent_announcements.start()

# ═══════════════════════════════════════════════════════════════════════════════
#                11. SLASH COMMANDS – HUDBA / MUSIC
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="yt", description="Přidej skladbu do fronty a přehrávej z YouTube")
async def yt_command(interaction: discord.Interaction, url: str):
    """Slash command /yt – přehrávání hudby z YouTube."""
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
    
    # Extrahuj název z URL pomocí yt-dlp
    try:
        title = "Načítám..."
        extracted = ytdlp_extract(url)
        title = extracted.get("title", "Neznámá skladba")
    except Exception as e:
        title = "Chyba při načítání názvu"
        print(f"[yt] Error extracting title: {e}")
    
    _queue_for(guild.id).append({"url": url, "title": title})
    if not vc.is_playing():
        await play_next(guild, interaction.channel)
        await interaction.followup.send(f"▶️ Začínám přehrávat: **{title}**\n{url}")
    else:
        await interaction.followup.send(f"✅ Přidáno do fronty: **{title}**\n{url}")

@bot.tree.command(name="další", description="Přeskoč na další písničku")
async def dalsi_command(interaction: discord.Interaction):
    """Skip current song."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nic se nehraje!")
            return
        vc.stop()
        await interaction.response.send_message("⏭️ Přeskočeno!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="pauza", description="Pozastavit přehrávání")
async def pauza_command(interaction: discord.Interaction):
    """Pause playback."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nic se nehraje!")
            return
        vc.pause()
        await interaction.response.send_message("⏸️ Pozastaveno!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="pokračuj", description="Pokračovat v přehrávání")
async def pokracuj_command(interaction: discord.Interaction):
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
        else:
            await interaction.response.send_message("❌ Nic není pozastaveno!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="zastav", description="Zastavit přehrávání")
async def zastav_command(interaction: discord.Interaction):
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
        now_playing[guild.id] = None
        await interaction.response.send_message("⏹️ Zastaveno! Fronta smazána.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="odejdi", description="Odpoj se z voice kanálu")
async def odejdi_command(interaction: discord.Interaction):
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
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="np", description="Zobraz právě přehrávanou skladbu")
async def np_command(interaction: discord.Interaction):
    """Show now playing."""
    try:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Nic se nehraje!")
            return
        title = now_playing.get(guild.id, "Unknown")
        embed = discord.Embed(title="🎵 Právě hraje", description=title, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="fronta", description="Zobraz hudební frontu")
async def fronta_command(interaction: discord.Interaction):
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
        embed = discord.Embed(title="🎵 Fronta", description=description, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="vtest", description="Test voice připojení")
async def vtest_command(interaction: discord.Interaction):
    """Test voice connection."""
    await interaction.response.defer()
    guild = interaction.guild
    vc = discord.utils.get(bot.voice_clients, guild=guild)
    if not vc or not vc.is_connected():
        await interaction.followup.send("❌ Bot není v voice kanálu!")
        return
    try:
        source = discord.FFmpegOpusAudio(
            "pipe:",
            stdin=True,
            before_options="-f lavfi -i anullsrc=r=48000:cl=mono -t 3",
            options=get_ffmpeg_options()
        )
        vc.play(source)
        await interaction.followup.send("🔊 Hraju 3 sekundový tón...")
        await asyncio.sleep(3.5)
        vc.stop()
        await interaction.followup.send("✅ Voice test úspěšný!")
    except Exception as e:
        await interaction.followup.send(f"❌ Voice test selhalo: {str(e)[:100]}")

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

@bot.tree.command(name="freegames", description="Hry zdarma – Epic Games, Steam, PlayStation")
async def freegames_command(interaction: discord.Interaction):
    """Show free games from Epic Games Store, Steam, and PlayStation."""
    await interaction.response.defer()
    try:
        free_games = get_free_games()
        if not free_games:
            await interaction.followup.send("❌ Momentálně nejsou k dispozici žádné hry zdarma.")
            return
        
        # Vytvoř strukturovaný text s odkazy
        description_lines = []
        urls_for_previews = []
        for i, game in enumerate(free_games[:15], 1):
            description_lines.append(f"{i}. [{game['title']}]({game['url']})")
            urls_for_previews.append(game['url'])
        
        description = "\n".join(description_lines)
        
        # Vytvoř embed
        embed = discord.Embed(title="🎁 Hry Zdarma", description=description, color=discord.Color.purple())
        embed.set_footer(text="Hry se mění měsíčně. Náhledy se načítají pod embedem...")
        
        # Pošli embed
        await interaction.followup.send(embed=embed)
        
        # Pošli bare URLs pro Discord link previews
        if urls_for_previews:
            urls_message = "\n".join(urls_for_previews)
            await interaction.followup.send(urls_message)
    except Exception as e:
        print(f"[freegames] Error: {type(e).__name__}: {e}")
        await interaction.followup.send(f"❌ Chyba při načítání her: {str(e)[:80]}")

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

@bot.tree.command(name="verze", description="Info o verzi botu")
async def verze_command(interaction: discord.Interaction):
    """Show bot version and changelog."""
    try:
        embed = discord.Embed(title="ℹ️ Ježíš Discord Bot", color=discord.Color.gold())
        embed.add_field(name="Verze", value="v2.2.1 – Enhanced Queue Display", inline=False)
        embed.add_field(name="Co je nového", value="""
**v2.2.1 – Enhanced Queue Display:**
✨ `/fronta` zobrazuje strukturovaně: název skladby + URL pod sebou
✨ Auto-extrakce názvů skladeb z YouTube do fronty
✨ Všechny minihry z v2.2 plně funkční

**v2.2 – Minihry & Interakce:**
🎮 `/biblickykviz` – biblický trivia s 10 interaktivními otázkami
🎮 `/versfight @user` – veršový duel se hlasováním
🎮 `/rollblessing` – RNG požehnání (cooldown 1 hodina)
🎮 `/profile [@user]` – profil s XP a levelem
🏅 XP Systém: 🔰 Učedník → 📜 Prorok → 👑 Apoštol

✅ Slash commands pro modernost a bezpečnost
❌ Žádné @ mention u automatických zpráv
""", inline=False)
        embed.add_field(name="GitHub", value="https://github.com/Braska-botmaker/Chatbot-discord-JESUS", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="komandy", description="Všechny dostupné příkazy")
async def komandy_command(interaction: discord.Interaction):
    """Show all available commands."""
    try:
        embed = discord.Embed(title="📋 Příkazy – Ježíš Discord Bot v2.2.1", color=discord.Color.blue())
        embed.add_field(name="🎵 Hudba", value="""
/yt <url> – Přehrávej z YouTube
/další – Přeskoč
/pauza – Pozastav
/pokračuj – Pokračuj
/zastav – Zastavit & vyčistit
/odejdi – Odejít z voice
/np – Co se hraje
/fronta – Zobraz frontu
/vtest – Test voice
""", inline=False)
        embed.add_field(name="📖 Ostatní", value="""
/verze – Info o verzi
/verse – Náhodný verš
/freegames – Hry zdarma
/bless [@user] – Požehnání
/diag – Diagnostika
/komandy – Tohle
""", inline=False)
        embed.add_field(name="🎮 Minihry (v2.2)", value="""
/biblickykviz – Biblický trivia
/versfight @user – Veršový duel
/rollblessing – RNG požehnání
/profile [@user] – Tvůj profil + XP
""", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="diag", description="Diagnostika a info o botu")
async def diag_command(interaction: discord.Interaction):
    """Show bot diagnostics."""
    await interaction.response.defer()
    embed = discord.Embed(title="🩺 Diagnostika", color=discord.Color.green())
    machine = platform.machine()
    is_rpi = _is_arm_system()
    embed.add_field(name="💻 Systém", value=f"Machine: {machine}\nARM: {'✅' if is_rpi else '❌'}", inline=True)
    ffmpeg_ok = "✅" if has_ffmpeg() else "❌"
    opus_ok = "✅" if HAS_OPUS else "❌"
    nacl_ok = "✅" if HAS_NACL else "❌"
    embed.add_field(name="🔊 Audio", value=f"FFmpeg: {ffmpeg_ok}\nOpus: {opus_ok}\nNaCl: {nacl_ok}", inline=True)
    voice_count = len(bot.voice_clients)
    embed.add_field(name="🎤 Voice", value=f"Connected: {voice_count}", inline=True)
    if bot.user:
        embed.add_field(name="⏱️ Verze", value="v2.2.1\nEnhanced Queue Display", inline=True)
    await interaction.followup.send(embed=embed)

# ═══════════════════════════════════════════════════════════════════════════════
#                13. SCHEDULED TASKS – AUTOMATICKÉ ZPRÁVY
# ═══════════════════════════════════════════════════════════════════════════════

@tasks.loop(minutes=1)
async def send_morning_message():
    """Odeslat ranní zprávu v 09:00 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 9 and now.minute == 0:
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="požehnání🙏")
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
            channel = discord.utils.get(guild.text_channels, name="požehnání🙏")
            if channel:
                embed = discord.Embed(title="🌙 Dobrou noc!", description="Spi v pokoji Kristově. Zítřka tě čeká nový den plný příležitostí.", color=discord.Color.dark_blue())
                try:
                    await channel.send(embed=embed)
                    print(f"[night] Sent to {guild.name}")
                except Exception as e:
                    print(f"[night] Error in {guild.name}: {e}")

@tasks.loop(minutes=1)
async def send_free_games():
    """Odeslat zdarma hry v 20:10 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 20 and now.minute == 10:
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="hry_zdarma💵")
            if channel:
                try:
                    free_games = get_free_games()
                    if not free_games:
                        continue
                    
                    # Vytvoř strukturovaný text s odkazy
                    description_lines = []
                    urls_for_previews = []
                    for i, game in enumerate(free_games[:15], 1):
                        description_lines.append(f"{i}. [{game['title']}]({game['url']})")
                        urls_for_previews.append(game['url'])
                    
                    description = "\n".join(description_lines)
                    
                    # Vytvoř embed
                    embed = discord.Embed(title="🎁 Hry Zdarma", description=description, color=discord.Color.purple())
                    embed.set_footer(text="Hry se mění měsíčně.")
                    
                    # Pošli embed
                    await channel.send(embed=embed)
                    
                    # Pošli bare URLs pro Discord link previews
                    if urls_for_previews:
                        urls_message = "\n".join(urls_for_previews)
                        await channel.send(urls_message)
                    
                    print(f"[send_free_games] Sent to {guild.name}")
                except Exception as e:
                    print(f"[send_free_games] Error in {guild.name}: {e}")

@tasks.loop(minutes=5)
async def voice_watchdog():
    """Monitoruj voice connections."""
    for guild_id, vc in list((vc.guild.id, vc) for vc in bot.voice_clients):
        if not vc.is_connected():
            _queue_for(guild_id).clear()
            now_playing[guild_id] = None

@tasks.loop(hours=1)
async def clear_recent_announcements():
    """Vyčisti staré oznámení každou hodinu."""
    global recently_announced_games
    recently_announced_games.clear()

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
        channel = discord.utils.get(after.guild.text_channels, name="požehnání🙏")
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
            print(f"[presence] Channel 'požehnání🙏' not found or no permissions")
    
    # Hra skončila
    elif before_game is not None and after_game is None:
        print(f"[presence] {after.name} stopped playing: {before_game.name}")

# ═══════════════════════════════════════════════════════════════════════════════
#                    15. MINIHRY & INTERAKCE (v2.2)
# ═══════════════════════════════════════════════════════════════════════════════

# XP tracking a role progression
user_xp = {}  # {user_id: {"xp": int, "level": str}}
xp_multiplier = 10  # 10 XP per win
biblical_quiz_questions = [
    {
        "question": "Kolik je všech 66 knih Bible?",
        "options": ["60", "66", "72", "50"],
        "correct": 1
    },
    {
        "question": "Kdo je autorem nejvíce psalmů?",
        "options": ["Mojžíš", "Davidský", "Salomon", "Ježíš"],
        "correct": 1
    },
    {
        "question": "Jaký je název první knihy Bible?",
        "options": ["Exodus", "Genesis", "Leviticus", "Čísla"],
        "correct": 1
    },
    {
        "question": "Jak se jmenoval Kristův učitel během dospělosti?",
        "options": ["Jan", "Petr", "Ježíš", "Jan Křtitel"],
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
        "question": "Jaké bylo jméno muže, který trpěl 38 let?",
        "options": ["Zákchej", "Neznámý", "Paralyzovaný", "Sleператор"],
        "correct": 2
    },
    {
        "question": "Kolik dní Ježíš postil v poušti?",
        "options": ["30", "40", "50", "7"],
        "correct": 1
    },
    {
        "question": "Jaké je jméno největšího apoštola?",
        "options": ["Matouš", "Petr", "Jakub", "Jan"],
        "correct": 1
    },
    {
        "question": "Co dělal Zákchej dříve?",
        "options": ["Rybář", "Celtář", "Horář", "Lékař"],
        "correct": 1
    }
]

def get_user_level(xp: int) -> str:
    """Vrátí level na základě XP."""
    if xp < 100:
        return "🔰 Učedník"
    elif xp < 300:
        return "📜 Prorok"
    else:
        return "👑 Apoštol"

@bot.tree.command(name="biblickykviz", description="Biblický trivia kviz – 10 otázek")
async def biblickykviz_command(interaction: discord.Interaction):
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
    
    # Uprav XP
    xp_gain = score * xp_multiplier
    user_xp[user_id]["xp"] += xp_gain
    user_xp[user_id]["level"] = get_user_level(user_xp[user_id]["xp"])
    
    result_embed = discord.Embed(
        title="🎉 Výsledky Kvizu",
        description=f"**Skóre:** {score}/10\n**XP:** +{xp_gain}\n**Celkem XP:** {user_xp[user_id]['xp']}\n**Level:** {user_xp[user_id]['level']}",
        color=discord.Color.green() if score >= 7 else discord.Color.orange()
    )
    await interaction.followup.send(embed=result_embed)

@bot.tree.command(name="versfight", description="Veršový duel s dalším hráčem")
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

@bot.tree.command(name="profile", description="Zobraz svůj profil s XP a levelem")
async def profile_command(interaction: discord.Interaction, user: discord.User = None):
    """Zobraz profil hráče s XP a levelem."""
    target = user or interaction.user
    user_id = target.id
    
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
        next_milestone = xp + 100  # Další milník
    
    progress = ((xp % (next_milestone // 2)) / (next_milestone // 2)) * 100
    progress_bar = "█" * int(progress // 10) + "░" * (10 - int(progress // 10))
    
    embed = discord.Embed(
        title=f"👤 Profil – {target.name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="🏅 Level", value=level, inline=True)
    embed.add_field(name="⭐ XP", value=f"{xp}", inline=True)
    embed.add_field(name="📊 Progres", value=f"{progress_bar} {int(progress)}%", inline=False)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
    
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════════════════════════════════════════════
#                      16. MAIN ENTRY POINT
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
