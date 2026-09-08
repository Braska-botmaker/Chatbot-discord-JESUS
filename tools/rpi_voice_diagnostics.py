#!/usr/bin/env python3
"""
RPi Voice Connection Diagnostics
Checks hardware, network, and Discord.py configuration
"""

import socket
import platform
import subprocess
import sys
import asyncio
import os

def run_cmd(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def check_platform():
    """Check if running on RPi"""
    print("\n=== PLATFORM ===")
    machine = platform.machine()
    system = platform.system()
    print(f"Machine: {machine}")
    print(f"System: {system}")
    print(f"Python: {sys.version}")
    is_arm = any(variant in machine.lower() for variant in ['arm', 'aarch64'])
    print(f"Is ARM: {'✅ YES' if is_arm else '❌ NO'}")
    return is_arm

def check_network():
    """Check network connectivity"""
    print("\n=== NETWORK ===")
    
    # Check DNS
    try:
        ip = socket.gethostbyname('discord.com')
        print(f"✅ DNS resolution (discord.com): {ip}")
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
    
    # Check internet connectivity
    out, code = run_cmd("ping -c 1 8.8.8.8 2>/dev/null || ping -n 1 8.8.8.8 2>nul")
    if code == 0:
        print(f"✅ Internet (ping 8.8.8.8): OK")
    else:
        print(f"❌ Internet (ping 8.8.8.8): FAILED")
    
    # Check Discord gateway connectivity
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('gateway.discord.gg', 443))
        sock.close()
        if result == 0:
            print(f"✅ Discord gateway (443): OK")
        else:
            print(f"❌ Discord gateway (443): FAILED (code {result})")
    except Exception as e:
        print(f"❌ Discord gateway check: {e}")

def check_audio():
    """Check audio system"""
    print("\n=== AUDIO ===")
    
    # Check Opus
    try:
        import discord.opus as opus
        if opus.is_loaded():
            print(f"✅ Opus: LOADED")
        else:
            print(f"⚠️  Opus: NOT LOADED")
            # Try to load it
            for name in ("libopus.so.0", "libopus.so", "opus"):
                try:
                    opus.load_opus(name)
                    print(f"   → Loaded from: {name}")
                    break
                except:
                    pass
    except Exception as e:
        print(f"❌ Opus check: {e}")
    
    # Check FFmpeg
    out, code = run_cmd("ffmpeg -version 2>&1 | head -1")
    if code == 0:
        print(f"✅ FFmpeg: {out}")
    else:
        print(f"❌ FFmpeg: NOT FOUND")
    
    # Check PyNaCl
    try:
        import nacl
        print(f"✅ PyNaCl: INSTALLED")
    except:
        print(f"❌ PyNaCl: NOT INSTALLED")

def check_socket():
    """Check UDP socket configuration"""
    print("\n=== UDP SOCKET ===")
    
    # Get system buffer sizes
    out_rcv, _ = run_cmd("cat /proc/sys/net/core/rmem_max 2>/dev/null || echo 'N/A'")
    out_snd, _ = run_cmd("cat /proc/sys/net/core/wmem_max 2>/dev/null || echo 'N/A'")
    print(f"UDP RCV buffer (max): {out_rcv}")
    print(f"UDP SND buffer (max): {out_snd}")
    
    # Check MTU
    out_mtu, _ = run_cmd("ip link show 2>/dev/null | grep -i mtu || echo 'N/A'")
    print(f"Network MTU: {out_mtu if out_mtu else 'N/A'}")

def _ver_tuple(v):
    out = []
    for part in str(v).split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)

def check_discord_py():
    """Check discord.py installation"""
    print("\n=== DISCORD.PY ===")

    try:
        import discord
        ver = discord.__version__
        # v2.8.2: Discord vyžaduje pro voice DAVE (E2EE) protokol – umí ho až 2.7.1+.
        # Starší verze padá při voice handshake s nedokumentovaným kódem 4017.
        if _ver_tuple(ver) >= (2, 7, 1):
            print(f"✅ discord.py: {ver} (podporuje DAVE / kód 4017 OK)")
        else:
            print(f"❌ discord.py: {ver} – PŘÍLIŠ STARÉ pro DAVE, voice spadne s 4017!")
            print(f"   → pip install -U \"discord.py[voice]\"")

        # Check voice requirements
        try:
            import discord.voice_client
            print(f"✅ Voice client module: OK")
        except Exception:
            print(f"❌ Voice client module: FAILED")

        # davey – povinná závislost pro DAVE (přijde s discord.py[voice] >= 2.7.1)
        try:
            import davey  # noqa: F401
            print(f"✅ davey (DAVE): INSTALLED")
        except Exception:
            print(f"❌ davey (DAVE): NOT INSTALLED – pip install -U \"discord.py[voice]\"")

    except Exception as e:
        print(f"❌ discord.py: {e}")

def check_js_runtime():
    """Check JS runtime for yt-dlp (v2.8.3)"""
    print("\n=== JS RUNTIME (yt-dlp) ===")
    # YouTube od ~2026.08 vyžaduje k extrakci JS engine, jinak "Sign in to confirm you're not a bot".
    found = False
    for name in ("deno", "node", "quickjs", "qjs", "bun"):
        path, code = run_cmd(f"command -v {name}")
        if code == 0 and path:
            print(f"✅ {name}: {path}")
            found = True
    if not found:
        print("❌ Žádný JS runtime (deno/node/quickjs/bun) v PATH")
        print("   → sudo apt-get install nodejs   (nebo nastav YTDLP_JS_RUNTIME v .env)")

def check_memory():
    """Check available memory"""
    print("\n=== MEMORY ===")
    
    out, _ = run_cmd("free -h 2>/dev/null || vm_stat 2>/dev/null | head -20")
    if out:
        for line in out.split('\n')[:5]:
            print(line)
    else:
        print("N/A")

def check_cpu():
    """Check CPU usage and temperature"""
    print("\n=== CPU ===")
    
    # Load average
    out, _ = run_cmd("uptime")
    print(f"Uptime: {out}")
    
    # CPU temp (RPi)
    out_temp, _ = run_cmd("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
    if out_temp and out_temp.isdigit():
        temp_c = int(out_temp) / 1000
        print(f"Temperature: {temp_c}°C {'🔥 HOT!' if temp_c > 60 else '✅ OK'}")
    else:
        print("Temperature: N/A")

def check_discord_connection():
    """Try to connect to Discord voice (async)"""
    print("\n=== DISCORD CONNECTION TEST ===")
    
    async def test_discord():
        try:
            import discord
            
            # Create a test client
            intents = discord.Intents.default()
            intents.voice_states = True
            client = discord.Client(intents=intents)
            
            # Get gateway info
            try:
                gateway_url = await client.http.get_gateway_bot()
                print(f"✅ Gateway info retrieved")
                print(f"   URL: {gateway_url.get('url', 'N/A')}")
                print(f"   Shards: {gateway_url.get('shards', 'N/A')}")
            except Exception as e:
                print(f"❌ Gateway info failed: {e}")
            
            await client.close()
        except Exception as e:
            print(f"❌ Discord test: {e}")
    
    try:
        asyncio.run(test_discord())
    except Exception as e:
        print(f"❌ Async test failed: {e}")

def main():
    print("╔════════════════════════════════════════════════════════╗")
    print("║        RPi VOICE CONNECTION DIAGNOSTICS                ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    is_arm = check_platform()
    check_network()
    check_audio()
    check_socket()
    check_discord_py()
    check_js_runtime()
    check_memory()
    check_cpu()
    
    if is_arm:
        check_discord_connection()
    
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║ SUMMARY                                                 ║")
    print("╚════════════════════════════════════════════════════════╝")
    print("""
If you see mostly ✅, your RPi is healthy.
If you see ❌ items, focus on those:

COMMON RPi VOICE ISSUES:
1. CPU temp > 60°C → Reduce FFmpeg bitrate further
2. Memory < 200MB → Kill background processes
3. UDP socket size too small → Check buffer sizes
4. PyNaCl/Opus missing → pip install -U "discord.py[voice]"
5. Network MTU issues → Check with: ip link show
6. discord.py < 2.7.1 → voice spadne s kódem 4017 (chybí DAVE)
7. Chybí node/deno → yt-dlp: "Sign in to confirm you're not a bot"

NEXT STEPS:
- Run bot with these diagnostics running: python tools/rpi_voice_diagnostics.py
- During /yt attempt, watch for network drops
- Check system logs: journalctl -u discordbot -f
- V Discordu: /diag  (rychlejší, běží přímo v botovi)
""")

if __name__ == "__main__":
    main()
