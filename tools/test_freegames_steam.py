#!/usr/bin/env python3
"""
Offline test JEN Steam/Reddit větve z bot.py `get_free_games()`.

POZOR: tohle není plná simulace `/freegames` – Epic Games ani PlayStation Plus
zdroje tady nejsou. Slouží k rychlému ověření, že Reddit r/FreeGameFindings
API pořád vrací použitelná data a parsování `[Steam]` postů funguje.
Logika je ručně zkopírovaná z bot.py – když se `get_free_games()` v botovi
změní, aktualizuj i tenhle soubor.

Spuštění:  python tools/test_freegames_steam.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import re
import datetime
from html import unescape as html_unescape
import xml.etree.ElementTree as ET

def get_free_games():
    """Ručně zkopírovaná JEN Steam/Reddit větev z bot.py `get_free_games()`."""
    games = []
    seen = set()
    source_status = {
        "epic": False,
        "steam": False,
        "playstation": False
    }

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
            print(f"[freegames] Loaded {len(posts)} posts from Reddit")
            
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
                        print(f"[STEAM] Skipping duplicate: {game_name}")
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
                    
                    game_dict = {
                        "title": game_name,
                        "url": steam_url,
                        "source": "Steam (Reddit)",
                        "image": image,
                        "original_price": "Zdarma",
                        "expire_date": expire_str,
                        "reviews": reviews,
                        "platforms": "PC"
                    }
                    
                    games.append(game_dict)
                    print(f"[STEAM] ✅ Added: {game_name}")
                    
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
    
    except Exception as e:
        print(f"[freegames] Steam (Reddit) error: {e}")
        source_status["steam"] = False

    return games, source_status


def simulate_command():
    """Simulace /freegames command"""
    print("\n" + "="*70)
    print("SIMULATING /freegames COMMAND")
    print("="*70 + "\n")
    
    free_games, source_status = get_free_games()
    
    print(f"\n[freegames] Obtained {len(free_games)} total games")
    print(f"[freegames] Source status: {source_status}\n")
    
    if not free_games:
        print("❌ Žádné zdarma hry nenalezeny")
        return
    
    # Oddělení her od PSN článků
    regular_games = [g for g in free_games if "playstation" not in g.get("source", "").lower()]
    psn_articles = [g for g in free_games if "playstation" in g.get("source", "").lower()]
    
    print(f"[freegames] Regular games: {len(regular_games)}, PSN articles: {len(psn_articles)}")
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
            
            print(f"\n📤 SENDING EMBED #{sent+1}:")
            print(f"   Title: {title}")
            print(f"   Source: {source}")
            print(f"   URL: {url}")
            print(f"   Price: {original_price}")
            print(f"   Expire: {expire_date}")
            print(f"   Reviews: {reviews}")
            print(f"   Platforms: {platforms}")
            
            if image:
                print(f"   Image: ✅ (has image)")
            else:
                print(f"   Image: ❌ (no image)")
            
            sent += 1
        except Exception as e:
            print(f"❌ Error sending game embed: {e}")
            continue
    
    print(f"\n✅ TOTAL SENT: {sent} embeds")


if __name__ == "__main__":
    simulate_command()
