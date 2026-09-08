# 🎁 Free hry – jak to funguje

Bot každý den sbírá aktuálně zdarma dostupné hry ze 3 zdrojů a posílá je do Discordu.

---

## Obsah

- [Přehled](#přehled)
- [Zdroje](#zdroje)
- [Příkazy a nastavení](#příkazy-a-nastavení)
- [Automatické odesílání](#automatické-odesílání)
- [Řešení problémů](#řešení-problémů)

---

## Přehled

Každá hra se posílá jako samostatný embed s obrázkem, cenou (přeškrtnutá původní + „ZDARMA"),
datem vydání a hodnocením (pokud je k dispozici). PlayStation Plus články se posílají
souhrnně v jednom embedu se seznamem odkazů.

## Zdroje

| Zdroj | Typ | Poznámka |
|---|---|---|
| 🟣 **Epic Games** | oficiální API | Týdenní rotace zdarma her |
| 🎮 **Steam** (přes Reddit) | `r/FreeGameFindings` JSON, bez nutné autentizace | Limitované giveaways, filtruje se na `[Steam]` tag, max. 5 na běh |
| 🎯 **PlayStation Plus** | RSS feed (`blog.playstation.com`) | Měsíční přehled novinek PS+ |

Přímé API zdroje GOG, Amazon Prime Gaming, IsThereAnyDeal a Ubisoft+ byly v minulosti
zkoušeny a odstraněny (nespolehlivé nebo bez veřejného API) – Steam proto jede oklikou přes
Reddit. Aktuálně platí jen tyto 3 zdroje. Historie je v [CHANGELOG.md](CHANGELOG.md).

Selhání jednoho zdroje neovlivní ostatní – každý má vlastní `try/except` a timeout.

## Příkazy a nastavení

```
/freegames                        – zobrazí aktuální free hry hned
/setchannel freegames <kanál>     – nastaví kanál pro automatické denní odesílání
/config                           – zobrazí aktuální nastavení kanálů
```

## Automatické odesílání

Každý den **ve 20:10 (Europe/Prague)** bot pošle až 12 her do nastaveného kanálu. Pokud
kanál není nastavený přes `/setchannel freegames`, nic se neposílá.

## Řešení problémů

| Problém | Co zkusit |
|---|---|
| Bot v 20:10 nic nepošle | Zkontroluj, že je kanál nastavený (`/config`) a bot v něm smí psát (**Send Messages**) |
| `/freegames` vrátí prázdný seznam | Momentálně opravdu nejsou žádné free hry, nebo je zdroj dočasně nedostupný – zkus to znovu později |
| Chybí obrázky u her | Zdroj byl pomalý / obrázek se nepodařilo stáhnout – projeví se při dalším běhu |
| Chci vidět, který zdroj selhal | `journalctl -u discordbot -f | grep freegames` |

Viz také [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) pro obecné problémy s botem.
