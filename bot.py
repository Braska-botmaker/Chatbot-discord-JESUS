import discord
from discord.ext import commands, tasks
import random
import datetime
import os
import requests
from dotenv import load_dotenv
import pytz

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

recently_announced_games = set()

# Česká časová zóna
CET = pytz.timezone("Europe/Prague")

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
    "Cyberpunk 2077": "Ať tvé rozhodnutí vedou k lepšímu světu Night City.",
    "Black Desert Online": "Ať tvé cestování bohatě obohatí duchovní i materiální život.",
    "The Witcher 3": "Ať tvá cesta po Ciri vedena moudrostí a milosrdenstvím.",
    "Red Dead Redemption 2": "Ať tvá čest je silnější než touha po penězích",
    "Hades": "Ať tvoje cesta z podsvětí vede k osvobození a odpuštění.",
    "Rainbow Six Siege": "Ať tvá taktika zachrání životy, ne přidá zármutek.",
    "Skyrim": "Ať dračí křídla nevzbudí zlo, a tvé srdce zůstane silné.",
}

@bot.event
async def on_ready():
    print(f"Bot je přihlášen jako {bot.user}")
    send_morning_message.start()
    send_night_message.start()
    send_free_games.start()
    clear_recent_announcements.start()

@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if channel.permissions_for(member.guild.me).send_messages:
            await channel.send(f"Vítej, {member.mention}, nový bratře v Kristu!")
            break

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

        message = game_blessings.get(game_name, f"Modlíme se za tebe, bratře v Kristu 🙏. Užij si tuto videohru.")

        for channel in after.guild.text_channels:
            if channel.permissions_for(after.guild.me).send_messages:
                try:
                    await channel.send(f"{after.mention} právě hraje **{game_name}**. {message}")
                except Exception as e:
                    print(f"[ERROR] Chyba při odesílání zprávy: {e}")
                break

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel != before.channel:
        members_in_channel = after.channel.members
        if len(members_in_channel) >= 2:
            games = [m.activity.name for m in members_in_channel if m.activity and isinstance(m.activity, discord.Game)]
            if len(games) >= 2 and all(g == games[0] for g in games):
                game = games[0]
                mentions = ", ".join(m.mention for m in members_in_channel)
                for channel in member.guild.text_channels:
                    if channel.permissions_for(member.guild.me).send_messages:
                        await channel.send(f"{mentions} se spojili ve voice chatu a společně hrají **{game}** 🎮. Ať vás provází Pán! ✝️")
                        break

# Ranní zprávy
@tasks.loop(time=datetime.time(hour=7, minute=0, tzinfo=CET))
async def send_morning_message():
    verse = random.choice(verses)
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(f"@everyone Dobré ráno, bratři a sestry v Kristu! 🌞\n📖 Dnešní verš:\n> {verse}")
                break

# Noční zprávy
@tasks.loop(time=datetime.time(hour=21, minute=0, tzinfo=CET))
async def send_night_message():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send("@everyone Dobrou noc a požehnaný spánek, bratři a sestry v Kristu. 🙏🌙")
                break

# Funkce pro zjištění her zdarma
def get_free_games():
    games = []

    # Epic Games Store
    try:
        epic_api = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        response = requests.get(epic_api, timeout=5)
        data = response.json()
        for game in data["data"]["Catalog"]["searchStore"]["elements"]:
            if game["price"]["totalPrice"]["discountPrice"] == 0:
                games.append({
                    "title": game["title"],
                    "url": f"https://store.epicgames.com/p/{game['catalogNs']['mappings'][0]['pageSlug']}"
                })
    except Exception as e:
        print(f"[ERROR] Epic Games API selhalo: {e}")

    # Steam 
    try:
        steam_api = "https://api.isthereanydeal.com/v01/deals/list/?key=demo&limit=5&offset=0"
        response = requests.get(steam_api, timeout=5)
        data = response.json()
        for game in data.get("data", {}).get("list", []):
            if game["price_new"] == 0:
                games.append({
                    "title": game["title"],
                    "url": f"https://store.steampowered.com/app/{game['id']}"
                })
    except Exception as e:
        print(f"[ERROR] Steam API selhalo: {e}")

    return games

# Odesílání her zdarma každý večer
@tasks.loop(time=datetime.time(hour=21, minute=10, tzinfo=CET))
async def send_free_games():
    free_games = get_free_games()
    if not free_games:
        return
    message = "**🎮 Dnešní hry zdarma:**\n" + "\n".join([f"- [{g['title']}]({g['url']})" for g in free_games])
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(message)
                break

# příkaz !hryzdarma
@bot.command(name="hryzdarma")
async def hry_zdarma(ctx):
    free_games = get_free_games()
    if not free_games:
        await ctx.send("Momentálně nejsou k dispozici žádné hry zdarma. 🙁")
        return
    message = "**🎮 Aktuální hry zdarma:**\n" + "\n".join([f"- [{g['title']}]({g['url']})" for g in free_games])
    await ctx.send(message)

# příkaz !verš
@bot.command(name="verš")
async def vers_command(ctx):
    verse = random.choice(verses)
    await ctx.send(f"📖 **Dnešní verš:**\n> {verse}")

@tasks.loop(hours=1)
async def clear_recent_announcements():
    recently_announced_games.clear()


bot.run(TOKEN)
