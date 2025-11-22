# bot.py — v2.1.0b – Slash Commands Era (Ježíš Discord Bot)
# Kompletní přepis na slash commands s Czech názvy pro unikalitu
# /yt, /další, /pauza, /zastav, /odejdi, /fronta, /verse, /freegames, /bless, /komandy, /diag

import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import datetime
import os
import requests
from dotenv import load_dotenv
import pytz
from html import unescape as html_unescape
import re
import platform

import asyncio
from collections import deque
from typing import Optional
import shutil
import time
import json
import pathlib
import socket
_yt_dlp = None

# ===== RPi VOICE FIX: Patch Discord VoiceClient UDP connection for ARM architecture =====
# Error 4006 occurs when discord.py's voice UDP handshake fails on Raspberry Pi.
# Root cause: UDP packets are fragmented or discord.py sends frames that don't negotiate properly.
# Fix: Monkeypatch VoiceClient._handshake_websocket() to retry on 4006 with exponential backoff.

def _is_arm_system():
    """Detect if running on ARM system (RPi, etc)."""
    machine = platform.machine().lower()
    # Check for various ARM architectures
    arm_variants = ['arm', 'armv6', 'armv7', 'aarch64', 'armv8']
    is_arm = any(variant in machine for variant in arm_variants)
    print(f"[RPi patch] Platform detection: machine={machine}, is_arm={is_arm}")
    return is_arm

def _patch_voice_client_for_rpi():
    """Apply 4006-specific retry logic to discord.VoiceClient."""
    is_rpi = _is_arm_system()
    if not is_rpi:
        print("[RPi patch] Not on ARM - skipping patches")
        return
    
    try:
        import discord.voice_client
        original_inner_connect = discord.voice_client.VoiceClient._inner_connect
        
        async def patched_inner_connect(self):
            """Retry inner connection with exponential backoff on 4006 errors."""
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
                        print(f"[RPi patch] 4006 detected in _inner_connect, retrying in {delay}s... ({attempt+1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    
                    if is_4006:
                        print(f"[RPi patch] 4006 error persisted after {max_retries} _inner_connect attempts")
                    raise
            
            return None
        
        discord.voice_client.VoiceClient._inner_connect = patched_inner_connect
        print("[RPi patch] ✅ Applied to VoiceClient._inner_connect - 4006 retry logic active")
    except Exception as e:
        print(f"[RPi patch] ⚠️ Warning: Failed to patch _inner_connect: {e}")

_patch_voice_client_for_rpi()

def _patch_voice_connect_for_rpi():
    """Add resilience to ch.connect() calls by catching and retrying 4006 internally."""
    is_rpi = _is_arm_system()
    if not is_rpi:
        return
    
    try:
        import discord.voice_client
        original_connect = discord.voice_client.VoiceClient.connect
        
        async def patched_connect(self, *, timeout=60.0, reconnect=False, self_deaf=False, self_mute=False, **kwargs):
            """Wrap connect() to retry on 4006 errors with extended timeout."""
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
                        print(f"[RPi patch] Timeout in connect(), retrying in {delay}s ({retry_count+1}/{max_retries})")
                        retry_count += 1
                        await asyncio.sleep(delay)
                        continue
                    print(f"[RPi patch] Timeout persisted after {max_retries} connect() attempts")
                    raise
                except Exception as e:
                    error_msg = str(e)
                    is_4006 = "4006" in error_msg or "WebSocket closed with 4006" in error_msg
                    
                    if is_4006 and retry_count < max_retries - 1:
                        delay = base_delay * (1.5 ** retry_count)
                        print(f"[RPi patch] 4006 in connect(), retrying in {delay}s ({retry_count+1}/{max_retries})")
                        retry_count += 1
                        await asyncio.sleep(delay)
                        continue
                    
                    if is_4006:
                        print(f"[RPi patch] 4006 persisted after {max_retries} connect() attempts")
                    raise
        
        discord.voice_client.VoiceClient.connect = patched_connect
        print("[RPi patch] ✅ Applied to VoiceClient.connect() - 4006 resilience active")
    except Exception as e:
        print(f"[RPi patch] ❌ Warning: Failed to patch connect(): {e}")

_patch_voice_connect_for_rpi()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ===== CONFIGURATION & DATA =====

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

# ===== MUSIC SYSTEM =====

recently_announced_games = set()

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

music_queues = {}
now_playing = {}
bot_loop = None

# ===== VERSE STREAK TRACKING =====
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

# ===== DATA: Verses & Blessings =====

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
}

def get_ffmpeg_options():
    """Return FFmpeg options optimized for platform (RPi uses lower bitrate)."""
    is_rpi = _is_arm_system()
    return FFMPEG_OPTIONS_RPi if is_rpi else FFMPEG_OPTIONS

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def _headers_str_from_info(info: dict) -> str:
    """Extract HTTP headers from yt-dlp info dict."""
    headers = info.get("http_headers") or {}
    return "".join(f"{k}: {v}\r\n" for k, v in headers.items())

def make_before_options(headers_str: str) -> str:
    """Compose before_options for FFmpeg including HTTP headers."""
    if not headers_str:
        return FFMPEG_RECONNECT
    safe = headers_str.replace('"', r'\"')
    return f'{FFMPEG_RECONNECT} -headers "{safe}"'

def ytdlp_extract(url: str):
    """Extract URL and headers from YouTube/stream. Retry on timeout."""
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

voice_locks = {}
last_voice_channel = {}

def _guild_lock(gid: int) -> asyncio.Lock:
    if gid not in voice_locks:
        voice_locks[gid] = asyncio.Lock()
    return voice_locks[gid]

async def wait_until_connected(vc: Optional[discord.VoiceClient], tries: int = 15, delay: float = 0.3) -> bool:
    """Opakovaně zkontroluje, zda je voice skutečně připojený."""
    for i in range(tries):
        if vc and vc.is_connected():
            await asyncio.sleep(0.1)
            return True
        wait_time = delay * (i + 1) if i < 3 else delay * 3
        await asyncio.sleep(wait_time)
    return False

async def ensure_voice_by_guild(guild: discord.Guild, *, text_channel: Optional[discord.TextChannel] = None) -> Optional[discord.VoiceClient]:
    """Ensure voice connection for guild. Přihlásí se do poslední známé voice channel."""
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
    """Play next song in queue."""
    queue = _queue_for(guild.id)
    
    if not queue:
        print(f"[music] Queue empty in {guild.name}")
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if vc and vc.is_connected():
            now_playing[guild.id] = None
            try:
                await vc.disconnect()
            except:
                pass
        return
    
    song = queue.popleft()
    
    try:
        print(f"[music] Extracting: {song['url']}")
        extracted = ytdlp_extract(song['url'])
        
        vc = await ensure_voice_by_guild(guild, text_channel=text_channel)
        if not vc:
            await text_channel.send("❌ Nelze se připojit k voice kanálu!")
            return
        
        headers = extracted.get("headers", "")
        before_options = make_before_options(headers)
        source = discord.FFmpegOpusAudio(
            extracted["url"],
            before_options=before_options,
            options=get_ffmpeg_options()
        )
        
        now_playing[guild.id] = extracted["title"]
        
        def after_play(error):
            if error:
                print(f"[music] Playback error: {error}")
            asyncio.run_coroutine_threadsafe(
                play_next(guild, text_channel),
                bot.loop
            )
        
        vc.play(source, after=after_play)
        embed = discord.Embed(title="🎵 Přehrávám", description=extracted["title"], color=discord.Color.blue())
        await text_channel.send(embed=embed)
        
    except Exception as e:
        now_playing[guild.id] = None
        await text_channel.send(f"❌ Chyba při přehrávání: {str(e)[:100]}")
        print(f"[music] Error: {e}")

# ===== SLASH COMMANDS =====

@bot.event
async def on_ready():
    """Bot startup event."""
    print(f"✅ Bot je přihlášen jako {bot.user}")
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

# HUDBA / MUSIC

@bot.tree.command(name="yt", description="Přidej skladbu do fronty a přehrávej z YouTube")
async def yt_command(interaction: discord.Interaction, url: str):
    """Slash command /yt – přehrávání hudby z YouTube."""
    await interaction.response.defer()
    
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("❌ Musíš být na serveru!")
        return
    
    vc = discord.utils.get(bot.voice_clients, guild=guild)
    if not vc or not vc.is_connected():
        await interaction.followup.send("❌ Bot není v voice kanálu. Připoj se do voice a zkus znovu!")
        return
    
    _queue_for(guild.id).append({"url": url})
    
    if not vc.is_playing():
        await play_next(guild, interaction.channel)
        await interaction.followup.send(f"▶️ Začínám přehrávat: {url}")
    else:
        await interaction.followup.send(f"✅ Přidáno do fronty: {url}")

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
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

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
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

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
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

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
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

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
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

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
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

@bot.tree.command(name="fronta", description="Zobraz hudební frontu")
async def fronta_command(interaction: discord.Interaction):
    """Show music queue."""
    try:
        guild = interaction.guild
        queue = _queue_for(guild.id)
        
        if not queue:
            await interaction.response.send_message("❌ Fronta je prázdná!")
            return
        
        items = "\n".join(f"{i+1}. {item['url']}" for i, item in enumerate(list(queue)[:10]))
        embed = discord.Embed(title="🎵 Fronta", description=items, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

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

# OSTATNÍ / OTHER

@bot.tree.command(name="verse", description="Random biblický verš")
async def verse_command(interaction: discord.Interaction):
    """Send random Bible verse with daily streak tracking."""
    try:
        user_id = interaction.user.id
        today = datetime.date.today()
        
        # Initialize streak if needed
        if user_id not in verse_streak:
            verse_streak[user_id] = {"count": 0, "last_date": None}
        
        user_streak = verse_streak[user_id]
        
        # Check if user already got verse today
        if user_streak["last_date"] == today:
            streak_count = user_streak["count"]
            selected = random.choice(verses)
            message = f"📖 Už si dnes vzal verš! Tvoje série: **{streak_count}** dní"
            embed = discord.Embed(title="Biblický Verš", description=selected, color=discord.Color.gold())
            embed.add_field(name="🔥 Série", value=message, inline=False)
            await interaction.response.send_message(embed=embed)
            return
        
        # Check if streak continues (yesterday)
        yesterday = today - datetime.timedelta(days=1)
        if user_streak["last_date"] == yesterday:
            # Streak continues!
            user_streak["count"] += 1
        else:
            # Streak broken or first time
            user_streak["count"] = 1
        
        user_streak["last_date"] = today
        streak_count = user_streak["count"]
        
        # Get milestone message
        milestone_msg = ""
        for days in sorted(streak_messages.keys(), reverse=True):
            if streak_count >= days:
                milestone_msg = f"\n\n🎉 {streak_messages[days]}"
                break
        
        selected = random.choice(verses)
        embed = discord.Embed(title="📖 Biblický Verš", description=selected, color=discord.Color.gold())
        embed.add_field(name="🔥 Tvoje série", value=f"**{streak_count}** dní\n{milestone_msg}", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

@bot.tree.command(name="freegames", description="Hry zdarma – Epic Games, Steam")
async def freegames_command(interaction: discord.Interaction):
    """Show free games from Epic Games Store."""
    await interaction.response.defer()
    
    try:
        response = requests.get("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions", timeout=10)
        data = response.json()
        
        games = []
        for elem in data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])[:5]:
            if elem.get("promotions", {}).get("promotionalOffers"):
                games.append(elem.get("title", "Unknown"))
        
        if games:
            desc = "\n".join(f"• {g}" for g in games)
            embed = discord.Embed(title="🎁 Epic Games – Zdarma", description=desc, color=discord.Color.purple())
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Žádné hry zdarma v Epic Games Store")
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba: {str(e)[:100]}")

@bot.tree.command(name="verze", description="Info o verzi botu")
async def verze_command(interaction: discord.Interaction):
    """Show bot version and changelog."""
    try:
        embed = discord.Embed(title="ℹ️ Ježíš Discord Bot", color=discord.Color.gold())
        embed.add_field(name="Verze", value="v2.1.0b – Slash Commands Era", inline=False)
        embed.add_field(name="Co je nového", value="""
✅ Kompletní přepis na slash commands
✅ Czech názvy pro unikalitu
✅ `/yt` místo `/play`
✅ `/další`, `/pauza`, `/pokračuj`, `/zastav`, `/odejdi`, `/fronta`
✅ `/verse`, `/freegames`, `/bless`, `/komandy`, `/diag`
""", inline=False)
        embed.add_field(name="GitHub", value="https://github.com/Braska-botmaker/Chatbot-discord-JESUS", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

@bot.tree.command(name="bless", description="Požehnání pro uživatele")
async def bless_command(interaction: discord.Interaction, user: discord.User = None):
    """Send blessing to user."""
    try:
        target = user or interaction.user
        # Try to use game_blessings if available, fallback to generic blessings
        all_blessings = list(game_blessings.values()) + [
            f"🙏 {target.mention}, Bůh tě požehná v každém kroku!",
            f"✝️ {target.mention}, sila a láska Boží jsou s tebou!",
            f"💫 {target.mention}, přeji ti pokoj a radost v Kristu!",
        ]
        
        selected = random.choice(all_blessings)
        # Add mention if it's a game blessing (doesn't have mention already)
        if target.mention not in selected:
            selected = f"{target.mention}, {selected}"
        
        embed = discord.Embed(description=selected, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

@bot.tree.command(name="komandy", description="Všechny dostupné příkazy")
async def komandy_command(interaction: discord.Interaction):
    """Show all available commands."""
    try:
        embed = discord.Embed(title="📋 Příkazy – Ježíš Discord Bot v2.1.0", color=discord.Color.blue())
        
        embed.add_field(name="🎵 Hudba", value="""
/yt <url> – Přehrávej hudbu z YouTube
/další – Přeskoč písničku
/pauza – Pozastav
/pokračuj – Pokračuj
/zastav – Zastavit a vyčistit frontu
/odejdi – Odejít z voice
/np – Co se hraje
/fronta – Zobraz frontu
/vtest – Test voice
""", inline=False)
        
        embed.add_field(name="📖 Ostatní", value="""
/verze – Info o verzi
/verse – Náhodný biblický verš
/freegames – Hry zdarma (Epic, Steam)
/bless [@user] – Požehnání
/diag – Diagnostika
/komandy – Seznam příkazů
""", inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        try:
            await interaction.response.send_message(f"❌ Chyba: {str(e)[:100]}")
        except:
            pass

@bot.tree.command(name="diag", description="Diagnostika a info o botu")
async def diag_command(interaction: discord.Interaction):
    """Show bot diagnostics."""
    await interaction.response.defer()
    
    embed = discord.Embed(title="🩺 Diagnostika", color=discord.Color.green())
    
    # System info
    machine = platform.machine()
    is_rpi = _is_arm_system()
    embed.add_field(name="💻 Systém", value=f"Machine: {machine}\nARM: {'✅' if is_rpi else '❌'}", inline=True)
    
    # Audio
    ffmpeg_ok = "✅" if has_ffmpeg() else "❌"
    opus_ok = "✅" if HAS_OPUS else "❌"
    nacl_ok = "✅" if HAS_NACL else "❌"
    embed.add_field(name="🔊 Audio", value=f"FFmpeg: {ffmpeg_ok}\nOpus: {opus_ok}\nNaCl: {nacl_ok}", inline=True)
    
    # Voice clients
    voice_count = len(bot.voice_clients)
    embed.add_field(name="🎤 Voice", value=f"Connected: {voice_count}", inline=True)
    
    # Uptime
    if bot.user:
        embed.add_field(name="⏱️ Verze", value="v2.1.0\nSlash Commands Era", inline=True)
    
    await interaction.followup.send(embed=embed)

# ===== SCHEDULED TASKS =====

@tasks.loop(hours=24)
async def send_morning_message():
    """Send morning message at 07:00 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 7 and now.minute < 1:
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="požehnání🙏")
            if channel:
                embed = discord.Embed(title="🌅 Dobré ráno!", description="Nechť tě Bůh požehná v novém dni!", color=discord.Color.orange())
                try:
                    await channel.send(embed=embed)
                except:
                    pass

@tasks.loop(hours=24)
async def send_night_message():
    """Send night message at 20:00 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 20 and now.minute < 1:
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="požehnání🙏")
            if channel:
                embed = discord.Embed(title="🌙 Dobrou noc!", description="Spi v pokoji Kristově. Zítřka tě čeká nový den plný příležitostí.", color=discord.Color.dark_blue())
                try:
                    await channel.send(embed=embed)
                except:
                    pass

@tasks.loop(hours=24)
async def send_free_games():
    """Send free games at 20:10 CET."""
    now = datetime.datetime.now(pytz.timezone("Europe/Prague"))
    if now.hour == 20 and 10 <= now.minute < 11:
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="hry_zdarma💵")
            if channel:
                try:
                    response = requests.get("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions", timeout=10)
                    data = response.json()
                    games = []
                    for elem in data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])[:5]:
                        if elem.get("promotions", {}).get("promotionalOffers"):
                            games.append(elem.get("title", "Unknown"))
                    
                    if games:
                        desc = "\n".join(f"• {g}" for g in games)
                        embed = discord.Embed(title="🎁 Zdarma hry – Epic Games", description=desc, color=discord.Color.purple())
                        await channel.send(embed=embed)
                except:
                    pass

@tasks.loop(minutes=5)
async def voice_watchdog():
    """Monitor voice connections."""
    for guild_id, vc in list((vc.guild.id, vc) for vc in bot.voice_clients):
        if not vc.is_connected():
            _queue_for(guild_id).clear()
            now_playing[guild_id] = None

@tasks.loop(hours=1)
async def clear_recent_announcements():
    """Clear old announcements every hour."""
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

# ===== MAIN =====

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
