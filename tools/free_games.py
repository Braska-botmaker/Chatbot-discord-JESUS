#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FREE_GAMES TOOL - v2.6.3
Komplexní nástroj pro testování, ladění a správu zdrojů her zdarma
Testuje tři produkční zdroje: Epic Games, Steam, PlayStation Plus
"""

import requests
import re
import json
from datetime import datetime
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup

class FreeGamesTool:
    """Komplexní nástroj pro testování a správu zdrojů her zdarma"""
    
    def __init__(self):
        self.games = []
        self.source_status = {}
        self.test_results = {}
        
    def test_epic_games(self) -> Dict:
        """Testuje Epic Games API"""
        result = {
            "source": "Epic Games",
            "working": False,
            "games_count": 0,
            "games": [],
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
            r = requests.get(url, timeout=8)
            data = r.json()
            
            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                return result
            
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
                        game = {
                            "title": element.get("title", "Unknown"),
                            "url": element.get("productSlug", ""),
                            "image": None
                        }
                        
                        # Hledej obrázek
                        key_images = element.get("keyImages", [])
                        if key_images and isinstance(key_images, list) and len(key_images) > 0:
                            image_obj = key_images[0]
                            if isinstance(image_obj, dict):
                                image = image_obj.get("url")
                                if image:
                                    game["image"] = image
                        
                        result["games"].append(game)
                except:
                    continue
            
            result["games_count"] = len(result["games"])
            result["working"] = result["games_count"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_steam(self) -> Dict:
        """Získej pouze časově omezené free hry ze Steamu (ne F2P)."""
        result = {
            "source": "Steam",
            "working": False,
            "games_count": 0,
            "games": [],
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # SteamDB free promotions endpoint
            url = "https://steamdb.info/upcoming/free/"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, timeout=6, headers=headers)
            
            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                return result
            
            games = []
            # Parse HTML pro limited-time free games
            soup = BeautifulSoup(r.text, 'html.parser')
            
            for row in soup.select('tr'):
                # Najdi hry s "Keep Forever" nebo "Limited Time"
                if 'Keep Forever' in row.text or 'ends in' in row.text.lower():
                    app_link = row.select_one('a[href*="/app/"]')
                    if app_link:
                        try:
                            app_id = app_link['href'].split('/app/')[1].split('/')[0]
                            title = app_link.text.strip()
                            
                            if result["games_count"] >= 10:
                                break
                            
                            # Získej detaily ze Steam Store API
                            try:
                                detail_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us"
                                detail_r = requests.get(detail_url, timeout=3)
                                detail_data = detail_r.json()
                                
                                if detail_data.get(app_id, {}).get("success"):
                                    app_data = detail_data[app_id]["data"]
                                    
                                    # Získej původní cenu
                                    original_price = "N/A"
                                    if app_data.get("price_overview"):
                                        original_price = f"${app_data['price_overview'].get('initial', 0) / 100:.2f}"
                                    
                                    # Získej datum vydání
                                    release_date = app_data.get("release_date", {}).get("date", "TBA")
                                    
                                    # Získej hodnocení (metacritic)
                                    reviews = "N/A"
                                    if app_data.get("metacritic"):
                                        reviews = f"Metacritic: {app_data['metacritic']['score']}/100"
                                    
                                    # Podporované platformy
                                    platforms = []
                                    if app_data.get("platforms", {}).get("windows"):
                                        platforms.append("Windows")
                                    if app_data.get("platforms", {}).get("mac"):
                                        platforms.append("Mac")
                                    if app_data.get("platforms", {}).get("linux"):
                                        platforms.append("Linux")
                                    
                                    game = {
                                        "title": title,
                                        "url": f"https://store.steampowered.com/app/{app_id}",
                                        "app_id": app_id,
                                        "image": f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",
                                        "original_price": original_price,
                                        "release_date": release_date,
                                        "reviews": reviews,
                                        "platforms": ", ".join(platforms) if platforms else "N/A"
                                    }
                                    result["games"].append(game)
                                else:
                                    # Fallback bez detailů
                                    game = {
                                        "title": title,
                                        "url": f"https://store.steampowered.com/app/{app_id}",
                                        "app_id": app_id,
                                        "image": f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",
                                        "original_price": "N/A",
                                        "release_date": "N/A",
                                        "reviews": "N/A",
                                        "platforms": "N/A"
                                    }
                                    result["games"].append(game)
                            except Exception as detail_err:
                                print(f"[steam] Error getting details for {app_id}: {detail_err}")
                                # Fallback
                                game = {
                                    "title": title,
                                    "url": f"https://store.steampowered.com/app/{app_id}",
                                    "app_id": app_id,
                                    "image": f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",
                                    "original_price": "N/A",
                                    "release_date": "N/A",
                                    "reviews": "N/A",
                                    "platforms": "N/A"
                                }
                                result["games"].append(game)
                        except Exception:
                            continue
            
            result["games_count"] = len(result["games"])
            result["working"] = result["games_count"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_playstation_plus(self) -> Dict:
        """Testuje PlayStation Plus RSS feed"""
        result = {
            "source": "PlayStation Plus",
            "working": False,
            "articles_count": 0,
            "articles": [],
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            url = "https://blog.playstation.com/tag/playstation-plus/feed/"
            r = requests.get(url, timeout=8)
            
            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                return result
            
            # Parse RSS
            pattern = re.compile(
                r'<item>.*?<title>([^<]+)</title>.*?<link>([^<]+)</link>.*?</item>',
                re.DOTALL
            )
            matches = pattern.findall(r.text)
            
            for title, link in matches[:10]:
                article = {
                    "title": title.strip(),
                    "url": link.strip(),
                    "image": "https://www.playstation.com/content/dam/corporate/images/logos/playstation-logo.png"
                }
                result["articles"].append(article)
            
            result["articles_count"] = len(result["articles"])
            result["working"] = result["articles_count"] > 0
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_all(self) -> None:
        """Testuje všechny zdroje"""
        print("\n" + "="*70)
        print("FREE_GAMES TOOL - Komplexní test všech zdrojů")
        print("="*70)
        
        # Test Epic
        epic_result = self.test_epic_games()
        self.test_results["Epic"] = epic_result
        self._print_result(epic_result)
        
        # Test Steam
        steam_result = self.test_steam()
        self.test_results["Steam"] = steam_result
        self._print_result(steam_result)
        
        # Test PlayStation
        ps_result = self.test_playstation_plus()
        self.test_results["PlayStation"] = ps_result
        self._print_result(ps_result)
        
        # Summary
        self._print_summary()
    
    def _print_result(self, result: Dict) -> None:
        """Vytiskne výsledek testu"""
        source = result["source"]
        working = "✓ WORKING" if result["working"] else "✗ BROKEN"
        count_key = "games_count" if "games_count" in result else "articles_count"
        count = result[count_key]
        
        print(f"\n{source}: {working}")
        print(f"  Count: {count}")
        
        if result["error"]:
            print(f"  Error: {result['error']}")
        
        items = result.get("games", result.get("articles", []))
        if items:
            print(f"  Sample:")
            for item in items[:3]:
                title = item.get("title", "Unknown")[:50]
                print(f"    - {title}")
    
    def _print_summary(self) -> None:
        """Vytiskne souhrn"""
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        working_sources = [s for s, r in self.test_results.items() if r["working"]]
        print(f"\n✓ Working Sources: {len(working_sources)}/3")
        for source in working_sources:
            print(f"  - {source}")
        
        total_games = sum(r.get("games_count", 0) + r.get("articles_count", 0) 
                         for r in self.test_results.values())
        print(f"\nTotal items found: {total_games}")
        print("\n" + "="*70)
    
    def export_results(self, filepath: str = None) -> str:
        """Exportuj výsledky do JSON"""
        if not filepath:
            filepath = "free_games_test_results.json"
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        return filepath


def main():
    """Spustí komplexní test"""
    print("\n" + "="*70)
    print("FREE GAMES v2.6.3 - PRODUCTION TEST")
    print("="*70 + "\n")
    
    tool = FreeGamesTool()
    
    # Epic Games
    print("🔍 Testing Epic Games...")
    epic_result = tool.test_epic_games()
    tool.test_results["Epic"] = epic_result
    print(f"   Result: {'✓ OK' if epic_result['working'] else '✗ FAILED'} - {epic_result['games_count']} items")
    if epic_result['games'] and epic_result['working']:
        for game in epic_result['games'][:3]:
            print(f"     • {game['title']}")
    
    # Steam
    print("\n🔍 Testing Steam...")
    steam_result = tool.test_steam()
    tool.test_results["Steam"] = steam_result
    print(f"   Result: {'✓ OK' if steam_result['working'] else '✗ FAILED'} - {steam_result['games_count']} items")
    if steam_result['games'] and steam_result['working']:
        for game in steam_result['games'][:3]:
            print(f"     • {game['title']}")
    
    # PlayStation Plus
    print("\n🔍 Testing PlayStation Plus...")
    psplus_result = tool.test_playstation_plus()
    tool.test_results["PlayStation"] = psplus_result
    print(f"   Result: {'✓ OK' if psplus_result['working'] else '✗ FAILED'} - {psplus_result['articles_count']} items")
    if psplus_result['articles'] and psplus_result['working']:
        for article in psplus_result['articles'][:2]:
            print(f"     • {article['title'][:60]}")
    
    # Summary
    print("\n" + "="*70)
    print("PRODUCTION SUMMARY")
    print("="*70)
    
    working = sum(1 for r in tool.test_results.values() if r['working'])
    total = sum(r.get('games_count', 0) + r.get('articles_count', 0) for r in tool.test_results.values())
    
    print(f"\n✓ Working Sources: {working}/3")
    for name, result in tool.test_results.items():
        status = "✓" if result['working'] else "✗"
        count = result.get('games_count', 0) + result.get('articles_count', 0)
        print(f"  {status} {name}: {count} items")
    
    print(f"\n📊 Total items found: {total}")
    print("="*70 + "\n")
    
    # Exportuj výsledky
    result_file = tool.export_results()
    print(f"📁 Results exported to: {result_file}\n")


if __name__ == "__main__":
    main()
