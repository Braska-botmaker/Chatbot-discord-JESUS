# bot.py — v2.0.5e – Opraveno voice + všechny chyby (Raspberry Pi Ready)


import discord
from discord.ext import commands, tasks
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
        # Try to patch _inner_connect which is the actual connection method in discord.py 2.x
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
                    
                    # Last attempt or non-4006 error - raise
                    if is_4006:
                        print(f"[RPi patch] 4006 error persisted after {max_retries} _inner_connect attempts")
                    raise
            
            return None
        
        discord.voice_client.VoiceClient._inner_connect = patched_inner_connect
        print("[RPi patch] ✅ Applied to VoiceClient._inner_connect - 4006 retry logic active")
    except Exception as e:
        print(f"[RPi patch] ⚠️ Warning: Failed to patch _inner_connect: {e}")
        print("[RPi patch] Note: VoiceClient.connect() wrapper will still provide 4006 resilience")

_patch_voice_client_for_rpi()

# Additional patch: Monitor and handle 4006 errors in the voice connection loop
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
            extended_timeout = 30.0  # Extended timeout for UDP handshake on RPi
            base_delay = 0.5
            
            # Use extended timeout for ARM systems
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
                    # Timeout on connect - likely UDP handshake issue, retry with delay
                    if retry_count < max_retries - 1:
                        delay = base_delay * (1.5 ** retry_count)  # Exponential: 0.5s, 0.75s, 1.1s, 1.7s
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
                    
                    # Final attempt or non-4006 error
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

bot = commands.Bot(command_prefix="!", intents=intents)

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
    # guild-specific namespace
    return db.setdefault(str(gid), {}).setdefault(key, default)



music_queues = {}
now_playing = {}
bot_loop = None

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

# RPi voice protocol fix: Lower audio quality to reduce UDP packet size
FFMPEG_OPTIONS_RPi = "-vn -ac 1 -b:a 96k -bufsize 128k"  # Smaller frames for ARM

def get_ffmpeg_options():
    """Return FFmpeg options optimized for platform (RPi uses lower bitrate)."""
    is_rpi = _is_arm_system()
    return FFMPEG_OPTIONS_RPi if is_rpi else FFMPEG_OPTIONS

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def _headers_str_from_info(info: dict) -> str:
    """
    YouTube (a další) vyžadují hlavičky z yt-dlp, jinak FFmpeg dostane 403.
    Vrátí string pro FFmpeg: 'Key: Value\\r\\nKey: Value\\r\\n'
    """
    headers = info.get("http_headers") or {}
    return "".join(f"{k}: {v}\r\n" for k, v in headers.items())

def make_before_options(headers_str: str) -> str:
    """Složí before_options pro FFmpeg včetně HTTP hlaviček (správné escapování)."""
    if not headers_str:
        return FFMPEG_RECONNECT
    safe = headers_str.replace('"', r'\"')
    return f'{FFMPEG_RECONNECT} -headers "{safe}"'

def ytdlp_extract(url: str):
    """Extrahuje URL a headers z YouTube/streamu. Retry na timeout."""
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
                
                # Zajisti, že jsou všechny potřebné klíče
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
                time.sleep(1)  # OPRAVA: time.sleep místo asyncio.sleep
            continue
    
    raise last_err

def _queue_for(guild_id: int) -> deque:
    if guild_id not in music_queues:
        music_queues[guild_id] = deque()
    return music_queues[guild_id]

voice_locks = {}
last_voice_channel = {}
reconnect_backoff = {}

def _guild_lock(gid: int) -> asyncio.Lock:
    if gid not in voice_locks:
        voice_locks[gid] = asyncio.Lock()
    return voice_locks[gid]

async def wait_until_connected(vc: Optional[discord.VoiceClient], tries: int = 15, delay: float = 0.3) -> bool:
    """Opakovaně zkontroluje, zda je voice skutečně připojený s progressivním čekáním."""
    for i in range(tries):
        if vc and vc.is_connected():
            await asyncio.sleep(0.1)  # krátké stabilizační čekání
            return True
        wait_time = delay * (i + 1) if i < 3 else delay * 3  # up to 3x delay
        await asyncio.sleep(wait_time)
    return False

async def ensure_voice_by_guild(guild: discord.Guild, *, text_channel: Optional[discord.TextChannel] = None) -> Optional[discord.VoiceClient]:
    """Zkusí připojit/move bota do naposledy známého voice kanálu daného serveru."""
    ch_id = last_voice_channel.get(guild.id)
    if not ch_id:
        if text_channel:
            await text_channel.send("❗ Neznám cílový voice kanál pro reconnect (spusť nejdřív `!play` v tvém kanálu).")
        return None

    ch = guild.get_channel(ch_id)
    if not isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
        if text_channel:
            await text_channel.send("❗ Cílový voice kanál už neexistuje.")
        return None

    async with _guild_lock(guild.id):
        vc = guild.voice_client
        try:
            me = guild.me
            perms = ch.permissions_for(me)
            if not (perms.connect and perms.speak):
                if text_channel:
                    await text_channel.send("❗ Chybí práva **Connect**/**Speak** do uloženého kanálu.")
                return None

            # 1. Pokud máme vc, zkontroluj stav
            if vc:
                if vc.is_connected():
                    if vc.channel == ch:
                        return vc
                    else:
                        # Jiný kanál – přesuneme se
                        await asyncio.wait_for(vc.move_to(ch), timeout=8)
                        await asyncio.sleep(0.3)
                        if not await wait_until_connected(vc, tries=8, delay=0.3):
                            if text_channel:
                                await text_channel.send("⚠️ Voice se nenastabilizoval. Zkus to znovu.")
                            return None
                        return vc
                else:
                    # vc není připojen – odpojíme a reconnectujeme
                    try:
                        await asyncio.wait_for(vc.disconnect(), timeout=3)
                    except Exception:
                        pass
                    await asyncio.sleep(0.3)
                    vc = None

            # 2. Nový connect
            if not vc or not vc.is_connected():
                try:
                    vc = await asyncio.wait_for(ch.connect(self_deaf=True), timeout=30)
                except discord.ClientException as e:
                    error_str = str(e)
                    if "Already connected" in error_str:
                        # Force disconnect a znovu
                        print(f"[reconnect] Already connected detected, force disconnect...")
                        vc = guild.voice_client
                        if vc:
                            try:
                                await asyncio.wait_for(vc.disconnect(), timeout=3)
                            except Exception as de:
                                print(f"[reconnect] Disconnect failed: {de}")
                        await asyncio.sleep(0.5)
                        vc = await asyncio.wait_for(ch.connect(self_deaf=True), timeout=30)
                    else:
                        raise
                except TypeError:
                    vc = await asyncio.wait_for(ch.connect(), timeout=30)
                except asyncio.TimeoutError as te:
                    print(f"[reconnect] Timeout on connect: {te}")
                    raise

            await asyncio.sleep(0.3)
            if not await wait_until_connected(vc, tries=8, delay=0.3):
                if text_channel:
                    await text_channel.send("⚠️ Voice se nenastabilizoval. Zkus to znovu.")
                return None
                
            return vc
        except asyncio.TimeoutError:
            if text_channel:
                await text_channel.send("⚠️ Reconnect timeoutoval. Server je zaneprázdněn.")
            print(f"[reconnect] Timeout")
            return None
        except Exception as e:
            print(f"[reconnect] {e}")
            if text_channel:
                try:
                    await text_channel.send(f"❗ Reconnect selhal: `{type(e).__name__}: {e}`")
                except Exception:
                    pass
            return None
# --------------------------------------------------------------------

async def play_next(guild: discord.Guild, text_channel: discord.TextChannel):
    """Interní přehrávací smyčka – vezme další položku z fronty a pustí ji."""
    q = _queue_for(guild.id)
    if not q:
        now_playing.pop(guild.id, None)
        return

    track = q.popleft()
    now_playing[guild.id] = track

    vc = guild.voice_client
    if not (vc and vc.is_connected()):
        vc = await ensure_voice_by_guild(guild, text_channel=text_channel)
        if not (vc and vc.is_connected()):
            now_playing.pop(guild.id, None)
            q.appendleft(track)  # vrátit do fronty
            return

    before = make_before_options(track.get("headers", ""))
    source = None
    
    # Pokus se získat audio
    for attempt in range(2):
        try:
            source = await discord.FFmpegOpusAudio.from_probe(
                track["url"],
                before_options=before,
                options="-vn"
            )
            break
        except AttributeError:
            # FFmpegOpusAudio není dostupné, použij PCMAudio
            try:
                source = discord.FFmpegPCMAudio(
                    track["url"],
                    before_options=before,
                    options=get_ffmpeg_options()  # Use platform-optimized options
                )
                break
            except Exception as e:
                if attempt == 1:
                    msg = f"❗ FFmpeg chyba pro **{track.get('title','?')}**: `{type(e).__name__}: {e}`"
                    print(f"[from_probe fallback] {e}")
                    try:
                        await text_channel.send(msg)
                    except Exception:
                        pass
                    return await play_next(guild, text_channel)
                await asyncio.sleep(1)
        except Exception as e:
            if attempt == 1:
                msg = f"❗ FFmpeg/stream chyba pro **{track.get('title','?')}**: `{type(e).__name__}: {e}`"
                print(f"[from_probe] {e}")
                try:
                    await text_channel.send(msg)
                except Exception:
                    pass
                return await play_next(guild, text_channel)
            await asyncio.sleep(1)

    if not source:
        try:
            await text_channel.send(f"❗ Nepodařilo se vytvoři audio zdroj pro **{track.get('title','?')}**")
        except Exception:
            pass
        return await play_next(guild, text_channel)

    def after_play(err):
        if err:
            print(f"[FFmpeg error] {err}")
        if bot_loop is None:
            return
        fut = asyncio.run_coroutine_threadsafe(play_next(guild, text_channel), bot_loop)
        try:
            fut.result()
        except Exception as ee:
            print(f"[after_play] {ee}")

    try:
        vc.play(source, after=after_play)
    except discord.ClientException as e:
        error_msg = str(e)
        if "Not connected to voice" in error_msg:
            vc = await ensure_voice_by_guild(guild, text_channel=text_channel)
            if vc and vc.is_connected():
                try:
                    vc.play(source, after=after_play)
                except Exception as e2:
                    try:
                        await text_channel.send(f"❗ Nepodařilo se spustit přehrávání: `{type(e2).__name__}: {e2}`")
                    except Exception:
                        pass
                    return await play_next(guild, text_channel)
            else:
                try:
                    await text_channel.send("⚠️ Nemohu se znovu připojit do voice. Zkus !play znovu.")
                except Exception:
                    pass
                return
        elif "Already connected" in error_msg or "is not playable" in error_msg:
            # Pokus znovu s dalším trackem
            print(f"[play] {error_msg} – skipuji a hraju další")
            return await play_next(guild, text_channel)
        else:
            try:
                await text_channel.send(f"❗ Nepodařilo se spustit přehrávání: `{type(e).__name__}: {e}`")
            except Exception:
                pass
            return await play_next(guild, text_channel)
    except Exception as e:
        # Fallback pro jakékoli jiné chyby
        print(f"[play_next exception] {type(e).__name__}: {e}")
        try:
            await text_channel.send(f"❗ Neznámá chyba při přehrávání: `{type(e).__name__}`")
        except Exception:
            pass
        return await play_next(guild, text_channel)

    await asyncio.sleep(1.0)
    if not vc.is_playing() and not vc.is_paused():
        try:
            await text_channel.send("❗ Přehrávání se nespustilo (možný 403/geo/stream problem). Zkus jiný odkaz.")
        except Exception:
            pass
        return await play_next(guild, text_channel)

    try:
        await text_channel.send(f"▶️ **Now playing:** {track['title']} \n🔗 {track['webpage_url']}")
    except Exception:
        pass


CET = pytz.timezone("Europe/Prague")


def get_channel_by_name(guild, name):
    return discord.utils.get(guild.text_channels, name=name)

verses = [
    "„Bůh je láska, a kdo zůstává v lásce, zůstává v Bohu a Bůh v něm.“ (1 Jan 4,16)",
    "„Pán je můj pastýř, nebudu mít nedostatek.“ (Žalm 23,1–2)",
    "„Všechno mohu v Kristu, který mi dává sílu.“ (Filipským 4,13)",
    "„Neboj se, neboť já jsem s tebou.“ (Izajáš 41,10)",
    "„Žádejte, a bude vám dáno.“ (Matouš 7,7)",
    "„Ať se vaše srdce nechvějí!“ (Jan 14,1)",
    "„Ve světě máte soužení, ale důvěřujte.“ (Jan 16,33)",
    "„Milujte své nepřátele.“ (Lukáš 6,27)",
    "„Radujte se v Pánu vždycky!“ (Filipským 4,4)",
    "„Láska je trpělivá, láska je dobrotivá.“ (1 Korintským 13,4)",
    "„Požehnaný člověk, který doufá v Hospodina.“ (Jeremjáš 17,7)",
    "„Věř v Pána celým svým srdcem.“ (Přísloví 3,5)",
    "„Neboj se, jen věř.“ (Marek 5,36)",
    "„Já jsem světlo světa.“ (Jan 8,12)",
    "„Boží milosrdenství je věčné.“ (Žalm 136,1)",
    "„Nebuďte úzkostliví o svůj život.“ (Matouš 6,25)",
    "„Modlete se bez přestání.“ (1 Tesalonickým 5,17)",
    "„On uzdravuje ty, kdo mají zlomené srdce.“ (Žalm 147,3)",
    "„Já jsem s vámi po všechny dny.“ (Matouš 28,20)",
    "„Pane, nauč nás modlit se.“ (Lukáš 11,1)",
    "„Hledejte nejprve Boží království.“ (Matouš 6,33)",
    "„Tvá víra tě uzdravila.“ (Marek 5,34)",
    "„Buď silný a odvážný.“ (Jozue 1,9)",
    "„Žádná zbraň, která se proti tobě připraví, neuspěje.“ (Izajáš 54,17)",
    "„Jsem cesta, pravda i život.“ (Jan 14,6)",
    "„Pán je blízko všem, kdo ho vzývají.“ (Žalm 145,18)",
    "„Odpouštějte, a bude vám odpuštěno.“ (Lukáš 6,37)",
    "„Každý dobrý dar je shůry.“ (Jakub 1,17)",
    "„S radostí budete čerpat vodu ze studnic spásy.“ (Izajáš 12,3)",
    "„Neboť u Boha není nic nemožného.“ (Lukáš 1,37)",
    "„Hospodin je moje světlo a moje spása.“ (Žalm 27,1)",
    "„Milost vám a pokoj od Boha Otce našeho.“ (Filipským 1,2)",
    "„Ježíš Kristus je tentýž včera, dnes i navěky.“ (Židům 13,8)",
    "„Bůh sám bude s nimi.“ (Zjevení 21,3)",
    "„Kdo v něj věří, nebude zahanben.“ (Římanům 10,11)",
    "„Ať se radují všichni, kdo se k tobě utíkají.“ (Žalm 5,12)",
    "„Jeho milosrdenství je nové každé ráno.“ (Pláč 3,23)",
    "„Dej nám dnes náš denní chléb.“ (Matouš 6,11)",
    "„Neskládejte poklady na zemi.“ (Matouš 6,19)",
    "„Zůstaňte v mé lásce.“ (Jan 15,9)"
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
}

@bot.event
async def on_ready():
    global bot_loop
    bot_loop = asyncio.get_running_loop()
    print(f"Bot je přihlášen jako {bot.user}")
    send_morning_message.start()
    send_night_message.start()
    send_free_games.start()
    clear_recent_announcements.start()
    voice_watchdog.start()

@bot.event
async def on_member_join(member):
    channel = get_channel_by_name(member.guild, "požehnání🙏")
    if channel and channel.permissions_for(member.guild.me).send_messages:
        await channel.send(f"Vítej, {member.mention}, nový bratře v Kristu!")

@bot.event
async def on_presence_update(before, after):
    def is_game_activity(activity):
        return activity.type == discord.ActivityType.playing

    before_game = next((a for a in before.activities if is_game_activity(a)), None)
    after_game = next((a for a in after.activities if is_game_activity(a)), None)

    if before_game is None and after_game is not None:
        game_name = after_game.name
        key = (after.id, game_name)
        if key in recently_announced_games:
            return
        recently_announced_games.add(key)

        message = game_blessings.get(game_name, "Modlíme se za tebe, bratře v Kristu 🙏. Užij si tuto videohru.")
        channel = get_channel_by_name(after.guild, "požehnání🙏")
        if channel and channel.permissions_for(after.guild.me).send_messages:
            await channel.send(f"{after.mention} právě hraje **{game_name}**. {message}")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel != before.channel:
        members_in_channel = [m for m in after.channel.members if not m.bot]
        if len(members_in_channel) >= 2:
            games = [m.activity.name for m in members_in_channel if m.activity and isinstance(m.activity, discord.Game)]
            if games and len(games) >= 2 and all(g == games[0] for g in games):
                game = games[0]
                mentions = ", ".join(m.mention for m in members_in_channel)
                channel = get_channel_by_name(member.guild, "požehnání🙏")
                if channel and channel.permissions_for(member.guild.me).send_messages:
                    await channel.send(f"{mentions} se spojili ve voice chatu a společně hrají **{game}** 🎮. Ať vás provází Pán! ✝️")

# Ranní zprávy
@tasks.loop(time=datetime.time(hour=7, minute=0, tzinfo=CET))
async def send_morning_message():
    verse = random.choice(verses)
    for guild in bot.guilds:
        channel = get_channel_by_name(guild, "požehnání🙏")
        if channel and channel.permissions_for(guild.me).send_messages:
            await channel.send(f"@everyone Dobré ráno, bratři a sestry v Kristu! 🌞\n📖 Dnešní verš:\n> {verse}")

# Noční zprávy
@tasks.loop(time=datetime.time(hour=20, minute=0, tzinfo=CET))
async def send_night_message():
    for guild in bot.guilds:
        channel = get_channel_by_name(guild, "požehnání🙏")
        if channel and channel.permissions_for(guild.me).send_messages:
            await channel.send("@everyone Dobrou noc a požehnaný spánek, bratři a sestry v Kristu. 🙏🌙")

# Získání her zdarma
def get_free_games():
    """Collect free games from multiple sources: Epic, Steam, PlayStation Blog (PlayStation Plus posts).

    Returns a list of dicts with 'title' and 'url'. Deduplicates by (title, url).
    """
    games = []
    seen = set()

    # Epic Games (existing behaviour)
    try:
        epic_api = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        response = requests.get(epic_api, timeout=5)
        data = response.json()
        for game in data["data"]["Catalog"]["searchStore"]["elements"]:
            try:
                if game["price"]["totalPrice"]["discountPrice"] == 0:
                    title = game.get("title") or "Unknown"
                    url = f"https://store.epicgames.com/p/{game['catalogNs']['mappings'][0]['pageSlug']}"
                    key = (title, url)
                    if key not in seen:
                        seen.add(key)
                        games.append({"title": title, "url": url})
            except Exception:
                continue
    except Exception as e:
        print(f"[ERROR] Epic Games API selhalo: {e}")

    # Steam — scrape search results filtered for free games
    try:
        steam_url = "https://store.steampowered.com/search/?filter=free"
        r = requests.get(steam_url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text
        # find rows: <a ... class="search_result_row" href="..."> ... <span class="title">Title</span>
        pattern = re.compile(r'<a[^>]+class="search_result_row[^"]*"[^>]+href="(?P<href>[^"]+)"[^>]*>.*?<span class="title">(?P<title>.*?)</span>', re.S)
        count = 0
        for m in pattern.finditer(html):
            title = re.sub(r"\s+", " ", m.group('title')).strip()
            title = html_unescape(title)
            href = m.group('href').split('?')[0]
            key = (title, href)
            if key not in seen:
                seen.add(key)
                games.append({"title": title, "url": href})
                count += 1
            if count >= 12:
                break
    except Exception as e:
        print(f"[ERROR] Steam scrape selhalo: {e}")

    # PlayStation Blog — PlayStation Plus tag feed (posts announcing monthly games)
    try:
        ps_feed = "https://blog.playstation.com/tag/playstation-plus/feed/"
        r = requests.get(ps_feed, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(r.content)
                # iterate <item> elements
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
                print(f"[ERROR] PlayStation feed parse selhalo: {e}")
    except Exception as e:
        print(f"[ERROR] PlayStation feed selhalo: {e}")

    return games

# Hry zdarma
@tasks.loop(time=datetime.time(hour=20, minute=10, tzinfo=CET))
async def send_free_games():
    free_games = get_free_games()
    if not free_games:
        return
    message = "**🎮 Dnešní hry zdarma (Epic / Steam / PlayStation):**\n" + "\n".join([f"- [{g['title']}]({g['url']})" for g in free_games])
    for guild in bot.guilds:
        channel = get_channel_by_name(guild, "hry_zdarma💵")
        if channel and channel.permissions_for(guild.me).send_messages:
            await channel.send(message)

# Příkaz !hryzdarma
@bot.command(name="hryzdarma")
async def hry_zdarma(ctx):
    free_games = get_free_games()
    if not free_games:
        await ctx.send("Momentálně nejsou k dispozici žádné hry zdarma. 🙁")
        return
    message = "**🎮 Aktuální hry zdarma (Epic / Steam / PlayStation):**\n" + "\n".join([f"- [{g['title']}]({g['url']})" for g in free_games])
    await ctx.send(message)


def _today_date_str():
    return datetime.datetime.now(tz=CET).strftime("%Y-%m-%d")

@bot.command(name="verš")
async def vers_command(ctx):
    verse = random.choice(verses)
    
    db = _load_data()
    st = _g(db, ctx.guild.id, "streaks", {})
    uid = str(ctx.author.id)
    user = st.get(uid, {"last": "", "count": 0})
    today = _today_date_str()

    if user["last"] != today:
        
        try:
            last = datetime.datetime.strptime(user["last"], "%Y-%m-%d").date() if user["last"] else None
        except Exception:
            last = None
        d_today = datetime.datetime.strptime(today, "%Y-%m-%d").date()
        if last and (d_today - last).days == 1:
            user["count"] = user.get("count", 0) + 1
        else:
            user["count"] = 1
        user["last"] = today
        st[uid] = user
        await _save_data(db)

    emb = discord.Embed(title="📖 Dnešní verš", description=f"> {verse}", color=discord.Color.blue())
    emb.set_footer(text=f"Streak: {user['count']} 🔥  (přijď zítra pro další bod)")
    await ctx.send(embed=emb)


@tasks.loop(hours=1)
async def clear_recent_announcements():
    recently_announced_games.clear()

@tasks.loop(seconds=30)
async def voice_watchdog():
    """Když je co hrát (queue/now_playing) a nejsme připojeni, zkus za minutu reconnect do posledního kanálu."""
    now = time.time()
    for guild in list(bot.guilds):
        q = _queue_for(guild.id)
        if not (q or now_playing.get(guild.id)):
            continue
        vc = guild.voice_client
        if vc and vc.is_connected():
            continue
        last = reconnect_backoff.get(guild.id, 0.0)
        if now - last < 90:  # throttle na 90 sekund
            continue
        reconnect_backoff[guild.id] = now
        try:
            await ensure_voice_by_guild(guild)
        except Exception as e:
            print(f"[watchdog] reconnect failed: {e}")

# ================= HUDEBNÍ PŘÍKAZY =================

async def ensure_voice(ctx) -> Optional[discord.VoiceClient]:
    """Připojí bota do stejného voice jako autor příkazu, s robustním error handlingem."""
    if ctx.author.voice and isinstance(ctx.author.voice.channel, discord.StageChannel):
        await ctx.send("⚠️ Jsi v **Stage** kanálu. Dejte botovi *Invite to Speak* nebo použij normální voice kanál.")
        return None
        
    if not (ctx.author.voice and ctx.author.voice.channel):
        await ctx.send("Nejprve se připoj do voice kanálu. 🎧")
        return None

    ch = ctx.author.voice.channel
    me = ctx.guild.me
    perms = ch.permissions_for(me)

    missing = []
    if not perms.connect:
        missing.append("Connect")
    if not perms.speak:
        missing.append("Speak")
    if missing:
        await ctx.send("Nemohu se připojit: chybí oprávnění: **" + ", ".join(missing) + "**")
        return None

    if ch.user_limit and len([m for m in ch.members if not m.bot]) >= ch.user_limit:
        await ctx.send("Nemohu se připojit: kanál je plný (user limit).")
        return None

    if not HAS_NACL:
        await ctx.send("❗ Nelze se připojit: chybí **PyNaCl** v běžícím prostředí.\n"
                       "Nainstaluj do venv:\n`pip install -U PyNaCl`")
        return None
    if not HAS_OPUS:
        await ctx.send("❗ Nelze se připojit: nenačtená knihovna **Opus**.\n"
                       "Na Linux měj `libopus0` (`sudo apt install -y libopus0`).")
        return None

    async with _guild_lock(ctx.guild.id):
        vc = ctx.guild.voice_client
        try:
            for attempt in range(3):
                try:
                    # 1. Pokud máme nějaký vc objekt, zkontroluj stav
                    if vc:
                        if vc.is_connected():
                            # Už jsme připojeni
                            if vc.channel == ch:
                                # Stejný kanál – super!
                                last_voice_channel[ctx.guild.id] = ch.id
                                return vc
                            else:
                                # Jiný kanál – přesuneme se
                                await asyncio.wait_for(vc.move_to(ch), timeout=8)
                                if await wait_until_connected(vc, tries=5, delay=0.3):
                                    last_voice_channel[ctx.guild.id] = ch.id
                                    return vc
                        else:
                            # vc existuje ale není připojen – reconnectuj
                            try:
                                await asyncio.wait_for(vc.disconnect(), timeout=3)
                            except Exception:
                                pass
                            await asyncio.sleep(0.3)
                            vc = None
                    
                    # 2. Nový connect (extended timeout for UDP handshake on RPi)
                    if not vc or not vc.is_connected():
                        try:
                            print(f"[voice] Attempting ch.connect(self_deaf=True) with 30s timeout...")
                            vc = await asyncio.wait_for(ch.connect(self_deaf=True), timeout=30)
                            print(f"[voice] ch.connect() succeeded")
                        except discord.ClientException as e:
                            error_str = str(e)
                            print(f"[voice] ClientException: {error_str}")
                            if "Already connected" in error_str:
                                print(f"[voice] Already connected detected, force disconnect...")
                                vc = ctx.guild.voice_client
                                if vc:
                                    try:
                                        await asyncio.wait_for(vc.disconnect(), timeout=3)
                                    except Exception as de:
                                        print(f"[voice] Disconnect failed: {de}")
                                await asyncio.sleep(0.5)
                                print(f"[voice] Retrying ch.connect() after force disconnect...")
                                vc = await asyncio.wait_for(ch.connect(self_deaf=True), timeout=30)
                                print(f"[voice] Retry succeeded")
                            else:
                                raise
                        except TypeError:
                            print(f"[voice] TypeError on connect, trying without self_deaf")
                            vc = await asyncio.wait_for(ch.connect(), timeout=30)
                        except asyncio.TimeoutError:
                            print(f"[voice] Timeout on ch.connect (attempt {attempt+1}/3)")
                            if attempt < 2:
                                print(f"[voice] Retrying with 3s delay...")
                                await asyncio.sleep(3)
                                continue
                            raise
                    
                    # 3. Čekej na stabilizaci
                    if await wait_until_connected(vc, tries=10, delay=0.3):
                        last_voice_channel[ctx.guild.id] = ch.id
                        return vc
                    
                    if attempt < 2:
                        await asyncio.sleep(1)
                        
                except asyncio.TimeoutError:
                    if attempt == 2:
                        raise
                    print(f"[voice] Timeout, retrying (attempt {attempt+1}/3)...")
                    await asyncio.sleep(3)
                except discord.ClientException as ce:
                    if "Already connected" in str(ce) and attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    raise
                    
            await ctx.send("⚠️ Nepodařilo se stabilně připojit do voice. Zkus to znovu nebo změň kanál.")
            return None
            
        except discord.Forbidden:
            await ctx.send("❗ Nemohu se připojit: nedostatek oprávnění.")
            return None
        except asyncio.TimeoutError as te:
            print(f"[voice] asyncio.TimeoutError after all retries: {te}")
            await ctx.send("⚠️ Připojení vypršelo timeoutem (UDP handshake problém). Zkus to za chvíli znovu.")
            return None
        except Exception as e:
            print(f"[voice] Unhandled exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❗ Nemohu se připojit do voice: `{type(e).__name__}: {e}`")
            return None

@bot.command(name="play")
async def play_cmd(ctx, url: str):
    """!play <YouTube URL> — přidá skladbu do fronty a spustí přehrávání."""
    global _yt_dlp
    if _yt_dlp is None:
        try:
            import yt_dlp as _yt_dlp  # type: ignore
        except Exception:
            await ctx.send("❗ Nelze přehrát: chybí `yt-dlp`. Nainstaluj do venv:\n"
                           "`/opt/discordbot/.venv/bin/python -m pip install -U yt-dlp`")
            return

    if not has_ffmpeg():
        await ctx.send("❗ Nelze přehrát: ffmpeg není v systému. Nainstaluj:\n`sudo apt install -y ffmpeg`")
        return

    vc = await ensure_voice(ctx)
    if not vc:
        return
    try:
        track = ytdlp_extract(url)
    except Exception as e:
        await ctx.send("Nepodařilo se načíst audio. Zkontroluj odkaz nebo yt-dlp.")
        print(f"[yt-dlp] {e}")
        return

    q = _queue_for(ctx.guild.id)
    was_idle = not (vc.is_playing() or vc.is_paused())
    q.append(track)

    if was_idle:
        await play_next(ctx.guild, ctx.channel)
    else:
        await ctx.send(f"➕ Zařazeno do fronty: **{track['title']}**")

@bot.command(name="skip")
async def skip_cmd(ctx):
    vc = ctx.guild.voice_client
    if not vc or not vc.is_connected():
        await ctx.send("Nejsem ve voice.")
        return
    if vc.is_playing() or vc.is_paused():
        vc.stop()
        await ctx.send("⏭️ Skip.")
    else:
        await ctx.send("Nic nehraje.")

@bot.command(name="pause")
async def pause_cmd(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_playing():
        vc.pause(); await ctx.send("⏸️ Pause.")
    else:
        await ctx.send("Nic nehraje.")

@bot.command(name="resume")
async def resume_cmd(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_paused():
        vc.resume(); await ctx.send("▶️ Resume.")
    else:
        await ctx.send("Není co obnovit.")

@bot.command(name="stop")
async def stop_cmd(ctx):
    vc = ctx.guild.voice_client
    if not vc:
        await ctx.send("Nejsem ve voice.")
        return
    q = _queue_for(ctx.guild.id)
    q.clear()
    if vc.is_playing() or vc.is_paused():
        vc.stop()
    await ctx.send("⏹️ Stop & fronta vyčištěna.")

@bot.command(name="leave")
async def leave_cmd(ctx):
    vc = ctx.guild.voice_client
    if vc and vc.is_connected():
        q = _queue_for(ctx.guild.id); q.clear()
        now_playing.pop(ctx.guild.id, None)
        await vc.disconnect()
        await ctx.send("👋 Odpojeno z voice.")
    else:
        await ctx.send("Nejsem ve voice.")

@bot.command(name="np")
async def nowplaying_cmd(ctx):
    track = now_playing.get(ctx.guild.id)
    if not track:
        await ctx.send("Nic nehraje.")
    else:
        await ctx.send(f"🎶 **Now playing:** {track['title']} \n🔗 {track['webpage_url']}")

@bot.command(name="mqueue")
async def queue_list_cmd(ctx):
    """Výpis fronty (prvních 10 položek)."""
    q = list(_queue_for(ctx.guild.id))
    if not q:
        await ctx.send("Fronta je prázdná.")
        return
    lines = []
    for i, t in enumerate(q[:10], 1):
        lines.append(f"{i}. {t['title']}")
    more = f"\n… a {len(q)-10} dalších" if len(q) > 10 else ""
    await ctx.send("📜 **Fronta:**\n" + "\n".join(lines) + more)

@bot.command(name="diag")
async def diag_cmd(ctx):
    import sys
    import platform
    ch = ctx.author.voice.channel if (ctx.author.voice and ctx.author.voice.channel) else None
    me = ctx.guild.me
    perms = ch.permissions_for(me) if ch else None
    try:
        import yt_dlp  # noqa
        ytdlp_ok = True
    except Exception:
        ytdlp_ok = False
    
    # Check if we're on Raspberry Pi
    is_rpi = _is_arm_system()
    rpi_label = " 🥧 (Raspberry Pi)" if is_rpi else ""
    
    await ctx.send(
        "🔧 **Diag**\n"
        f"Python: `{sys.executable}` v{sys.version.split()[0]}\n"
        f"Platform: `{platform.system()} {platform.machine()}{rpi_label}`\n"
        f"yt-dlp: {'✅ OK' if ytdlp_ok else '❌ NE'}\n"
        f"PyNaCl: {'✅ OK' if HAS_NACL else '❌ NE'}\n"
        f"Opus loaded: {'✅ OK' if HAS_OPUS else '❌ NE'}\n"
        f"ffmpeg: `{shutil.which('ffmpeg') or '❌ nenalezeno'}`\n"
        f"Voice: `{ch.name if ch else '—'}` | "
        f"{'✔️ connect' if (perms and perms.connect) else '❌ connect'}, "
        f"{'✔️ speak' if (perms and perms.speak) else '❌ speak'}\n\n"
        f"💡 **Tip:** Máš problém? Zkontroluj `/FAQ.md` nebo spusť `python validate_setup.py`"
    )

@bot.command(name="vtest")
async def vtest_cmd(ctx):
    vc = await ensure_voice(ctx)
    if not vc:
        return

    if not await wait_until_connected(vc, tries=10, delay=0.3):
        vc = await ensure_voice_by_guild(ctx.guild, text_channel=ctx.channel)
        if not (vc and vc.is_connected()):
            await ctx.send("⚠️ Voice session se nepodařilo stabilizovat. Zkus jiný kanál nebo znovu připojit.")
            return

    try:
        src = discord.FFmpegPCMAudio(
            "sine=frequency=440:sample_rate=48000:duration=3",
            before_options="-f lavfi",
            options=""
        )
        try:
            vc.play(src)
        except discord.ClientException as e:
            if "Not connected to voice" in str(e):
                vc = await ensure_voice_by_guild(ctx.guild, text_channel=ctx.channel)
                if not (vc and vc.is_connected()):
                    await ctx.send("❗ FFmpeg test selhal: Not connected to voice (po opakování).")
                    return
                vc.play(src)
            else:
                await ctx.send(f"❗ FFmpeg test selhal: `{type(e).__name__}: {e}`")
                return
        await ctx.send("🔊 Test tón 3s…")
    except Exception as e:
        await ctx.send(f"❗ FFmpeg test selhal: `{type(e).__name__}: {e}`")


BLESS_SHORT = [
    "Ať tě Pán vede k radosti a pokoji. ✝️",
    "Ať dnes potkáš dobro a neseš ho dál. 🌟",
    "Ať tvoje slova léčí, ne zraňují. 🕊️",
    "Ať se tvé srdce naplní odvahou i něhou. ❤️",
    "Ať máš moudrost v rozhodování a klid v bouři. 🌊",
]

@bot.command(name="pozehnani")
async def pozehnani_cmd(ctx, user: discord.Member=None):
    target = user or ctx.author
    text = random.choice(BLESS_SHORT)
    emb = discord.Embed(title="🙏 Požehnání", description=f"{target.mention}\n{text}", color=discord.Color.teal())
    await ctx.send(embed=emb)


# --- VERZE ---
@bot.command(name="verze")
async def verze_cmd(ctx):
    embed = discord.Embed(
        title="📌 Aktuální verze bota",
        description="Informace o posledním updatu",
        color=discord.Color.blue()
    )
    embed.add_field(name="Verze", value="**v2.0.5e 🔧 – Plně funkční & RPi optimalizovaný**", inline=False)
    embed.add_field(
        name="Co je nového v v2.0.5e",
        value=(
            "🎯 **4006 OPRAVENO:** Voice konektivita teď funguje na RPi!\n"
            "✅ Exponential backoff retry: 0.5s → 0.75s → 1.1s → 1.7s\n"
            "✅ Extended timeout: 30s pro UDP handshake\n"
            "✅ FFmpeg optimalizace: 96kbps na RPi (menší pakety)\n"
            "✅ Diagnostika: !diag a !vtest pro troubleshooting\n"
            "✅ Stability: Voice watchdog pro automatické reconnect\n\n"
            "🧪 Příkazy: `!vtest`, `!diag`, `!verze`"
        ),
        inline=False
    )
    embed.add_field(
        name="Příkazy",
        value=(
            "`!play <URL>` – YouTube přehrávání\n"
            "`!skip` `!pause` `!stop` `!leave` `!np` `!mqueue`\n"
            "`!verš` – Denní biblický verš se streakem 🔥\n"
            "`!pozehnani` – Krátké požehnání\n"
            "`!hryzdarma` – Hry zdarma\n"
            "`!diag` – Diagnostika\n"
            "`!vtest` – Voice test"
        ),
        inline=False
    )
    embed.add_field(
        name="Dokumentace",
        value=(
            "📖 **README.md** – Úvod a přehled\n"
            "⚡ **RYCHLY_START.md** – Spuštění v 5 minut\n"
            "🥧 **INSTALACE.md** – RPi setup (systemd, autostart)\n"
            "🩺 **CHYBY.md** – Troubleshooting a FAQ"
        ),
        inline=False
    )
    embed.set_footer(text="Váš věrný bot ✝️ | v2.0.5e | discord.py 2.0+")
    await ctx.send(embed=embed)


# --- COMMANDS ---
@bot.command(name="commands")
async def commands_cmd(ctx):
    embed = discord.Embed(
        title="📖 Dostupné příkazy",
        description="Seznam toho, co všechno bot umí:",
        color=discord.Color.green()
    )
    embed.add_field(
        name="🎵 Hudba",
        value="`!play <url>`\n`!skip` `!pause` `!stop` `!leave` `!mqueue`",
        inline=False
    )
    embed.add_field(
        name="ℹ️ Ostatní",
        value=(
            "`!verze` – aktuální verze bota\n"
            "`!verš` – náhodný biblický verš (se streakem 🔥)\n"
            "`!pozehnani @uživatel` – krátké požehnání\n"
            "`!hryzdarma` – seznam free her"
        ),
        inline=False
    )
    embed.set_footer(text="Tip: Použij !verš každý den a sbírej streak 🔥")
    await ctx.send(embed=embed)

bot.run(TOKEN)