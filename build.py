#!/usr/bin/env python3
"""Nachtwache: erzeugt das Datapack aus den Tabellen in tabellen/.

Aufruf:  python3 build.py            -> schreibt out/nachtwache/ und out/nachtwache.zip
Alles, was sich am Spiel einstellen laesst, steht entweder in tabellen/*.csv
oder hier oben im Abschnitt EINSTELLUNGEN.
"""
import csv, json, math, os, shutil, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COIN = "\u25cf"                         # Muenz-Symbol im UI (● wird vom Ressourcenpaket durch eine Muenze ersetzt)
RESSOURCENPAKET = True                 # eigene Item-Symbole (item_model) fuer Watch Bell und Kits, braucht out/nachtwache-rp.zip beim Client
TAB = HERE / "tabellen"
OUT = HERE / "out" / "nachtwache"
NS = "nachtwache"

# ----------------------------------------------------------------------------
# EINSTELLUNGEN
# ----------------------------------------------------------------------------
PACK_VERSION = 50                       # hochzaehlen, wenn Stand/Sammler sich aendern (Migration beim Laden)
PACK_MIN, PACK_MAX = 94, 110          # 1.21.11 = 94, spaetere Versionen bis 110 zugelassen

ADMINS = ["luisgamer2349"]           # bekommen den Tag nw.admin und duerfen /trigger reset + /trigger yes (Ops koennen weitere per /tag <name> add nw.admin freischalten)
ZWERG_TAKT = 300                        # Ticks je Schlag auf Stufe 0 (15 s)
ZWERG_STUFE_TICKS = 20                  # je Upgrade eine Sekunde schneller
ZWERG_MAX = 12                          # 12 Upgrades -> 3 s
ZWERG_YAW_VERSATZ = 0                  # Blickrichtungs-Versatz (Luis 07.09.2026: mit 180 schaute er weg vom Quell)
ZWERG_UPGRADE_PREIS = 250               # mal (Stufe + 1)
# Rucksack: Truhe mit 27 Faechern. 0..23 sind Lager, 24 Alles verkaufen, 25 groesserer Rucksack, 26 Tempo.
# Freigeschaltet sind je nach Rucksackstufe 9, 18 oder 24 Faecher, der Rest ist mit einer Scheibe gesperrt.
# Rucksack: eine Fallentruhe mit 27 Faechern (drei Reihen). Offen ist anfangs eine Reihe, jeder Kauf schaltet eine weitere frei.
# Die drei Knoepfe sitzen immer rechts in der letzten offenen Reihe, alles davor ist Lager, alles danach gesperrt.
ZWERG_REIHEN_START = 1
ZWERG_BP_PREIS = [500, 500]             # zwei Erweiterungen, dann sind die drei Reihen der Truhe voll
ZWERG_BP_MAX = len(ZWERG_BP_PREIS)
ZWERG_FAECHER = [(ZWERG_REIHEN_START + b) * 9 - 3 for b in range(ZWERG_BP_MAX + 1)]   # nutzbare Lagerfaecher je Stufe
ZWERG_SPERRE = ('minecraft:gray_stained_glass_pane[custom_data={nw_zwerg_lock:1b},'
                'custom_name={text:"Locked",color:"dark_gray",italic:false},'
                'lore=[{text:"Buy a bigger pack to use this slot",color:"dark_gray",italic:false}]]')
ZWERG_VERKAUF_KNOPF = ('minecraft:emerald[custom_data={nw_zwerg_sell:1b},custom_name={text:"Sell everything",color:"yellow",italic:false},'
                       'lore=[{text:"Sells the whole pack at the Collector price",color:"gray",italic:false},'
                       '{text:"Take this to sell",color:"dark_gray",italic:false}]]')
def zwerg_bp_knopf(b):
    faecher = ZWERG_FAECHER[b]
    if b < ZWERG_BP_MAX:
        return (f'minecraft:bundle[custom_data={{nw_zwerg_bp:1b}},custom_name={{text:"Bigger pack",color:"yellow",italic:false}},'
                f'lore=[{{text:"Now: {faecher} slots ({ZWERG_REIHEN_START + b} rows)",color:"gray",italic:false}},'
                f'[{{text:"Next: one more row for {ZWERG_BP_PREIS[b]} ",color:"gold",italic:false}},{{text:"{COIN}",color:"white",italic:false}}],'
                f'{{text:"Take this to buy",color:"dark_gray",italic:false}}]]')
    return (f'minecraft:shulker_shell[custom_data={{nw_zwerg_bp:1b}},custom_name={{text:"Full pack",color:"yellow",italic:false}},'
            f'lore=[{{text:"{faecher} slots ({ZWERG_REIHEN_START + b} rows)",color:"gray",italic:false}}]]')
def zwerg_up_knopf(l):
    sek = (ZWERG_TAKT - l * ZWERG_STUFE_TICKS) // 20
    if l < ZWERG_MAX:
        preis = ZWERG_UPGRADE_PREIS * (l + 1)
        return (f'minecraft:iron_pickaxe[custom_data={{nw_zwerg_up:1b}},custom_name={{text:"Upgrade speed",color:"yellow",italic:false}},'
                f'lore=[{{text:"Now: one block every {sek} s (level {l})",color:"gray",italic:false}},'
                f'[{{text:"Next: {sek-1} s for {preis} ",color:"gold",italic:false}},{{text:"{COIN}",color:"white",italic:false}}],'
                f'{{text:"Take this to buy",color:"dark_gray",italic:false}}]]')
    return (f'minecraft:netherite_pickaxe[custom_data={{nw_zwerg_up:1b}},custom_name={{text:"Max speed",color:"yellow",italic:false}},'
            f'lore=[{{text:"One block every {sek} s (level {l})",color:"gray",italic:false}}]]')

def zwerg_item(lvl, bp=0):
    """Der Zwerg als Gegenstand (Spawn-Ei, das einen Marker mit Stufen-Tags setzt)."""
    modell = 'item_model="nachtwache:dwarf",' if RESSOURCENPAKET else ""
    sek = (ZWERG_TAKT - lvl * ZWERG_STUFE_TICKS) // 20
    lore = ('[{text:"Place him next to a Source Generator, on solid ground.",color:"gray",italic:false},'
            '{text:"He mines the generator right in front of him. Four dwarves fit around one.",color:"gray",italic:false},'
            '{text:"Right-click: open his pack, buy speed and space, sell everything.",color:"gray",italic:false},'
            f'{{text:"Speed: one block every {sek} s (level {lvl})",color:"aqua",italic:false}},'
            f'{{text:"Pack: {ZWERG_FAECHER[bp]} slots ({ZWERG_REIHEN_START + bp} rows)",color:"aqua",italic:false}}]')
    return (f'minecraft:zombie_spawn_egg[{modell}custom_name={{text:"Fraggle",color:"aqua",italic:false}},custom_data={{nw_zwerg:1b,lvl:{lvl},bp:{bp}}},'
            f'entity_data={{id:"minecraft:marker",Tags:["nw.zwerg_neu","nw.lvl{lvl}","nw.bp{bp}"]}},lore={lore}]')

QUELL = (0, 64, -7)                    # Start-Generator, mittig auf der Insel
# Sieben Stufen des Quells: (Block, Farbe, Abbauten bis zur naechsten Stufe, Splitter je Abbau, Mob-Chance, Mob)
# Alle Bloecke brauchen eine Spitzhacke, um schnell zu gehen (Haerte 1.5 bis 1.8), Drops werden weggeraeumt.
STUFEN = [
    ("minecraft:tuff",             "Grau",    500,  1, 0.02, "zombie"),
    ("minecraft:green_concrete",   "Gruen",   1000, 2, 0.025, "zombie"),
    ("minecraft:blue_concrete",    "Blau",    1500, 3, 0.03, "skeleton"),
    ("minecraft:budding_amethyst", "Lila",    2000, 4, 0.035, "spider"),
    ("minecraft:yellow_concrete",  "Gelb",    3000, 5, 0.04, "witch"),
    ("minecraft:orange_concrete",  "Orange",  4000, 6, 0.045, "wither_skeleton"),
    ("minecraft:black_concrete",   "Schwarz", 0,    8, 0.05, "wither_skeleton"),
]
ANZ_STUFEN = len(STUFEN)
QUELL_BLOCK = STUFEN[0][0]
PHASEN_GRENZEN = []            # kumulierte Abbauten, ab denen Stufe 2..7 beginnt
_summe = 0
for _b, _f, _n, _s, _c, _m in STUFEN[:-1]:
    _summe += _n; PHASEN_GRENZEN.append(_summe)
SPLITTER_PRO_ABBAU = {i + 1: st[3] for i, st in enumerate(STUFEN)}
QUELL_MOBS = False                       # Luis 07.09.2026: kein Mob aus dem Quell, die Wellen reichen
MOB_CHANCE = {i + 1: (st[4] if QUELL_MOBS else 0.0) for i, st in enumerate(STUFEN)}
MOB_AUS_QUELL = {i + 1: st[5] for i, st in enumerate(STUFEN)}

# Startinsel: laengliche Ellipse, Laengsachse zeigt zur Bruecke (Luis 08.09.2026).
# Bruecke trifft die Insel bei z = INSEL_ZM + INSEL_RZ, der Beacon liegt 25 Bloecke dahinter.
INSEL_RX = 9                           # halbe Breite (x)
INSEL_RZ = 15                          # halbe Laenge (z)
INSEL_ZM = -7                          # Mittelpunkt der Insel in z
GEGNER_Z = 72                          # Mittelpunkt Gegnerinsel (x = 0)
GEGNER_RADIUS = 11
STRASSE_Z = (9, 59)                    # von .. bis (z), Breite 3 (x -1..1). Davor und dahinter feste Stege der Inseln
STRASSENMUND = (0.5, 64, 6.5)          # wohin festhaengende oder gefallene Gegner gesetzt werden (Inselrand)
BODEN_Y = 63                           # Oberkante Boden, gelaufen wird auf 64

LADEN = (-6, 64, -10)                  # Mitte des Tresens; der Laden steht seitlich, nicht im Weg Bruecke -> Beacon
KAUF_A = (LADEN[0] - 1, LADEN[1], LADEN[2])   # Truhenhaelfte mit den Feldern 0..26 (oben im Fenster) -> type=right bei facing=south
KAUF_B = (LADEN[0], LADEN[1], LADEN[2])       # Truhenhaelfte mit den Feldern 27..53 (unten)
VERKAUF = (LADEN[0] + 1, LADEN[1], LADEN[2])  # Fass
SAMMLER_POS = (LADEN[0] + 0.5, LADEN[1], LADEN[2] - 0.5)   # direkt hinter der rechten Truhenhaelfte, Wand im Ruecken
SPAWN = (0, 64, -10)
BEACON = (0, 64, -17)                  # roter Beacon: 25 Bloecke vom Brueckenende, am hinteren Ende der Insel
LEBEN_START, LEBEN_MAX, LEBEN_PREIS = 10, 20, 1500
DURCHBRUCH_TICKS = 100                 # 5 s ungestoert am Beacon, dann kostet der Gegner ein Leben
DURCHBRUCH_RADIUS = 3.5
TRUHE = (2, 64, 2)                     # alte Starttruhe, nur noch fuer die Migration

# Uhr: die Spielzeit laeuft mit ZAEHLER/NENNER Zeiteinheiten je Tick (Akkumulator, dadurch fluessig). Tag = 13500 Einheiten.
TAG_ZAEHLER, TAG_NENNER = 45, 32       # 1,40625 je Tick -> Tag genau 8 Minuten (Luis, 07.09.2026)
NACHT_ZAEHLER, NACHT_NENNER = 5, 7     # 0,714 je Tick -> Nacht bis 23000 in ca. 11,7 Minuten, dann steht die Uhr, bis alle Gegner tot sind
NACHT_START, TAG_START = 13000, 23500  # Uhrzeiten fuer Strasse auf / Strasse weg

WELLE_BASIS, WELLE_PRO_NACHT = 4, 2    # Groesse = 4 + 2*Nacht (+ Nacht*Nacht/WELLE_QUADRAT, 0 = aus) * Phasenfaktor/10. Luis: Nacht 1 = 6, dann +2 je Nacht
WELLE_QUADRAT = 0                      # quadratischer Anteil, 0 = aus
PHASEN_FAKTOR = {1: 10, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 10}   # Wellengroesse je Quellstufe in Zehnteln (10 = keine Aenderung); Luis will exakte Zahlen, daher aus   # in Zehnteln
LETZTE_NACHT = 30
BONUS_PRO_NACHT = 16                    # Splitter fuer eine komplett getoetete Welle (mal Nacht)
KOPFGELD = {"zombie": 6, "husk": 6, "skeleton": 9, "spider": 9, "cave_spider": 6, "creeper": 15, "enderman": 20,
            "witch": 18, "wither_skeleton": 18, "pillager": 15, "ravager": 45, "warden": 0}
KOPFGELD_BOSS = 150
TOD_ABZUG_PROZENT = 10

STILL_TICKS = 80                       # Stillstand, bis ein Gegner anfaengt zu graben (4 s)
GRAB_WEICH, GRAB_MITTEL, GRAB_HART = 40, 100, 200   # zusaetzliche Ticks je Materialklasse
EINGEBAUT_TICKS = 600                  # 30 s Stillstand UND undurchgrabbarer Block Richtung Spieler (Obsidian, Portalrahmen): erst dann taucht der Gegner neben ihm auf

# Bosse: nacht -> (mob-Typ, Name, Leben, Faehigkeit)
BOSSE = {
    5:  ("zombie_eisen", "The First", 60, None),
    10: ("spider", "The Mother", 48, "mutter"),        # ruft Hoehlenspinnen
    15: ("skeleton", "The Marksman", 60, "schuetze"),  # Bogen mit Staerke V
    20: ("ravager", "The Colossus", 150, None),
    25: ("witch", "The Witch", 84, "hexe"),             # ruft Diener
    30: ("warden", "The Collector", 170, "finale"),
}

# Materialklassen fuer den Durchbruch (Block-Tags). Alles andere gilt als unzerstoerbar.
WEICH = ["#minecraft:dirt", "minecraft:sand", "minecraft:red_sand", "minecraft:gravel", "minecraft:clay",
         "#minecraft:wool", "#minecraft:leaves", "minecraft:hay_block", "minecraft:moss_block",
         "minecraft:soul_sand", "minecraft:soul_soil", "minecraft:netherrack", "minecraft:snow_block",
         "minecraft:mud", "minecraft:packed_mud", "#minecraft:sand", "minecraft:glass", "minecraft:glass_pane",
         "#minecraft:wool_carpets", "minecraft:cobweb", "minecraft:sponge"]
MITTEL = ["#minecraft:logs", "#minecraft:planks", "#minecraft:fences", "#minecraft:fence_gates", "#minecraft:doors",
          "#minecraft:trapdoors", "#minecraft:wooden_slabs", "#minecraft:wooden_stairs", "minecraft:cobblestone",
          "minecraft:stone", "minecraft:mossy_cobblestone", "minecraft:andesite", "minecraft:granite", "minecraft:diorite",
          "minecraft:cobbled_deepslate", "minecraft:deepslate", "minecraft:sandstone", "minecraft:bricks", "minecraft:stone_bricks",
          "#minecraft:slabs", "#minecraft:stairs", "#minecraft:walls", "minecraft:blackstone", "minecraft:basalt",
          "minecraft:bookshelf", "minecraft:crafting_table", "minecraft:furnace", "minecraft:chest", "minecraft:barrel",
          "minecraft:magma_block", "minecraft:end_stone", "minecraft:purpur_block", "minecraft:quartz_block",
          "minecraft:glowstone", "minecraft:shroomlight", "minecraft:sea_lantern", "minecraft:ladder", "minecraft:scaffolding",
          "minecraft:iron_bars", "minecraft:iron_chain", "minecraft:bamboo_block", "minecraft:packed_ice", "minecraft:ice", "minecraft:blue_ice",
          "minecraft:tnt", "minecraft:piston", "minecraft:sticky_piston", "minecraft:observer", "minecraft:dispenser", "minecraft:dropper", "minecraft:hopper"]
HART = ["minecraft:iron_block", "minecraft:gold_block", "minecraft:copper_block", "#minecraft:copper", "minecraft:diamond_block",
        "minecraft:emerald_block", "minecraft:lapis_block", "minecraft:redstone_block", "minecraft:coal_block", "minecraft:netherite_block",
        "minecraft:deepslate_bricks", "minecraft:deepslate_tiles", "minecraft:polished_deepslate", "minecraft:polished_blackstone",
        "minecraft:polished_blackstone_bricks", "minecraft:nether_bricks", "minecraft:crying_obsidian", "minecraft:amethyst_block",
        "minecraft:prismarine", "minecraft:dark_prismarine", "minecraft:iron_door", "minecraft:iron_trapdoor", "minecraft:anvil",
        "minecraft:chipped_anvil", "minecraft:damaged_anvil", "minecraft:smithing_table", "minecraft:blast_furnace", "minecraft:smoker"]

# Sonder-Items im Angebot (Kurzname -> item id + components)
SONDERITEMS = {
    "TRANK_HEILUNG":   ("minecraft:potion", 1, '[potion_contents={potion:"minecraft:strong_healing"}]'),
    "TRANK_STAERKE":   ("minecraft:potion", 1, '[potion_contents={potion:"minecraft:strength"}]'),
    "TRANK_NACHTSICHT":("minecraft:potion", 1, '[potion_contents={potion:"minecraft:long_night_vision"}]'),
}
BUECHER = [  # (Verzauberung, [Stufen], Name, [Preise]) fuer den Reiter Books: Hoechststufe und eine darunter
    ("SHARPNESS", [4, 5], "Sharpness", [9000, 15000]), ("PROTECTION", [3, 4], "Protection", [6000, 14000]),
    ("EFFICIENCY", [4, 5], "Efficiency", [8000, 12000]), ("FORTUNE", [2, 3], "Fortune", [6000, 12000]),
    ("LOOTING", [2, 3], "Looting", [4000, 8000]), ("UNBREAKING", [2, 3], "Unbreaking", [3000, 5000]),
    ("POWER", [4, 5], "Power (bow)", [8000, 12000]), ("PUNCH", [1, 2], "Punch (bow)", [2000, 4000]),
    ("FIRE_ASPECT", [1, 2], "Fire Aspect", [3000, 6000]), ("KNOCKBACK", [1, 2], "Knockback", [1500, 3000]),
    ("SWEEPING_EDGE", [2, 3], "Sweeping Edge", [2000, 4000]), ("FEATHER_FALLING", [3, 4], "Feather Falling", [3000, 6000]),
    ("SILK_TOUCH", [1], "Silk Touch", [8000]), ("MENDING", [1], "Mending", [10000]),
    ("INFINITY", [1], "Infinity (bow)", [8000]), ("FLAME", [1], "Flame (bow)", [5000]),
]
ROEMISCH = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}
for _n, _ls, _, _ in BUECHER:
    for _l in _ls:
        SONDERITEMS[f"BUCH_{_n}_{_l}"] = ("minecraft:enchanted_book", 1,
                                          '[stored_enchantments={"minecraft:%s":%d}]' % (_n.lower(), _l))

# Vorgefuellte Kisten aus dem Quell (Name -> Liste von (item, anzahl))
KISTEN = {
    "KISTE_1": [("minecraft:bread", 4), ("minecraft:torch", 8), ("minecraft:string", 3), ("minecraft:iron_ingot", 2), ("minecraft:arrow", 8)],
    "KISTE_2": [("minecraft:iron_ingot", 5), ("minecraft:gold_ingot", 2), ("minecraft:redstone", 8), ("minecraft:bread", 6), ("minecraft:leather", 3), ("minecraft:name_tag", 1)],
    "KISTE_3": [("minecraft:diamond", 2), ("minecraft:enchanted_book", 1), ("minecraft:golden_apple", 1), ("minecraft:ender_pearl", 2), ("minecraft:blaze_rod", 2), ("minecraft:experience_bottle", 6)],
    "KISTE_4": [("minecraft:diamond", 4), ("minecraft:netherite_scrap", 1), ("minecraft:golden_apple", 2), ("minecraft:totem_of_undying", 1), ("minecraft:experience_bottle", 12), ("minecraft:enchanted_golden_apple", 1)],
}

# Mob-Typen der Wellen: name -> (entity, zusatz-NBT)
HELM = '{id:"minecraft:leather_helmet",count:1,components:{"minecraft:unbreakable":{},"minecraft:dyed_color":1315860}}'
def _mob(entity, extra="", helm=True, follow=100):
    nbt = 'PersistenceRequired:1b,attributes:[{id:"minecraft:follow_range",base:%dd}]' % follow
    if helm:
        nbt += ',equipment:{head:%s},drop_chances:{head:0.0f}' % HELM
    if extra:
        nbt += "," + extra
    return (entity, nbt)

MOBS = {
    "zombie":          _mob("minecraft:zombie", 'CanBreakDoors:1b'),
    "husk":            _mob("minecraft:husk", 'CanBreakDoors:1b', helm=False),
    "zombie_leder":    _mob("minecraft:zombie", 'CanBreakDoors:1b,equipment:{head:%s,chest:{id:"minecraft:leather_chestplate",count:1},legs:{id:"minecraft:leather_leggings",count:1}},drop_chances:{head:0.0f,chest:0.0f,legs:0.0f}' % HELM, helm=False),
    "zombie_eisen":    _mob("minecraft:zombie", 'CanBreakDoors:1b,equipment:{head:{id:"minecraft:iron_helmet",count:1},chest:{id:"minecraft:iron_chestplate",count:1},mainhand:{id:"minecraft:iron_sword",count:1}},drop_chances:{head:0.0f,chest:0.0f,mainhand:0.05f}', helm=False),
    "brutalo":         _mob("minecraft:zombie", 'CanBreakDoors:1b,CustomName:"Brute",attributes:[{id:"minecraft:follow_range",base:100d},{id:"minecraft:max_health",base:40d},{id:"minecraft:attack_damage",base:7d},{id:"minecraft:movement_speed",base:0.27d}],Health:40f,equipment:{head:{id:"minecraft:chainmail_helmet",count:1}},drop_chances:{head:0.0f},active_effects:[{id:"minecraft:strength",duration:-1,amplifier:0,show_particles:0b}]', helm=False, follow=100),
    "skeleton":        _mob("minecraft:skeleton", 'equipment:{head:%s,mainhand:{id:"minecraft:bow",count:1}},drop_chances:{head:0.0f,mainhand:0.05f}' % HELM, helm=False),
    "spider":          _mob("minecraft:spider", "", helm=False),
    "creeper":         _mob("minecraft:creeper", "", helm=False),
    "zombie_baby":     _mob("minecraft:zombie", 'CanBreakDoors:1b,IsBaby:1b'),
    "enderman":        _mob("minecraft:enderman", "", helm=False),
    "witch":           _mob("minecraft:witch", "", helm=False),
    "wither_skeleton": _mob("minecraft:wither_skeleton", 'equipment:{mainhand:{id:"minecraft:stone_sword",count:1}},drop_chances:{mainhand:0.05f}', helm=False),
    "pillager":        _mob("minecraft:pillager", 'equipment:{mainhand:{id:"minecraft:crossbow",count:1}},drop_chances:{mainhand:0.05f}', helm=False),
    "ravager":         _mob("minecraft:ravager", "", helm=False, follow=100),
    "cave_spider":     _mob("minecraft:cave_spider", "", helm=False),
}
# "attributes" doppelt bei brutalo: den ersten Eintrag aus _mob entfernen
MOBS["brutalo"] = (MOBS["brutalo"][0], MOBS["brutalo"][1].replace('attributes:[{id:"minecraft:follow_range",base:100d}],', '', 1))

# ----------------------------------------------------------------------------
# Hilfen
# ----------------------------------------------------------------------------
files = {}

def w(path, content):
    """Datei ins Datapack legen (Pfad relativ zu data/)."""
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False, indent=1)
    files[path] = content

def fn(name, lines):
    """mcfunction im Namespace nachtwache."""
    w(f"{NS}/function/{name}.mcfunction", "\n".join(l for l in lines if l is not None) + "\n")

def J(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

def txt(text, color=None, **kw):
    d = {"text": text}
    if color: d["color"] = color
    d.update(kw)
    return d

def coin():
    """Muenzsymbol als eigene Komponente in Weiss, damit die Muenzgrafik des Ressourcenpakets ihre Farben behaelt."""
    return {"text": COIN, "color": "white"}

def star():
    """Stern (Kontrakt aktiv), Grafik aus dem Ressourcenpaket."""
    return {"text": "\u2605", "color": "white"}

def sammler_sagt(component_list):
    return "tellraw @a " + J([txt("[The Collector] ", "dark_red")] + component_list)

def read_csv(name):
    rows = []
    with open(TAB / name, encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                rows.append(line)
    return list(csv.DictReader(rows))

def ellipse_fills(cx, cz, rx, rz, y1, y2, block):
    """fill-Befehle fuer eine Ellipsenscheibe (Zeile fuer Zeile, Laengsachse z)."""
    out = []
    for z in range(-rz, rz + 1):
        w = 1.0 - (z * z) / float(rz * rz)
        if w <= 0: continue
        half = int(rx * math.sqrt(w))
        out.append(f"fill {cx-half} {y1} {cz+z} {cx+half} {y2} {cz+z} {block}")
    return out

def kreis_fills(cx, cz, r, y1, y2, block):
    """fill-Befehle fuer eine Kreisscheibe (Zeile fuer Zeile)."""
    out = []
    for z in range(-r, r + 1):
        half = int(math.sqrt(r * r - z * z + 0.25))
        out.append(f"fill {cx-half} {y1} {cz+z} {cx+half} {y2} {cz+z} {block}")
    return out

# ----------------------------------------------------------------------------
# pack.mcmeta, Tags, Grundgeruest
# ----------------------------------------------------------------------------
w("../pack.mcmeta", {"pack": {"description": "Nightwatch: one block, the nights, the Collector", "min_format": PACK_MIN, "max_format": PACK_MAX}})
w("minecraft/tags/function/load.json", {"values": [f"{NS}:load"]})
w("minecraft/tags/function/tick.json", {"values": [f"{NS}:tick"]})
w(f"{NS}/tags/block/weich.json", {"values": WEICH})
w(f"{NS}/tags/block/mittel.json", {"values": MITTEL})
w(f"{NS}/tags/block/hart.json", {"values": HART})
w(f"{NS}/tags/block/quell.json", {"values": [st[0] for st in STUFEN]})
# Der Generator ist ein Fass. Luis will Steineigenschaften: Spitzhacke statt Axt (v0.15).
w("minecraft/tags/block/mineable/pickaxe.json", {"values": ["minecraft:barrel"]})
w("minecraft/tags/block/mineable/axe.json", {"replace": True, "values": ["minecraft:note_block", "minecraft:bamboo", "minecraft:bee_nest", "minecraft:beehive", "minecraft:big_dripleaf_stem", "minecraft:big_dripleaf", "minecraft:bookshelf", "minecraft:brown_mushroom_block", "minecraft:campfire", "minecraft:cartography_table", "minecraft:carved_pumpkin", "minecraft:chest", "minecraft:chorus_flower", "minecraft:chorus_plant", "minecraft:cocoa", "minecraft:composter", "minecraft:crafting_table", "minecraft:daylight_detector", "minecraft:fletching_table", "minecraft:glow_lichen", "minecraft:jack_o_lantern", "minecraft:jukebox", "minecraft:ladder", "minecraft:lectern", "minecraft:loom", "minecraft:melon", "minecraft:mushroom_stem", "minecraft:pumpkin", "minecraft:red_mushroom_block", "minecraft:smithing_table", "minecraft:soul_campfire", "minecraft:trapped_chest", "minecraft:vine", "#minecraft:banners", "#minecraft:fence_gates", "#minecraft:logs", "#minecraft:planks", "#minecraft:signs", "#minecraft:wooden_buttons", "#minecraft:wooden_doors", "#minecraft:wooden_fences", "#minecraft:wooden_pressure_plates", "#minecraft:wooden_slabs", "#minecraft:wooden_stairs", "#minecraft:wooden_trapdoors", "minecraft:mangrove_roots", "#minecraft:all_hanging_signs", "minecraft:bamboo_mosaic", "minecraft:bamboo_mosaic_slab", "minecraft:bamboo_mosaic_stairs", "#minecraft:bamboo_blocks", "minecraft:chiseled_bookshelf", "#minecraft:wooden_shelves", "minecraft:creaking_heart"]})
for p, c in MOB_CHANCE.items():
    w(f"{NS}/predicate/quell_mob_{p}.json", {"condition": "minecraft:random_chance", "chance": c})

OBJEKTIVE = [("nw.mined_gen", "minecraft.mined:minecraft.barrel")] + [
    ("nw.konto", "dummy"), ("nw.abbau", "dummy"), ("nw.phase", "dummy"), ("nw.nacht", "dummy"), ("nw.gegner", "dummy"),
    ("nw.tmp", "dummy"), ("nw.tmp2", "dummy"), ("nw.zeit", "dummy"), ("nw.tick", "dummy"), ("nw.status", "dummy"),
    ("nw.kauf", "trigger"), ("nw.endlos", "trigger"), ("nw.hilfe", "trigger"),
    ("nw.tode", "deathCount"),
    ("nw.px", "dummy"), ("nw.py", "dummy"), ("nw.pz", "dummy"), ("nw.qx", "dummy"), ("nw.qy", "dummy"), ("nw.qz", "dummy"),
    ("nw.still", "dummy"), ("nw.kills", "dummy"), ("nw.verdient", "dummy"), ("nw.anzeige", "dummy"), ("nw.const", "dummy"),
    ("nw.boss", "dummy"), ("nw.upgrade", "dummy"), ("nw.laterne", "dummy"), ("nw.zwerg", "dummy"), ("nw.zwerg_t", "dummy"), ("nw.zwerg_b", "dummy"), ("nw.zwerg_d", "dummy"), ("nw.leben", "dummy"), ("nw.chan", "dummy"), ("nw.hpv", "dummy"), ("nw.hpp", "dummy"),
    ("nw.b_sp", "dummy"), ("nw.b_st", "dummy"), ("nw.b_mu", "dummy"), ("nw.b_fl", "dummy"), ("nw.b_inf", "dummy"), ("nw.b_kb", "dummy"), ("nw.b_rg", "dummy"), ("nw.b_t", "dummy"), ("nw.b_nm", "dummy"), ("reset", "trigger"), ("yes", "trigger"), ("night", "trigger"), ("boss", "trigger"), ("fraggle", "trigger"), ("endnight", "trigger"), ("money", "trigger"), ("nw.schlaf", "dummy"), ("nw.fest", "dummy"), ("nw.dmin", "dummy"),
]

# ---- load ------------------------------------------------------------------
load = [f"scoreboard objectives add {o} {c}" for o, c in OBJEKTIVE]
load += [
    "scoreboard objectives modify nw.anzeige numberformat blank",
    'scoreboard objectives modify nw.anzeige displayname {"text":"NIGHTWATCH","color":"dark_red","bold":true}',
    "scoreboard objectives setdisplay sidebar nw.anzeige",
    "bossbar add nw:welle \"Night\"", "bossbar set nw:welle color red", "bossbar set nw:welle style notched_10", "bossbar set nw:welle visible false",
    "bossbar add nw:uhr \"Day\"", "bossbar set nw:uhr color green", "bossbar set nw:uhr style notched_6", "bossbar set nw:uhr max 13500",
    "bossbar add nw:boss \"Boss\"", "bossbar set nw:boss color purple", "bossbar set nw:boss style progress", "bossbar set nw:boss visible false",
]
for k in [-1, 2, 3, 4, 5, 6, 7, 10, 16, 20, 100, 200, 250, 360, 1000, 6000]:
    load.append(f"scoreboard players set #{k} nw.const {k}")
load += [
    f"execute unless score #init nw.status matches 1 run function {NS}:init",
    # Migration erst ein paar Sekunden nach dem Start (dann sind die Entities der Welt geladen)
    f"execute if score #init nw.status matches 1 unless score #version nw.status matches {PACK_VERSION} run scoreboard players set #migrieren nw.status 1",
    "scoreboard players set #tick nw.tick 0",
    "scoreboard players enable @a nw.kauf", "scoreboard players enable @a nw.endlos", "scoreboard players enable @a nw.hilfe",
    f"tellraw @a {J([txt('[Nightwatch] ', 'dark_red'), txt('Datapack loaded. ', 'gray'), txt('/trigger nw.hilfe', 'yellow', click_event={'action':'run_command','command':'trigger nw.hilfe'}), txt(' shows the help.', 'gray')])}",
]
fn("load", load)
fn("migration", [
    f"scoreboard players set #version nw.status {PACK_VERSION}", "scoreboard players set #migrieren nw.status 0",
    "kill @e[tag=nw.kasse]", "fill -4 64 -6 -3 65 -5 minecraft:air", "fill -1 64 -5 1 64 -5 minecraft:air",
    f"function {NS}:welt/stand", f"function {NS}:sammler/erscheinen",
    f"function {NS}:strasse/entfernen", f"function {NS}:welt/gegnerinsel",
    f"fill -1 {BODEN_Y} 6 1 {BODEN_Y} 8 minecraft:polished_deepslate",
    f"execute unless score #phase nw.phase matches 1.. run scoreboard players set #phase nw.phase 1",
    f"setblock {QUELL[0]} {QUELL[1]} {QUELL[2]} minecraft:air", f"function {NS}:quell/setzen",
    'kill @e[type=item,x=-2,y=62,z=-2,dx=4,dy=4,dz=4,nbt={Item:{id:"minecraft:budding_amethyst"}}]',
    f"function {NS}:sammler/kaufmenue",
    f"scoreboard players set #zoff nw.status {ZWERG_YAW_VERSATZ}",
    # Fraggles Rucksack ist jetzt eine Doppeltruhe: bestehende Zwerge einmal neu aufbauen, der alte Inhalt faellt heraus
    f"execute as @e[type=marker,tag=nw.zwerg] at @s run function {NS}:zwerg/migrieren",
    f"function {NS}:zwerg/altlast",
    # Starttruhe und Brunnen aus aelteren Fassungen abraeumen (Luis 07.09.2026), nur die eigenen Bloecke
    f"execute if block {TRUHE[0]} {TRUHE[1]} {TRUHE[2]} minecraft:chest run setblock {TRUHE[0]} {TRUHE[1]} {TRUHE[2]} minecraft:air destroy",
    "fill -1 64 4 1 64 6 minecraft:air replace minecraft:cobblestone_wall",
    "fill -1 65 4 1 65 6 minecraft:air replace minecraft:oak_fence",
    "setblock 0 66 5 minecraft:air",
    "fill -1 63 4 1 63 6 minecraft:grass_block replace minecraft:cobblestone",
    "fill -1 63 4 1 63 6 minecraft:grass_block replace minecraft:water",
    f"clear @a minecraft:echo_shard[custom_data~{{nw_splitter:1b}}]", f"clear @a minecraft:prismarine_crystals[custom_data~{{nw_buendel:1b}}]",
    "kill @e[type=item,x=-6,y=60,z=-10,dx=12,dy=10,dz=8]",
    # ---- v0.13: Insel umgebaut. Alter Stand, alter Beacon, alte Rampe, alter Baum und der alte Quell weg,
    # danach baut welt/startinsel die neue Ellipse. Alles, was Spieler gebaut haben, bleibt stehen.
    "fill -3 64 -9 3 68 -3 minecraft:air",                                   # alter Stand samt Rampe (x -2..2, z -8..-4)
    "fill -3 63 -9 3 63 -3 minecraft:grass_block replace minecraft:polished_deepslate",
    "fill -2 64 2 2 67 6 minecraft:air",                                     # alter Beacon (0,64,4) samt Sockel
    "fill -2 63 2 2 63 6 minecraft:grass_block replace minecraft:iron_block",
    "fill -6 64 -3 -2 71 1 minecraft:air",                                   # alter verkohlter Baum bei (-4,*,-1)
    "setblock 5 64 3 minecraft:air", "setblock -5 64 4 minecraft:air",       # alte Laternen
    'kill @e[type=item,x=-8,y=60,z=-12,dx=16,dy=14,dz=20,nbt={Item:{id:"minecraft:iron_block"}}]',
    'kill @e[type=item,x=-8,y=60,z=-12,dx=16,dy=14,dz=20,nbt={Item:{id:"minecraft:beacon"}}]',
    'kill @e[type=item,x=-8,y=60,z=-12,dx=16,dy=14,dz=20,nbt={Item:{id:"minecraft:deepslate_bricks"}}]',
    'kill @e[type=item,x=-8,y=60,z=-12,dx=16,dy=14,dz=20,nbt={Item:{id:"minecraft:hopper"}}]',
    # der Start-Generator zieht in die Inselmitte
    "kill @e[type=marker,tag=nw.gen,x=0,y=64,z=0,dx=0,dy=0,dz=0]",
    "kill @e[type=marker,tag=nw.gen_neu,x=0,y=64,z=0,dx=0,dy=0,dz=0]",
    "kill @e[type=block_display,tag=nw.gen_block,x=-1,y=63,z=-1,dx=2,dy=2,dz=2]",
    "setblock 0 64 0 minecraft:air",
    f"function {NS}:welt/startinsel",
    f"function {NS}:welt/stand",
    f"function {NS}:sammler/erscheinen", f"function {NS}:sammler/kaufmenue",
    f"function {NS}:beacon/aufbauen",
    "kill @e[tag=nw.herz]", "kill @e[tag=nw.herz_text]",
    # v0.15: Generatoren sind jetzt sichtbar, die alten grossen Farbwuerfel weg (werden klein neu gesetzt)
    "kill @e[type=block_display,tag=nw.gen_block]",
    "execute as @e[tag=nw.welle] run attribute @s minecraft:follow_range base set 128",
    f"spawnpoint @a {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}", f"setworldspawn {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    "tellraw @a " + J([txt("[Nightwatch] The island has been rebuilt: longer, the beacon at the far end, the stall off to the side.", "yellow")]),
])

# ---- init: Welt bauen -------------------------------------------------------
init = [
    # Gamerule-Namen ab 1.21.11 (snake_case)
    "gamerule advance_time false", "gamerule advance_weather false", "gamerule spawn_mobs false", "gamerule spawn_monsters false",
    "gamerule fire_spread_radius_around_player 0", "gamerule spawn_phantoms false", "gamerule spawn_patrols false", "gamerule spawn_wandering_traders false",
    "gamerule keep_inventory false", "gamerule mob_griefing true", "gamerule respawn_radius 0", "gamerule players_sleeping_percentage 100",
    "gamerule immediate_respawn false", "gamerule show_advancement_messages false", "gamerule spawner_blocks_work true", "gamerule spawn_wardens false",
    "difficulty hard",
    "weather thunder 1000000",
    "scoreboard players set #zeit nw.zeit 1000", "time set 1000",
    "scoreboard players set #konto nw.konto 0", "scoreboard players set #abbau nw.abbau 0", "scoreboard players set #phase nw.phase 1",
    "scoreboard players set #nacht nw.nacht 0", "scoreboard players set #gegner nw.gegner 0", "scoreboard players set #status nw.status 0",
    "scoreboard players set #modus nw.status 0", "scoreboard players set #finale nw.status 0", "scoreboard players set #kills nw.kills 0",
    "scoreboard players set #verdient nw.verdient 0", "scoreboard players set #tode nw.tode 0", f"scoreboard players set #leben nw.leben {LEBEN_START}", "scoreboard players set #ende nw.status 0", "scoreboard players set #glocke nw.upgrade 0", "scoreboard players set #kontrakt nw.upgrade 0", "kill @e[type=marker,tag=nw.laterne]", "kill @e[tag=nw.zwerg]", "kill @e[tag=nw.zwerg_k]", "kill @e[tag=nw.zwerg_a]",
    "scoreboard players set #boss nw.boss 0",
    f"forceload add -20 -20 20 100",
    f"function {NS}:welt/startinsel", f"function {NS}:welt/stand", f"function {NS}:welt/gegnerinsel",
    f"function {NS}:quell/setzen",
    f"function {NS}:sammler/erscheinen",
    f"spawnpoint @a {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    f"setworldspawn {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    "scoreboard players set #init nw.status 1", f"scoreboard players set #version nw.status {PACK_VERSION}",
    f"function {NS}:anzeige/aktualisieren",
    f"tellraw @a {J([txt('[Nightwatch] ', 'dark_red'), txt('The world is built. The Source stands in the middle, the Collector waits at his stall.', 'gray')])}",
]
fn("init", init)

# Startinsel: laengliche Ellipse, Bruecke am +z-Ende, Beacon am -z-Ende, Generator in der Mitte
RX, RZ, ZM = INSEL_RX, INSEL_RZ, INSEL_ZM
start = []
start += ellipse_fills(0, ZM, RX, RZ, BODEN_Y, BODEN_Y, "minecraft:grass_block")
start += ellipse_fills(0, ZM, RX, RZ, BODEN_Y - 3, BODEN_Y - 1, "minecraft:dirt")
start += ellipse_fills(0, ZM, RX - 1, RZ - 1, BODEN_Y - 6, BODEN_Y - 4, "minecraft:deepslate")
start += ellipse_fills(0, ZM, RX - 3, RZ - 4, BODEN_Y - 8, BODEN_Y - 7, "minecraft:deepslate")
start += ellipse_fills(0, ZM, RX - 5, RZ - 8, BODEN_Y - 9, BODEN_Y - 9, "minecraft:deepslate")
# Steg zur Strasse (Teil der Insel, luecken- und gelaenderlos)
start += [
    f"fill -1 {BODEN_Y} {ZM+RZ-2} 1 {BODEN_Y} {ZM+RZ} minecraft:polished_deepslate",
    f"fill -1 {BODEN_Y+1} {ZM+RZ-2} 1 {BODEN_Y+2} {ZM+RZ} minecraft:air",
    # verkohlter Baum, seitlich am Beaconende
    "fill 5 64 -14 5 68 -14 minecraft:stripped_dark_oak_log",
    "setblock 5 69 -14 minecraft:stripped_dark_oak_log", "setblock 4 68 -14 minecraft:stripped_dark_oak_log[axis=x]",
    "setblock 6 67 -14 minecraft:stripped_dark_oak_log[axis=x]", "setblock 6 67 -13 minecraft:stripped_dark_oak_log[axis=z]",
    "setblock 5 70 -14 minecraft:dark_oak_leaves[persistent=true]",
    # Herz der Insel: roter Beacon auf einem Eisensockel
    f"fill {BEACON[0]-1} {BEACON[1]-1} {BEACON[2]-1} {BEACON[0]+1} {BEACON[1]-1} {BEACON[2]+1} minecraft:iron_block",
    f"setblock {BEACON[0]} {BEACON[1]} {BEACON[2]} minecraft:beacon",
    f"setblock {BEACON[0]} {BEACON[1]+1} {BEACON[2]} minecraft:red_stained_glass",
    # Lichter entlang des Wegs
    "setblock 5 64 2 minecraft:soul_lantern", "setblock -5 64 -2 minecraft:soul_lantern",
    "setblock 4 64 -19 minecraft:soul_lantern", "setblock -4 64 -19 minecraft:soul_lantern",
]
fn("welt/startinsel", start)

# Stand des Sammlers: 3 Bloecke Front (Doppeltruhe + Fass), der Sammler direkt dahinter, Wand im Ruecken,
# Dach direkt darueber. Bauwerk x LADEN[0]-2 .. +2, z LADEN[2]-2 .. LADEN[2], y 63..66 (Luis 08.09.2026).
LX, LY, LZ = LADEN
SCHUTT = ('minecraft:polished_deepslate', 'minecraft:deepslate_bricks', 'minecraft:crimson_slab',
          'minecraft:soul_lantern', 'minecraft:crimson_wall_sign', 'minecraft:chest', 'minecraft:barrel')
stand = [
    f"fill {LX-2} {BODEN_Y} {LZ-2} {LX+2} {BODEN_Y} {LZ} minecraft:polished_deepslate",          # Boden
    f"fill {LX-2} 64 {LZ-2} {LX+2} 65 {LZ-2} minecraft:deepslate_bricks",                        # Rueckwand
    f"fill {LX-2} 64 {LZ-1} {LX-2} 65 {LZ} minecraft:deepslate_bricks",                          # Seite links
    f"fill {LX+2} 64 {LZ-1} {LX+2} 65 {LZ} minecraft:deepslate_bricks",                          # Seite rechts
    f"fill {LX-1} 64 {LZ-1} {LX+1} 65 {LZ-1} minecraft:air",                                     # ein Block Platz fuer den Sammler
    f"fill {LX-1} 65 {LZ} {LX+1} 65 {LZ} minecraft:air",                                         # Front ueber dem Tresen offen
    f"fill {LX-2} 66 {LZ-2} {LX+2} 66 {LZ} minecraft:crimson_slab[type=bottom]",                 # Dach
    f"execute unless block {LX-2} 67 {LZ} minecraft:soul_lantern run setblock {LX-2} 67 {LZ} minecraft:soul_lantern",
    f"execute unless block {LX+2} 67 {LZ} minecraft:soul_lantern run setblock {LX+2} 67 {LZ} minecraft:soul_lantern",
    f'execute unless block {LX-2} 65 {LZ+1} minecraft:crimson_wall_sign run setblock {LX-2} 65 {LZ+1} '
    f'minecraft:crimson_wall_sign[facing=south]{{front_text:{{messages:["",{{text:"THE",color:"dark_red"}},{{text:"COLLECTOR",color:"dark_red"}},""]}}}}',
    f"function {NS}:sammler/tresen",
]
# Der ganze Stand ist unzerstoerbar: was abgeschlagen wird, ist zwei Ticks spaeter wieder da und das Item verschwindet
stand += [f'kill @e[type=item,x={LX-2},y={BODEN_Y-1},z={LZ-2},dx=5,dy=6,dz=4,nbt={{Item:{{id:"{b}"}}}}]' for b in SCHUTT]
fn("welt/stand", stand)

# Gegnerinsel
GZ, GR = GEGNER_Z, GEGNER_RADIUS
geg = [f"fill -{GR+1} {BODEN_Y+1} {GZ-GR-1} {GR+1} {BODEN_Y+12} {GZ+GR+1} minecraft:air"]   # alles Gebaute darueber weg
geg += kreis_fills(0, GZ, GR, BODEN_Y, BODEN_Y, "minecraft:blackstone")
geg += kreis_fills(0, GZ, GR, BODEN_Y - 3, BODEN_Y - 1, "minecraft:deepslate")
geg += kreis_fills(0, GZ, GR - 2, BODEN_Y - 6, BODEN_Y - 4, "minecraft:deepslate")
geg += kreis_fills(0, GZ, GR - 5, BODEN_Y - 8, BODEN_Y - 7, "minecraft:deepslate")
geg += kreis_fills(0, GZ, 3, BODEN_Y, BODEN_Y, "minecraft:soul_soil")
geg += [
    f"setblock 0 {BODEN_Y+1} {GZ} minecraft:soul_fire",
    f"setblock 4 {BODEN_Y} {GZ+3} minecraft:soul_soil", f"setblock 4 {BODEN_Y+1} {GZ+3} minecraft:soul_fire",
    f"setblock -5 {BODEN_Y} {GZ-2} minecraft:soul_soil", f"setblock -5 {BODEN_Y+1} {GZ-2} minecraft:soul_fire",
    f"fill -3 {BODEN_Y} {GZ+5} -1 {BODEN_Y} {GZ+7} minecraft:netherrack", f"fill 5 {BODEN_Y} {GZ-6} 7 {BODEN_Y} {GZ-4} minecraft:netherrack",
    f"fill -7 {BODEN_Y} {GZ+1} -5 {BODEN_Y} {GZ+3} minecraft:soul_sand",
    # tote Baeume
    f"fill 6 {BODEN_Y+1} {GZ+5} 6 {BODEN_Y+5} {GZ+5} minecraft:crimson_stem", f"setblock 7 {BODEN_Y+4} {GZ+5} minecraft:crimson_stem[axis=x]",
    f"fill -7 {BODEN_Y+1} {GZ-5} -7 {BODEN_Y+4} {GZ-5} minecraft:crimson_stem", f"setblock -7 {BODEN_Y+3} {GZ-6} minecraft:crimson_stem[axis=z]",
    f"fill 0 {BODEN_Y+1} {GZ+9} 0 {BODEN_Y+3} {GZ+9} minecraft:crimson_stem",
    # Lichter und Rahmen
    f"setblock 3 {BODEN_Y+1} {GZ-8} minecraft:shroomlight", f"setblock -3 {BODEN_Y+1} {GZ-8} minecraft:shroomlight",
    f"setblock 8 {BODEN_Y+1} {GZ} minecraft:crying_obsidian", f"setblock -8 {BODEN_Y+1} {GZ} minecraft:crying_obsidian",
    f"setblock 0 {BODEN_Y+1} {GZ+10} minecraft:crying_obsidian",
    f"fill -1 {BODEN_Y} {GZ-GR-1} 1 {BODEN_Y} {GZ-GR+1} minecraft:blackstone",   # Steg zur Strasse (z 60..62)
    f"fill -1 {BODEN_Y+1} {GZ-GR} 1 {BODEN_Y+1} {GZ-GR} minecraft:air",   # Strassenmuendung frei
    f"setblock -2 {BODEN_Y+1} {GZ-GR} minecraft:crying_obsidian", f"setblock 2 {BODEN_Y+1} {GZ-GR} minecraft:crying_obsidian",
    f"setblock -2 {BODEN_Y+2} {GZ-GR} minecraft:shroomlight", f"setblock 2 {BODEN_Y+2} {GZ-GR} minecraft:shroomlight",
]
fn("welt/gegnerinsel", geg)

# Strasse
# REGEL (Lehre vom 06.09.2026): Bloecke, die einen Traeger brauchen (Fackeln, Laternen, Schilder, Zaeune mit
# Fackel drauf), NIE per fill/setblock jeden Tick neu setzen und NIE ihren Traeger per fill wegnehmen. Der
# Nachbar-Update beim Entfernen des Traegers laesst sie sofort als Item abfallen, auch wenn sie im selben Tick
# neu gesetzt werden. Deshalb: nur setzen, wenn sie fehlen (execute unless block), und Luft nur dort fuellen,
# wo kein Traeger steht.
Z1, Z2 = STRASSE_Z
POSTEN = list(range(Z1 + 2, Z2, 6))          # z-Positionen der Pfosten (x = -2 und 2)

def strasse_bauen():
    out = [
        f"fill -1 {BODEN_Y} {Z1} 1 {BODEN_Y} {Z2} minecraft:crimson_planks",            # Gehweg
        f"fill -1 {BODEN_Y+1} {Z1} 1 {BODEN_Y+3} {Z2} minecraft:air",                   # ueber dem Gehweg frei
        f"fill -3 {BODEN_Y-1} {Z1} 3 {BODEN_Y-1} {Z2} minecraft:air",                   # darunter frei
        f"fill -3 {BODEN_Y} {Z1} -3 {BODEN_Y+3} {Z2} minecraft:air", f"fill 3 {BODEN_Y} {Z1} 3 {BODEN_Y+3} {Z2} minecraft:air",   # Aussenkanten frei
        f"fill -2 {BODEN_Y+2} {Z1} -2 {BODEN_Y+3} {Z2} minecraft:air", f"fill 2 {BODEN_Y+2} {Z1} 2 {BODEN_Y+3} {Z2} minecraft:air",  # ueber den Pfosten frei
    ]
    # Pfostenspalten (x = +-2, y 63..64): Luft nur ZWISCHEN den Pfosten
    grenzen = [Z1 - 1] + POSTEN + [Z2 + 1]
    for a, b in zip(grenzen, grenzen[1:]):
        if b - a > 1:
            for x in (-2, 2):
                out.append(f"fill {x} {BODEN_Y} {a+1} {x} {BODEN_Y+1} {b-1} minecraft:air")
    # Pfosten nur setzen, wenn sie fehlen
    for z in POSTEN:
        for x in (-2, 2):
            out.append(f"execute unless block {x} {BODEN_Y} {z} minecraft:crimson_fence run setblock {x} {BODEN_Y} {z} minecraft:crimson_fence")
            out.append(f"execute unless block {x} {BODEN_Y+1} {z} minecraft:redstone_torch run setblock {x} {BODEN_Y+1} {z} minecraft:redstone_torch[lit=true]")
    out.append(f"execute as @e[type=marker,tag=nw.laterne,x=-3,y={BODEN_Y},z={Z1},dx=6,dy=3,dz={Z2-Z1}] at @s run function {NS}:laterne/halten")
    return out

fn("strasse/bauen", strasse_bauen())
# Entfernen: erst die Fackeln, dann die Pfosten, dann der Rest (so faellt nichts ab)
fn("strasse/entfernen", [f"fill -2 {BODEN_Y+1} {Z1} -2 {BODEN_Y+1} {Z2} minecraft:air", f"fill 2 {BODEN_Y+1} {Z1} 2 {BODEN_Y+1} {Z2} minecraft:air",
                         f"fill -3 {BODEN_Y-1} {Z1} 3 {BODEN_Y+3} {Z2} minecraft:air",
                         f"execute as @e[type=marker,tag=nw.laterne,x=-3,y={BODEN_Y},z={Z1},dx=6,dy=3,dz={Z2-Z1}] at @s run function {NS}:laterne/halten"])

# ----------------------------------------------------------------------------
# Collector Lantern: Marker je gesetzter Laterne, Gegner im Umkreis 8 langsam, drei Naechte
# ----------------------------------------------------------------------------
w(f"{NS}/advancement/laterne_gesetzt.json", {"criteria": {"gesetzt": {"trigger": "minecraft:placed_block", "conditions": {
    "item": {"items": "minecraft:soul_lantern", "predicates": {"minecraft:custom_data": "{nw_laterne:1b}"}}}}},
    "rewards": {"function": f"{NS}:laterne/gesetzt"}})
fn("laterne/gesetzt", [
    f"advancement revoke @s only {NS}:laterne_gesetzt",
    "scoreboard players set #strahl nw.tmp2 28",
    f"execute at @s anchored eyes positioned ^ ^ ^ run function {NS}:laterne/strahl",
])
fn("laterne/strahl", [
    f"execute if block ~ ~ ~ minecraft:soul_lantern unless entity @e[type=marker,tag=nw.laterne,distance=..0.9] run return run function {NS}:laterne/markieren",
    "scoreboard players remove #strahl nw.tmp2 1",
    f"execute if score #strahl nw.tmp2 matches 1.. positioned ^ ^ ^0.25 run function {NS}:laterne/strahl",
])
fn("laterne/markieren", [
    'execute align xyz positioned ~0.5 ~0.5 ~0.5 run summon minecraft:marker ~ ~ ~ {Tags:["nw.laterne"]}',
    "execute align xyz positioned ~0.5 ~0.5 ~0.5 run scoreboard players set @e[type=marker,tag=nw.laterne,distance=..0.9] nw.laterne 0",
    "execute align xyz positioned ~0.5 ~0.5 ~0.5 run particle minecraft:soul ~ ~ ~ 0.3 0.3 0.3 0.02 20",
    "playsound minecraft:block.respawn_anchor.charge block @s ~ ~ ~ 1 0.7",
    "tellraw @s " + J([txt("The lantern burns. Enemies near it slow down. Three nights.", "aqua")]),
])
fn("laterne/halten", [       # Strasse wird alle 2 Ticks neu gesetzt: Stuetze und Laterne wieder hinstellen (Stuetze zuerst)
    f"execute unless block ~ ~-1 ~ minecraft:crimson_planks run setblock ~ ~-1 ~ minecraft:crimson_planks",
    "execute unless block ~ ~ ~ minecraft:soul_lantern run setblock ~ ~ ~ minecraft:soul_lantern",
])
fn("laterne/sekunde", [f"execute as @e[type=marker,tag=nw.laterne] at @s run function {NS}:laterne/eine"])

# ----------------------------------------------------------------------------
# Der Zwerg: Marker (Logik) + zwei item_displays (Koerper, Axt-Arm) + unsichtbares Fass (Rucksack, 26 Faecher + Upgrade-Symbol)
# ----------------------------------------------------------------------------
import math as _m
qx, qy, qz = QUELL
ZWERG_UP_PRED = "*[custom_data~{nw_zwerg_up:1b}]"
ZWERG_BP_PRED = "*[custom_data~{nw_zwerg_bp:1b}]"
ZWERG_SELL_PRED = "*[custom_data~{nw_zwerg_sell:1b}]"
ZWERG_LOCK_PRED = "*[custom_data~{nw_zwerg_lock:1b}]"
def _quat_x(grad):
    a = _m.radians(grad); return (round(_m.sin(a / 2), 5), 0, 0, round(_m.cos(a / 2), 5))
def _arm_transform(grad):
    """Drehung des Arms um die Schulter (Modellkoordinaten 1.5, 9, 7.5 -> Blockkoordinaten um die Mitte)."""
    px, py, pz = (1.5 - 8) / 16, (9 - 8) / 16, (7.5 - 8) / 16
    a = _m.radians(grad); c, s = _m.cos(a), _m.sin(a)
    ry, rz = py * c - pz * s, py * s + pz * c          # R * p
    tx, ty, tz = 0, round(py - ry, 5), round(pz - rz, 5)
    q = _quat_x(grad)
    return f"{{left_rotation:[{q[0]}f,{q[1]}f,{q[2]}f,{q[3]}f],translation:[{tx}f,{ty}f,{tz}f],scale:[1f,1f,1f],right_rotation:[0f,0f,0f,1f]}}"
def _display(tag, modell, yaw):
    # brightness fest: die Displays stecken im (unsichtbaren) Fass, dort ist Lichtwert 0 und das Modell waere schwarz
    return (f'summon minecraft:item_display ~ ~ ~ {{Tags:["{tag}"],Rotation:[{yaw}f,0f],item_display:"none",interpolation_duration:2,brightness:{{sky:15,block:15}},'
            f'item:{{id:"minecraft:stick",count:1,components:{{"minecraft:item_model":"nachtwache:{modell}"}}}}}}')
# Die acht Nachbarfelder des Quells. Fraggle belegt sein Feld und ein zweites Feld radial nach aussen,
# beide sind unsichtbare Fallentruhen und bilden zusammen eine Doppeltruhe mit 54 Faechern (sechs Reihen).
# Sein eigener Block ist die obere Haelfte (type=right), der Block aussen die untere.
def _partner(dx, dz):
    return (1 if dx > 0 else -1, 0) if dx else (0, 1 if dz > 0 else -1)
_FACING = {(1, 0): "south", (-1, 0): "north", (0, 1): "west", (0, -1): "east"}
ZWERG_FELDER = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dz) != (0, 0)]

def zwerg_bloecke(dx, dz):
    """(eigener Block, Block aussen, facing) fuer ein Nachbarfeld."""
    ax, az = _partner(dx, dz)
    return (qx + dx, qy, qz + dz), (qx + dx + ax, qy, qz + dz + az), _FACING[(ax, az)]

def zwerg_slot(feld, gui):
    """GUI-Fach 0..53 -> (Blockkoordinaten, Fach im Block)."""
    eigen, aussen, _ = zwerg_bloecke(*feld)
    return (eigen if gui < 27 else aussen), (gui if gui < 27 else gui - 27)

ZWERG_LAGER_ENDE = lambda reihen: reihen * 9 - 3     # Faecher 0 .. ENDE-1 sind Lager, danach die drei Knoepfe

fn("zwerg/migrieren", [
    "kill @e[type=item_display,tag=nw.zwerg_k,distance=..0.1]", "kill @e[type=item_display,tag=nw.zwerg_a,distance=..0.1]",
    "setblock ~ ~ ~ minecraft:air destroy",
    'kill @e[type=item,distance=..3.5,nbt={Item:{id:"minecraft:trapped_chest"}}]',
    'kill @e[type=item,distance=..3.5,nbt={Item:{components:{"minecraft:custom_data":{nw_zwerg_lock:1b}}}}]',
    *[f"tag @s remove nw.bp{b}" for b in range(1, 4)],
    "tag @s add nw.bp0", "scoreboard players set @s nw.zwerg_b 0",
    "tag @s remove nw.zwerg", "tag @s add nw.zwerg_neu",
])
# Reste alter Fassungen: verwaiste Fallentruhen rund um den Quell abraeumen (nur bei der Migration)
fn("zwerg/altlast", [f"execute if block {qx+dx} {qy} {qz+dz} minecraft:trapped_chest run setblock {qx+dx} {qy} {qz+dz} minecraft:air destroy"
                     for dx in range(-2, 3) for dz in range(-2, 3) if (dx, dz) != (0, 0)])

fn("zwerg/tick", [
    f"execute as @e[type=marker,tag=nw.zwerg_neu] at @s run function {NS}:zwerg/neu",
    f"execute as @e[type=marker,tag=nw.zwerg] at @s run function {NS}:zwerg/einer",
])
# Fraggle steht frei auf der Insel, braucht aber einen Generator direkt vor sich (vier Seiten je Generator).
# Richtung 0 = Norden (-z), 1 = Osten (+x), 2 = Sueden (+z), 3 = Westen (-x)
ZWERG_RICHTUNGEN = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
ZWERG_YAW = {0: 180, 1: 270, 2: 0, 3: 90}
def zwerg_vor(d):
    dx, dz = ZWERG_RICHTUNGEN[d]
    return f"~{dx} ~ ~{dz}"

neu = [
    "tag @s remove nw.zwerg_neu",
    "execute align xyz positioned ~0.5 ~0.5 ~0.5 run tp @s ~ ~ ~",
    f"execute unless block ~ ~ ~ minecraft:air run return run function {NS}:zwerg/zurueck",
    f"execute if block ~ ~-1 ~ minecraft:air run return run function {NS}:zwerg/zurueck",
    "scoreboard players set @s nw.zwerg_d -1",
]
for d in range(4):
    neu.append(f"execute positioned {zwerg_vor(d)} if entity @e[type=marker,tag=nw.gen,distance=..0.2] "
               f"run scoreboard players set @s nw.zwerg_d {d}")
neu += [
    f"execute if score @s nw.zwerg_d matches -1 run return run function {NS}:zwerg/zurueck",
    f"function {NS}:zwerg/setzen",
]
fn("zwerg/neu", neu)

# Blickrichtung: Grundwinkel aus der gespeicherten Richtung plus Versatz #zoff nw.status
zeichnen = ["kill @e[type=item_display,tag=nw.zwerg_k,distance=..0.1]", "kill @e[type=item_display,tag=nw.zwerg_a,distance=..0.1]",
            f"execute unless score #zoff nw.status matches -1000.. run scoreboard players set #zoff nw.status {ZWERG_YAW_VERSATZ}",
            "scoreboard players set #yaw nw.tmp2 0"]
for d in range(4):
    zeichnen.append(f"execute if score @s nw.zwerg_d matches {d} run scoreboard players set #yaw nw.tmp2 {ZWERG_YAW[d]}")
zeichnen += [
    "scoreboard players operation #yaw nw.tmp2 += #zoff nw.status", "scoreboard players add #yaw nw.tmp2 720",
    "scoreboard players operation #yaw nw.tmp2 %= #360 nw.const",
    "execute store result storage nachtwache:tmp yaw int 1 run scoreboard players get #yaw nw.tmp2",
    f"function {NS}:zwerg/displays with storage nachtwache:tmp",
]
fn("zwerg/zeichnen", zeichnen)
fn("zwerg/displays", ["$" + _display("nw.zwerg_k", "dwarf_body", "$(yaw)"), "$" + _display("nw.zwerg_a", "dwarf_arm", "$(yaw)")])
fn("zwerg/zurueck", [
    *[f"execute if entity @s[tag=nw.lvl{l}] if entity @s[tag=nw.bp{b}] as @p[distance=..10] run give @s {zwerg_item(l, b)}"
      for l in range(ZWERG_MAX + 1) for b in range(ZWERG_BP_MAX + 1)],
    "tellraw @p[distance=..10] " + J([txt("[Fraggle] ", "aqua"), txt("Put me next to a Source Generator, on solid ground. I need one right in front of me.", "gray")]),
    "kill @s",
])
setzen = ["tag @s add nw.zwerg", "scoreboard players set @s nw.zwerg 0", "scoreboard players set @s nw.zwerg_t 0", "scoreboard players set @s nw.zwerg_b 0"]
setzen += [f"execute if entity @s[tag=nw.lvl{l}] run scoreboard players set @s nw.zwerg {l}" for l in range(1, ZWERG_MAX + 1)]
setzen += [f"execute if entity @s[tag=nw.bp{b}] run scoreboard players set @s nw.zwerg_b {b}" for b in range(1, ZWERG_BP_MAX + 1)]
# Ausrichtung im Schachbrettmuster nach Blockkoordinaten, damit zwei benachbarte Zwerge nie eine Doppeltruhe bilden
setzen += [
    "execute store result score #cx nw.tmp2 run data get entity @s Pos[0] 2",
    "execute store result score #cz nw.tmp2 run data get entity @s Pos[2] 2",
    "scoreboard players remove #cx nw.tmp2 1", "scoreboard players remove #cz nw.tmp2 1",
    "scoreboard players operation #cx nw.tmp2 /= #2 nw.const", "scoreboard players operation #cz nw.tmp2 /= #2 nw.const",
    "scoreboard players operation #cx nw.tmp2 += #cz nw.tmp2", "scoreboard players operation #cx nw.tmp2 %= #2 nw.const",
    "execute if score #cx nw.tmp2 matches 0 run setblock ~ ~ ~ minecraft:trapped_chest[facing=north,type=single]",
    "execute if score #cx nw.tmp2 matches 1 run setblock ~ ~ ~ minecraft:trapped_chest[facing=east,type=single]",
]
setzen += [
    f"function {NS}:zwerg/zeichnen",
    f"function {NS}:zwerg/symbol",
    "playsound minecraft:entity.villager.work_toolsmith neutral @a ~ ~ ~ 1 0.8",
    "tellraw @a[distance=..12] " + J([txt("Fraggle takes his place at the generator. Right-click him for his pack.", "aqua")]),
]
fn("zwerg/setzen", setzen)

# Knoepfe rechts in der letzten offenen Reihe, davor Lager, danach gesperrt
symbol = []
for b in range(ZWERG_BP_MAX + 1):
    ende = ZWERG_LAGER_ENDE(ZWERG_REIHEN_START + b)
    for sl in range(27):
        ziel = f"~ ~ ~ container.{sl}"
        if sl < ende:
            symbol.append(f"execute if score @s nw.zwerg_b matches {b} if items block {ziel} {ZWERG_LOCK_PRED} run item replace block {ziel} with minecraft:air")
            if sl >= ZWERG_LAGER_ENDE(ZWERG_REIHEN_START):
                for pred in (ZWERG_SELL_PRED, ZWERG_BP_PRED, ZWERG_UP_PRED):
                    symbol.append(f"execute if score @s nw.zwerg_b matches {b} if items block {ziel} {pred} run item replace block {ziel} with minecraft:air")
        elif sl == ende:
            symbol.append(f"execute if score @s nw.zwerg_b matches {b} run item replace block {ziel} with {ZWERG_VERKAUF_KNOPF}")
        elif sl == ende + 1:
            symbol.append(f"execute if score @s nw.zwerg_b matches {b} run item replace block {ziel} with {zwerg_bp_knopf(b)}")
        elif sl == ende + 2:
            for l in range(ZWERG_MAX + 1):
                symbol.append(f"execute if score @s nw.zwerg_b matches {b} if score @s nw.zwerg matches {l} run item replace block {ziel} with {zwerg_up_knopf(l)}")
        else:
            symbol.append(f"execute if score @s nw.zwerg_b matches {b} run item replace block {ziel} with {ZWERG_SPERRE}")
for l in range(ZWERG_MAX + 1):
    symbol.append(f'execute if score @s nw.zwerg matches {l} run data merge block ~ ~ ~ '
                  f'{{CustomName:[{{text:"Fraggle   ",color:"aqua"}},{{text:"Level {l}",color:"gray"}}]}}')
fn("zwerg/symbol", symbol)

fn("zwerg/einer", [
    f"execute unless block ~ ~ ~ minecraft:trapped_chest run return run function {NS}:zwerg/kaputt",
    "scoreboard players add @s nw.zwerg_t 1",
    "scoreboard players operation #iv nw.tmp2 = @s nw.zwerg",
    f"scoreboard players operation #iv nw.tmp2 *= #{ZWERG_STUFE_TICKS} nw.const",
    f"scoreboard players set #takt nw.tmp2 {ZWERG_TAKT}",
    "scoreboard players operation #takt nw.tmp2 -= #iv nw.tmp2",
    f"execute if score @s nw.zwerg_t >= #takt nw.tmp2 run function {NS}:zwerg/schlag",
    f"execute if score @s nw.zwerg_t matches 6 as @e[type=item_display,tag=nw.zwerg_a,distance=..0.1] run data merge entity @s {{start_interpolation:0,interpolation_duration:8,transformation:{_arm_transform(0)}}}",
    *[f"execute if score @s nw.zwerg_b matches {b} unless items block ~ ~ ~ container.{ZWERG_LAGER_ENDE(ZWERG_REIHEN_START + b) + off} {pred} run function {NS}:zwerg/{ziel}"
      for b in range(ZWERG_BP_MAX + 1)
      for off, pred, ziel in ((0, ZWERG_SELL_PRED, "verkauf_alles"), (1, ZWERG_BP_PRED, "rucksack"), (2, ZWERG_UP_PRED, "upgrade"))],
    f"clear @a[distance=..8] {ZWERG_LOCK_PRED}",
    f"execute if score #m20 nw.tmp matches 11 run function {NS}:zwerg/symbol",
])
schlag = ["scoreboard players set @s nw.zwerg_t 0", "scoreboard players set #gen nw.tmp2 0"]
for d in range(4):
    schlag.append(f"execute if score @s nw.zwerg_d matches {d} positioned {zwerg_vor(d)} "
                  f"if entity @e[type=marker,tag=nw.gen,distance=..0.2] run scoreboard players set #gen nw.tmp2 1")
schlag += [
    "execute if score #gen nw.tmp2 matches 0 run return 0",
    "execute store result score #voll nw.tmp2 run data get block ~ ~ ~ Items",
    "execute if score #voll nw.tmp2 matches 27.. run return run title @a[distance=..8] actionbar " + J([txt("Fraggle's pack is full. Sell it or buy a bigger one.", "red")]),
    f"execute as @e[type=item_display,tag=nw.zwerg_a,distance=..0.1] run data merge entity @s {{start_interpolation:0,interpolation_duration:2,transformation:{_arm_transform(-75)}}}",
]
for d in range(4):
    schlag.append(f"execute if score @s nw.zwerg_d matches {d} positioned {zwerg_vor(d)} "
                  f"run playsound minecraft:block.stone.hit block @a ~ ~ ~ 1 0.8")
    for i2, st in enumerate(STUFEN):
        schlag.append(f"execute if score @s nw.zwerg_d matches {d} if score #phase nw.phase matches {i2+1} "
                      f'positioned {zwerg_vor(d)} run particle minecraft:block{{block_state:"{st[0]}"}} ~ ~ ~ 0.3 0.3 0.3 0 12')
schlag.append(f"function {NS}:zwerg/abbau")
fn("zwerg/schlag", schlag)

fn("zwerg/upgrade", [
    "scoreboard players operation #lvl nw.tmp2 = @s nw.zwerg",
    "scoreboard players operation #up nw.tmp2 = #lvl nw.tmp2", "scoreboard players add #up nw.tmp2 1",
    f"scoreboard players operation #up nw.tmp2 *= #{ZWERG_UPGRADE_PREIS} nw.const",
    f"execute as @a[distance=..8] store result score @s nw.tmp run clear @s {ZWERG_UP_PRED} 0",
    f"execute as @a[distance=..8,scores={{nw.tmp=1..}}] run function {NS}:zwerg/upgrade_kauf",
    "scoreboard players operation @s nw.zwerg = #lvl nw.tmp2",
    f"function {NS}:zwerg/symbol",
])
fn("zwerg/upgrade_kauf", [
    f"clear @s {ZWERG_UP_PRED}",
    f"execute if score #lvl nw.tmp2 matches {ZWERG_MAX}.. run return run tellraw @s " + J([txt("[Fraggle] ", "aqua"), txt("Faster than this I will not go.", "gray")]),
    "execute if score #konto nw.konto < #up nw.tmp2 run tellraw @s " + J([txt("[Fraggle] ", "aqua"), txt("Not enough coins. ", "gray"), {"score": {"name": "#up", "objective": "nw.tmp2"}, "color": "gold"}, txt(" needed.", "gray")]),
    "execute if score #konto nw.konto < #up nw.tmp2 run return run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
    "scoreboard players operation #konto nw.konto -= #up nw.tmp2",
    "scoreboard players add #lvl nw.tmp2 1",
    "playsound minecraft:block.anvil.use block @s ~ ~ ~ 0.6 1.2",
    "tellraw @s " + J([txt("[Fraggle] ", "aqua"), txt("Sharper. Level ", "gray"), {"score": {"name": "#lvl", "objective": "nw.tmp2"}, "color": "aqua"}, txt(".", "gray")]),
])
fn("zwerg/rucksack", [
    "scoreboard players operation #bp nw.tmp2 = @s nw.zwerg_b",
    *[f"execute if score #bp nw.tmp2 matches {b} run scoreboard players set #bpp nw.tmp2 {ZWERG_BP_PREIS[b]}" for b in range(ZWERG_BP_MAX)],
    f"execute as @a[distance=..8] store result score @s nw.tmp run clear @s {ZWERG_BP_PRED} 0",
    f"execute as @a[distance=..8,scores={{nw.tmp=1..}}] run function {NS}:zwerg/rucksack_kauf",
    "scoreboard players operation @s nw.zwerg_b = #bp nw.tmp2",
    f"function {NS}:zwerg/symbol",
])
fn("zwerg/rucksack_kauf", [
    f"clear @s {ZWERG_BP_PRED}",
    f"execute if score #bp nw.tmp2 matches {ZWERG_BP_MAX}.. run return run tellraw @s " + J([txt("[Fraggle] ", "aqua"), txt("The pack holds no more.", "gray")]),
    "execute if score #konto nw.konto < #bpp nw.tmp2 run tellraw @s " + J([txt("[Fraggle] ", "aqua"), txt("Not enough coins. ", "gray"), {"score": {"name": "#bpp", "objective": "nw.tmp2"}, "color": "gold"}, txt(" needed.", "gray")]),
    "execute if score #konto nw.konto < #bpp nw.tmp2 run return run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
    "scoreboard players operation #konto nw.konto -= #bpp nw.tmp2",
    "scoreboard players add #bp nw.tmp2 1",
    "playsound minecraft:block.wool.place block @s ~ ~ ~ 0.8 1.2",
    "tellraw @s " + J([txt("[Fraggle] ", "aqua"), txt("One more row. Pack level ", "gray"), {"score": {"name": "#bp", "objective": "nw.tmp2"}, "color": "aqua"}, txt(".", "gray")]),
])
verkauf_alles = [f"clear @a[distance=..8] {ZWERG_SELL_PRED}", "scoreboard players set #erloes nw.tmp2 0"]
for b in range(ZWERG_BP_MAX + 1):
    for sl in range(ZWERG_LAGER_ENDE(ZWERG_REIHEN_START + b)):
        verkauf_alles.append(f"execute if score @s nw.zwerg_b matches {b} if items block ~ ~ ~ container.{sl} * "
                             f"unless items block ~ ~ ~ container.{sl} {ZWERG_LOCK_PRED} run function {NS}:zwerg/verkauf_fach {{slot:{sl}}}")
verkauf_alles += [
    "execute if score #erloes nw.tmp2 matches 1.. run playsound minecraft:entity.villager.trade neutral @a[distance=..12] ~ ~ ~ 0.8 1",
    "execute if score #erloes nw.tmp2 matches 1.. run tellraw @a[distance=..12] " + J([txt("[Fraggle] ", "aqua"), txt("Pack sold: +", "gray"), {"score": {"name": "#erloes", "objective": "nw.tmp2"}, "color": "gold"}, txt(" ", "gray"), coin()]),
    "execute if score #erloes nw.tmp2 matches ..0 run tellraw @a[distance=..12] " + J([txt("[Fraggle] ", "aqua"), txt("Nothing worth selling in here.", "gray")]),
    f"function {NS}:zwerg/symbol",
]
fn("zwerg/verkauf_alles", verkauf_alles)
fn("zwerg/verkauf_fach", [
    "$execute store result score #n nw.tmp run data get block ~ ~ ~ Items[{Slot:$(slot)b}].count",
    "$data modify storage nachtwache:tmp id set string block ~ ~ ~ Items[{Slot:$(slot)b}].id 10",
    "scoreboard players set #w nw.tmp2 0",
    f"function {NS}:sammler/preis with storage nachtwache:tmp",
    "execute if score #w nw.tmp2 matches ..0 run return 0",
    "scoreboard players operation #gain nw.tmp = #n nw.tmp", "scoreboard players operation #gain nw.tmp *= #w nw.tmp2",
    "execute if score #gain nw.tmp matches ..0 run return 0",
    "scoreboard players operation #konto nw.konto += #gain nw.tmp", "scoreboard players operation #verdient nw.verdient += #gain nw.tmp",
    "scoreboard players operation #erloes nw.tmp2 += #gain nw.tmp",
    "$item replace block ~ ~ ~ container.$(slot) with minecraft:air",
])
kaputt = [
    "kill @e[type=item_display,tag=nw.zwerg_k,distance=..0.1]", "kill @e[type=item_display,tag=nw.zwerg_a,distance=..0.1]",
    'kill @e[type=item,distance=..2.5,nbt={Item:{id:"minecraft:trapped_chest"}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_zwerg_up:1b}}}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_zwerg_bp:1b}}}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_zwerg_sell:1b}}}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_zwerg_lock:1b}}}}]',
]
for l in range(ZWERG_MAX + 1):
    for b in range(ZWERG_BP_MAX + 1):
        kaputt.append(f"execute if score @s nw.zwerg matches {l} if score @s nw.zwerg_b matches {b} as @p[distance=..10] run give @s {zwerg_item(l, b)}")
kaputt += [
    "tellraw @p[distance=..10] " + J([txt("[Fraggle] ", "aqua"), txt("Packing up. I am in your inventory.", "gray")]),
    "playsound minecraft:entity.item.pickup player @p[distance=..10] ~ ~ ~ 1 0.8",
    "kill @s",
]
fn("zwerg/kaputt", kaputt)
fn("laterne/eine", [
    "execute unless block ~ ~ ~ minecraft:soul_lantern run return run kill @s",
    "effect give @e[tag=nw.welle,distance=..8] minecraft:slowness 2 1 true",
    "particle minecraft:soul ~ ~0.2 ~ 0.2 0.2 0.2 0.01 3",
])
fn("laterne/erloschen", [
    "setblock ~ ~ ~ minecraft:air",
    f"execute if entity @s[x=-3,y={BODEN_Y},z={Z1},dx=6,dy=3,dz={Z2-Z1}] run setblock ~ ~-1 ~ minecraft:air",
    "particle minecraft:large_smoke ~ ~ ~ 0.2 0.2 0.2 0.02 15",
    "playsound minecraft:block.fire.extinguish block @a ~ ~ ~ 1 0.8",
    "tellraw @a " + J([txt("A Collector Lantern has burned out.", "gray", italic=True)]),
    "kill @s",
])

# ----------------------------------------------------------------------------
# tick
# ----------------------------------------------------------------------------
fn("tick", [
    "scoreboard players add #tick nw.tick 1",
    "scoreboard players operation #m20 nw.tmp = #tick nw.tick",
    "scoreboard players operation #m20 nw.tmp %= #20 nw.const",
    f"execute unless score #init nw.status matches 1 run return 0",
    f"function {NS}:uhr/tick",
    f"function {NS}:sammler/interaktion",
    f"function {NS}:sammler/kauf_tick",
    "scoreboard players operation #m5 nw.tmp = #tick nw.tick", "scoreboard players operation #m5 nw.tmp %= #5 nw.const",
    f"execute if score #m5 nw.tmp matches 0 run function {NS}:sammler/verkauf",
    f"execute as @a[scores={{nw.hilfe=1..}}] run function {NS}:hilfe",
    f"execute as @a[scores={{nw.endlos=1..}}] run function {NS}:nacht/endlos_an",
    f"execute as @a[scores={{nw.tode=1..}}] run function {NS}:spieler/tod",
    f"function {NS}:gegner/tick",
    f"function {NS}:schutz/tick",
    f"function {NS}:zwerg/tick",
    f"function {NS}:bogi/tick",
    f"function {NS}:gen/tick",
    f"execute as @a[tag=nw.admin,scores={{reset=1..}}] run function {NS}:admin/reset_trigger",
    f"execute as @a[tag=nw.admin,scores={{yes=1..}}] run function {NS}:admin/yes_trigger",
    f"execute as @a[tag=nw.admin,scores={{night=1..}}] run function {NS}:admin/night_trigger",
    f"execute as @a[tag=nw.admin,scores={{boss=1..}}] run function {NS}:admin/boss_trigger",
    f"execute as @a[tag=nw.admin,scores={{fraggle=1..}}] run function {NS}:admin/fraggle_trigger",
    f"execute as @a[tag=nw.admin,scores={{endnight=1..}}] run function {NS}:admin/endnight_trigger",
    f"execute as @a[tag=nw.admin,scores={{money=1..}}] run function {NS}:admin/money_trigger",
    f"execute as @a[tag=nw.admin,scores={{money=..-1}}] run function {NS}:admin/money_trigger",
    f"execute if score #m20 nw.tmp matches 0 run function {NS}:schutz/sekunde",
    f"execute if score #m20 nw.tmp matches 10 run function {NS}:anzeige/aktualisieren",
    f"execute if score #m20 nw.tmp matches 15 run function {NS}:uhr/anzeige",
    f"execute if score #m20 nw.tmp matches 5 run function {NS}:atmo/sekunde",
    f"function {NS}:spieler/bett",
    f"function {NS}:nacht/boss_tick",
])

# ----------------------------------------------------------------------------
# Quell
# ----------------------------------------------------------------------------
qx, qy, qz = QUELL
# Der Quell heisst jetzt Generator und steht als Marker in der Welt (siehe Abschnitt Generatoren).
# quell/setzen stellt den ersten Generator an seinen Platz, falls dort keiner steht.
fn("quell/setzen", [
    f"execute unless entity @e[type=marker,tag=nw.gen,x={qx},y={qy},z={qz},dx=0,dy=0,dz=0] "
    f"unless entity @e[type=marker,tag=nw.gen_neu,x={qx},y={qy},z={qz},dx=0,dy=0,dz=0] run "
    f'summon minecraft:marker {qx+0.5} {qy+0.5} {qz+0.5} {{Tags:["nw.gen_neu"]}}',
])

def abbau_lines(wer, loot_ziel, mit_anzeige):
  abbau = [
    f"scoreboard players set #wer nw.tmp {wer}",
    "scoreboard players add #abbau nw.abbau 1",
    "scoreboard players operation #splitter nw.tmp = #phase nw.phase",
]
  for p, s in SPLITTER_PRO_ABBAU.items():
    abbau.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #splitter nw.tmp {s}")
  abbau += [
    "execute if score #focus nw.upgrade matches 1.. run scoreboard players operation #splitter nw.tmp *= #2 nw.const",
    "scoreboard players operation #konto nw.konto += #splitter nw.tmp",
    "scoreboard players operation #verdient nw.verdient += #splitter nw.tmp",
    f"playsound minecraft:block.amethyst_block.break player @a ~ ~ ~ 0.6 0.7",
  ]
  for p in range(1, ANZ_STUFEN + 1):
    abbau.append(f"execute if score #phase nw.phase matches {p} if predicate {NS}:quell_mob_{p} run function {NS}:quell/mob_{p}")
    abbau.append(f"execute if score #phase nw.phase matches {p} unless score #mobda nw.tmp matches 1 run loot {loot_ziel} loot {NS}:quell/phase{p}")
  abbau.append("scoreboard players reset #mobda nw.tmp")
  if mit_anzeige:
    abbau.append(f'title @s actionbar {J([txt("+", "gold"), {"score": {"name": "#splitter", "objective": "nw.tmp"}, "color": "gold"}, txt(" ", "gray"), coin(), txt("   mined ", "gray"), {"score": {"name": "#abbau", "objective": "nw.abbau"}, "color": "gray"}])}')
  for i, g in enumerate(PHASEN_GRENZEN):
    abbau.append(f"execute if score #abbau nw.abbau matches {g} run function {NS}:quell/phase_wechsel {{phase:{i+2}}}")
  return abbau
fn("quell/abbau", abbau_lines(1, "give @s", True))
fn("zwerg/abbau", abbau_lines(2, "insert ~ ~ ~", False))

for p in range(1, ANZ_STUFEN + 1):
    ent, nbt = MOBS[MOB_AUS_QUELL[p]] if MOB_AUS_QUELL[p] in MOBS else (f"minecraft:{MOB_AUS_QUELL[p]}", "")
    fn(f"quell/mob_{p}", [
        "scoreboard players set #mobda nw.tmp 1",
        f"summon {ent} {qx+0.5} {qy+1} {qz+0.5} {{Tags:[\"nw.welle\",\"nw.quellmob\"],{nbt}}}",
        f"playsound minecraft:entity.evoker.prepare_summon hostile @a {qx} {qy} {qz} 1 0.6",
        f"tellraw @a {J([txt('Something crawled out of the Source.', 'dark_red', italic=True)])}",
    ])

fn("quell/phase_wechsel", [
    "$scoreboard players set #phase nw.phase $(phase)",
    '$title @a title {"text":"Tier $(phase)","color":"dark_purple"}',
    'title @a subtitle {"text":"The Source changes colour. New goods at the Collector.","color":"gray"}',
    f"function {NS}:quell/setzen",
    f"execute as @e[type=marker,tag=nw.gen] at @s run function {NS}:gen/farbe",
    f"execute as @e[type=marker,tag=nw.gen] at @s run function {NS}:gen/anzeige",
    "playsound minecraft:block.beacon.power_select master @a ~ ~ ~ 1 0.5",
    f"function {NS}:sammler/kaufmenue",
    f"function {NS}:sammler/spruch/phase",
])

# Loot-Tabellen des Quells
rows = read_csv("quell.csv")
def phasen_von(s):
    if "-" in s:
        a, b = s.split("-"); return range(int(a), int(b) + 1)
    return [int(s)]
for p in range(1, ANZ_STUFEN + 1):
    entries = []
    for r in rows:
        if p not in phasen_von(r["phasen"]):
            continue
        item = r["item"]; wgt = int(r["gewicht"]); mn, mx = int(r["min"]), int(r["max"])
        if item.startswith("KISTE_"):
            inhalt = [{"slot": i, "item": {"id": it, "count": c}} for i, (it, c) in enumerate(KISTEN[item])]
            entries.append({"type": "minecraft:item", "name": "minecraft:chest", "weight": wgt,
                            "functions": [{"function": "minecraft:set_components", "components": {"minecraft:container": inhalt}},
                                          {"function": "minecraft:set_name", "name": {"text": "Crate from the Source", "color": "gold"}, "target": "custom_name"}]})
        else:
            e = {"type": "minecraft:item", "name": f"minecraft:{item}", "weight": wgt}
            if mx > 1:
                e["functions"] = [{"function": "minecraft:set_count", "count": {"min": mn, "max": mx}}]
            entries.append(e)
    w(f"{NS}/loot_table/quell/phase{p}.json", {"pools": [{"rolls": 1, "entries": entries}]})

# Belohnung bei komplett getoeteter Welle ab Nacht 10
w(f"{NS}/loot_table/belohnung.json", {"pools": [{"rolls": 1, "entries": [
    {"type": "minecraft:item", "name": "minecraft:golden_apple", "weight": 6},
    {"type": "minecraft:item", "name": "minecraft:experience_bottle", "weight": 8, "functions": [{"function": "minecraft:set_count", "count": {"min": 4, "max": 8}}]},
    {"type": "minecraft:item", "name": "minecraft:diamond", "weight": 5, "functions": [{"function": "minecraft:set_count", "count": {"min": 1, "max": 2}}]},
    {"type": "minecraft:item", "name": "minecraft:enchanted_book", "weight": 4, "functions": [{"function": "minecraft:enchant_with_levels", "levels": 20}]},
    {"type": "minecraft:item", "name": "minecraft:saddle", "weight": 2},
    {"type": "minecraft:item", "name": "minecraft:totem_of_undying", "weight": 1},
    {"type": "minecraft:item", "name": "minecraft:arrow", "weight": 6, "functions": [{"function": "minecraft:set_count", "count": {"min": 16, "max": 32}}]},
    {"type": "minecraft:item", "name": "minecraft:iron_ingot", "weight": 6, "functions": [{"function": "minecraft:set_count", "count": {"min": 3, "max": 6}}]},
]}]})

# ----------------------------------------------------------------------------
# Anzeige (Seitenleiste)
# ----------------------------------------------------------------------------
# Icons als Schriftzeichen aus dem Ressourcenpaket (icons.py): Muenze ●, Stufenscheiben, Mond, Zombie, Totenkopf.
import icons
def icon(name):
    return {"text": icons.ZEICHEN[name] + " ", "color": "white"}

fn("anzeige/aktualisieren", [
    "scoreboard players set sb_5 nw.anzeige 5", "scoreboard players set sb_4 nw.anzeige 4", "scoreboard players set sb_3 nw.anzeige 3",
    "scoreboard players set sb_2 nw.anzeige 2", "scoreboard players set sb_1 nw.anzeige 1",
    "scoreboard players display name sb_5 nw.anzeige " + J([icon("coin"), txt("Coins  ", "gold"), {"score": {"name": "#konto", "objective": "nw.konto"}, "color": "yellow", "bold": True}]),
    f"function {NS}:anzeige/stufe",
    "scoreboard players display name sb_3 nw.anzeige " + J([icon("moon"), txt("Night  ", "red"), {"score": {"name": "#nacht", "objective": "nw.nacht"}, "color": "white"}]),
    "scoreboard players display name sb_2 nw.anzeige " + J([icon("heart"), txt("Lives  ", "red"), {"score": {"name": "#leben", "objective": "nw.leben"}, "color": "white", "bold": True}]),
    "scoreboard players display name sb_1 nw.anzeige " + J([icon("skull"), txt("Deaths  ", "dark_gray"), {"score": {"name": "#tode", "objective": "nw.tode"}, "color": "gray"}]),
])


FARBE_EN = {"Grau": "Gray", "Gruen": "Green", "Blau": "Blue", "Lila": "Purple", "Gelb": "Yellow", "Orange": "Orange", "Schwarz": "Black"}
# Stufenzeile: "<Scheibe> Tier 3  41%  620/1500", letzte Stufe "<Scheibe> Tier 7  max"
stufe = []
for i, st in enumerate(STUFEN):
    p = i + 1
    if p < ANZ_STUFEN:
        start = PHASEN_GRENZEN[i - 1] if i > 0 else 0
        ziel = PHASEN_GRENZEN[i]
        stufe.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #st_start nw.tmp2 {start}")
        stufe.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #st_ziel nw.tmp2 {ziel}")
    else:
        stufe.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #st_start nw.tmp2 {PHASEN_GRENZEN[-1]}")
        stufe.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #st_ziel nw.tmp2 0")
stufe += [
    "scoreboard players operation #st_hab nw.tmp2 = #abbau nw.abbau", "scoreboard players operation #st_hab nw.tmp2 -= #st_start nw.tmp2",
    "scoreboard players operation #st_soll nw.tmp2 = #st_ziel nw.tmp2", "scoreboard players operation #st_soll nw.tmp2 -= #st_start nw.tmp2",
    "scoreboard players operation #st_pct nw.tmp2 = #st_hab nw.tmp2", "scoreboard players operation #st_pct nw.tmp2 *= #100 nw.const",
    "execute if score #st_soll nw.tmp2 matches 1.. run scoreboard players operation #st_pct nw.tmp2 /= #st_soll nw.tmp2",
    "execute if score #st_soll nw.tmp2 matches ..0 run scoreboard players set #st_pct nw.tmp2 100",
    "execute if score #st_pct nw.tmp2 matches 101.. run scoreboard players set #st_pct nw.tmp2 100",
    "execute if score #st_pct nw.tmp2 matches ..-1 run scoreboard players set #st_pct nw.tmp2 0",
    "execute if score #st_hab nw.tmp2 matches ..-1 run scoreboard players set #st_hab nw.tmp2 0",
]
for i, st in enumerate(STUFEN):
    p = i + 1
    farbe = {"Grau": "gray", "Gruen": "green", "Blau": "blue", "Lila": "light_purple", "Gelb": "yellow", "Orange": "gold", "Schwarz": "dark_gray"}[st[1]]
    if p < ANZ_STUFEN:
        comp = [icon(f"tier{p}"), txt(f"Tier {p}  ", farbe), {"score": {"name": "#st_pct", "objective": "nw.tmp2"}, "color": "white"}, txt("%  ", "white"),
                {"score": {"name": "#st_hab", "objective": "nw.tmp2"}, "color": "gray"}, txt("/", "gray"), {"score": {"name": "#st_soll", "objective": "nw.tmp2"}, "color": "gray"}]
    else:
        comp = [icon(f"tier{p}"), txt(f"Tier {p}  ", farbe), txt("max", "white")]
    stufe.append(f"execute if score #phase nw.phase matches {p} run scoreboard players display name sb_4 nw.anzeige " + J(comp))
fn("anzeige/stufe", stufe)

# Hilfe
fn("hilfe", [
    "scoreboard players reset @s nw.hilfe", "scoreboard players enable @s nw.hilfe",
    "tellraw @s " + J([txt("--- NIGHTWATCH ---", "dark_red", bold=True)]),
    "tellraw @s " + J([txt("The Source ", "light_purple"), txt("in the middle gives blocks and coins. Mine it, everything goes straight into your inventory.", "gray")]),
    "tellraw @s " + J([txt("The Collector: ", "dark_red"), txt("chest on the left of the counter = BUY (click one, shift-click a stack). Barrel on the right = SELL (put goods in, coins are credited at once, he does not take tools). Hopper outside = drop-off, sells automatically at 80%.", "gray")]),
    "tellraw @s " + J([txt("At night ", "red"), txt("the wave comes over the road. The night only ends when everything is dead. Beds only work when nothing is alive. Walling up does not help, they dig.", "gray")]),
    "tellraw @s " + J([txt("Building ", "green"), txt("is allowed anywhere except the enemy island and the road.", "gray")]),
    "tellraw @s " + J([txt("Night 30 ", "dark_purple"), txt("is the last one. After that it is over, or ", "gray"), txt("[endless mode]", "yellow", click_event={"action": "run_command", "command": "trigger nw.endlos"}), txt(".", "gray")]),
])

# ----------------------------------------------------------------------------
# Sammler
# ----------------------------------------------------------------------------
sx, sy, sz = SAMMLER_POS
# Ankaufspreise: preise_abgeleitet.csv (alle Gegenstaende, aus preise.csv plus Spielrezepten, python3 preise_ableiten.py),
# falls die fehlt nur preise.csv
preise = read_csv("preise_abgeleitet.csv") if (TAB / "preise_abgeleitet.csv").exists() else read_csv("preise.csv")
preise = [r for r in preise if int(r["wert"]) >= 1]
angebot = read_csv("angebot.csv")
sprueche = read_csv("sprueche.csv")


# ----------------------------------------------------------------------------
# Bogi: der Bogenschuetzen-Zwerg. Steht ueberall auf der Insel, schiesst auf Gegner in Reichweite.
# Rucksack: eine Reihe (Faecher 0..8), rechts die sieben Knoepfe, links Platz fuer Pfeile.
# Alle Stufen stehen im data-Feld des Markers und ueberleben deshalb das Abbauen.
# ----------------------------------------------------------------------------
BOGI_PREIS = 7500
BOGI_TAKT = 60                          # Ticks je Schuss auf Stufe 0 (3 s)
# (Schluessel, Name, Symbol, Maxstufe, Preis je Stufe, Wirkungstext je Stufe)
BOGI_UPGRADES = [
    ("sp",  "Draw speed", "minecraft:feather",        4, 400, lambda n: f"one shot every {(BOGI_TAKT - 10 * n) / 20:.1f} s"),
    ("st",  "Power",      "minecraft:iron_sword",     4, 500, lambda n: f"{4 + 2 * n} damage per arrow"),
    ("mu",  "Multishot",  "minecraft:crossbow",       2, 2000, lambda n: f"{1 + n} target(s) per shot"),
    ("fl",  "Flame",      "minecraft:blaze_powder",   1, 1500, lambda n: "sets the target on fire" if n else "no fire"),
    ("inf", "Infinity",   "minecraft:end_crystal",    1, 4000, lambda n: "arrows are not used up" if n else "one arrow per shot"),
    ("kb",  "Knockback",  "minecraft:piston",         2, 800, lambda n: f"pushes {n} step(s) back" if n else "no knockback"),
    ("rg",  "Range",      "minecraft:spyglass",       2, 700, lambda n: f"{10 + 4 * n} blocks"),
]
BOGI_NAMEN = ["Tombo", "Svenjo", "Harzo", "Django", "Rocko", "Bendo", "Ferro", "Nurbo",
              "Wando", "Silko", "Grimbo", "Zappo", "Lumbo", "Kordo", "Mirko", "Tarbo"]
BOGI_SLOT = {"sp": 8, "st": 7, "mu": 6, "fl": 5, "inf": 4, "kb": 3, "rg": 2}   # von rechts nach links
BOGI_PFEIL_SLOTS = [0, 1]
BOGI_LAGER = 9                          # nur die erste Reihe ist offen, der Rest ist gesperrt
def bogi_takt(n): return BOGI_TAKT - 10 * n
def bogi_schaden(n): return 4 + 2 * n
def bogi_reichweite(n): return 10 + 4 * n

def bogi_item(werte=None, nr=0):
    """nr 1..16 = fester Name, 0 = noch keiner (der Laden vergibt ihn beim Kauf)."""
    w = werte or {k: 0 for k, *_ in BOGI_UPGRADES}
    modell = 'item_model="nachtwache:archer",' if RESSOURCENPAKET else ""
    name = BOGI_NAMEN[nr - 1] if 1 <= nr <= len(BOGI_NAMEN) else "Bogi"
    daten = ",".join(f"{k}:{w[k]}" for k, *_ in BOGI_UPGRADES) + f",nm:{nr}"
    lore = ('[{text:"Put him anywhere on your island, he shoots what comes close.",color:"gray",italic:false},'
            '{text:"Right-click: his row of slots. Arrows go left, upgrades are on the right.",color:"gray",italic:false},'
            '{text:"No arrows, no shots. Break him: he jumps back into your inventory.",color:"gray",italic:false}]')
    return (f'minecraft:zombie_spawn_egg[{modell}custom_name={{text:"{name}",color:"green",italic:false}},custom_data={{nw_bogi:1b}},'
            f'entity_data={{id:"minecraft:marker",Tags:["nw.bogi_neu"],data:{{{daten}}}}},lore={lore}]')

def _bogi_display(tag, modell):
    return (f'summon minecraft:item_display ~ ~ ~ {{Tags:["{tag}"],item_display:"none",interpolation_duration:2,brightness:{{sky:15,block:15}},'
            f'item:{{id:"minecraft:stick",count:1,components:{{"minecraft:item_model":"nachtwache:{modell}"}}}}}}')

fn("bogi/tick", [
    f"execute as @e[type=marker,tag=nw.bogi_neu] at @s run function {NS}:bogi/neu",
    f"execute as @e[type=marker,tag=nw.bogi] at @s run function {NS}:bogi/einer",
])
fn("bogi/neu", [
    "tag @s remove nw.bogi_neu",
    "execute align xyz positioned ~0.5 ~0.5 ~0.5 run tp @s ~ ~ ~",
    f"execute at @s unless block ~ ~ ~ minecraft:air run return run function {NS}:bogi/zurueck",
    f"execute at @s unless block ~ ~-1 ~ #{NS}:grabbar unless block ~ ~-1 ~ minecraft:grass_block run return run function {NS}:bogi/zurueck",
    "tag @s add nw.bogi",
    # ab hier auf der ausgerichteten Position weiterarbeiten, sonst stecken die Modelle im Boden
    # Stufen aus dem Marker lesen
    *[f"execute store result score @s nw.b_{k} run data get entity @s data.{k}" for k, *_ in BOGI_UPGRADES],
    "execute store result score @s nw.b_nm run data get entity @s data.nm",
    "scoreboard players set @s nw.b_t 0",
    # Fallentruhe als Rucksack, Ausrichtung so, dass keine Doppeltruhe entsteht
    "execute at @s run setblock ~ ~ ~ minecraft:trapped_chest[facing=north,type=single]",
    *[f"execute at @s unless block ~ ~ ~ minecraft:trapped_chest[type=single] run setblock ~ ~ ~ minecraft:trapped_chest[facing={d},type=single]"
      for d in ("east", "south", "west")],
    f"execute at @s run function {NS}:bogi/zeichnen",
    f"execute at @s run function {NS}:bogi/symbol",
    "playsound minecraft:entity.villager.work_fletcher neutral @a ~ ~ ~ 1 0.9",
    "tellraw @a[distance=..12] " + J([txt("Bogi takes his post. Give him arrows and he will shoot.", "green")]),
])
fn("bogi/zeichnen", [
    "kill @e[type=item_display,tag=nw.bogi_k,distance=..0.1]", "kill @e[type=item_display,tag=nw.bogi_a,distance=..0.1]",
    _bogi_display("nw.bogi_k", "archer_body"), _bogi_display("nw.bogi_a", "archer_arm"),
])
fn("bogi/zurueck", [
    *[f"data modify storage nachtwache:tmp {k} set from entity @s data.{k}" for k, *_ in BOGI_UPGRADES],
    "data modify storage nachtwache:tmp nm set from entity @s data.nm",
    "execute store result score #bnm nw.tmp2 run data get entity @s data.nm",
    f"execute as @p[distance=..10] run function {NS}:bogi/geben",
    "tellraw @p[distance=..10] " + J([txt("[Bogi] ", "green"), txt("Put me on a free block, on solid ground.", "gray")]),
    "kill @s",
])
# Item mit den Stufen des Markers zurueckgeben (Makro, damit nicht jede Kombination als eigene Zeile noetig ist)
for _n in range(len(BOGI_NAMEN) + 1):
    fn(f"bogi/geben_{_n}", [f"$give @s {bogi_item({k: '$(' + k + ')' for k, *_ in BOGI_UPGRADES}, _n)}"])
fn("bogi/geben", [f"execute if score #bnm nw.tmp2 matches {n} run function {NS}:bogi/geben_{n} with storage nachtwache:tmp"
                  for n in range(len(BOGI_NAMEN) + 1)]
   + [f"execute unless score #bnm nw.tmp2 matches 0..{len(BOGI_NAMEN)} run function {NS}:bogi/geben_0 with storage nachtwache:tmp"])

# Sekundentakt und Schuss
fn("bogi/einer", [
    f"execute unless block ~ ~ ~ minecraft:trapped_chest run return run function {NS}:bogi/kaputt",
    "scoreboard players add @s nw.b_t 1",
    "scoreboard players operation #bt nw.tmp2 = @s nw.b_sp",
    "scoreboard players operation #bt nw.tmp2 *= #10 nw.const",
    f"scoreboard players set #btakt nw.tmp2 {BOGI_TAKT}",
    "scoreboard players operation #btakt nw.tmp2 -= #bt nw.tmp2",
    f"execute if score @s nw.b_t >= #btakt nw.tmp2 run function {NS}:bogi/schuss",
    f"execute if score @s nw.b_t matches 5 as @e[type=item_display,tag=nw.bogi_a,distance=..0.1] run data merge entity @s {{start_interpolation:0,interpolation_duration:8,transformation:{_arm_transform(0)}}}",
    # Knoepfe und Sperren
    *[f"execute unless items block ~ ~ ~ container.{BOGI_SLOT[k]} *[custom_data~{{nw_bogi_{k}:1b}}] run function {NS}:bogi/kauf_{k}" for k, *_ in BOGI_UPGRADES],
    "clear @a[distance=..8] *[custom_data~{nw_bogi_lock:1b}]",
    f"execute if score #m20 nw.tmp matches 13 run function {NS}:bogi/symbol",
])
schuss = [
    "scoreboard players set @s nw.b_t 0",
    "scoreboard players operation #brg nw.tmp2 = @s nw.b_rg",
    "scoreboard players operation #bmu nw.tmp2 = @s nw.b_mu",
    "scoreboard players operation #bfl nw.tmp2 = @s nw.b_fl",
    "scoreboard players operation #bkb nw.tmp2 = @s nw.b_kb",
    "scoreboard players operation #bdmg nw.tmp2 = @s nw.b_st",
    "scoreboard players operation #bdmg nw.tmp2 *= #2 nw.const",
    "scoreboard players add #bdmg nw.tmp2 4",
    # Pfeil im ersten belegten Fach? Ohne Pfeil kein Schuss.
    "scoreboard players set #bpf nw.tmp2 -1",
]
for sl in reversed(BOGI_PFEIL_SLOTS):
    schuss.append(f"execute if items block ~ ~ ~ container.{sl} minecraft:arrow run scoreboard players set #bpf nw.tmp2 {sl}")
schuss += [
    "execute if score #bpf nw.tmp2 matches -1 run return 0",
]
# Ziele je nach Reichweite und Multishot
for rg in range(3):
    for mu in range(3):
        schuss.append(f"execute if score #brg nw.tmp2 matches {rg} if score #bmu nw.tmp2 matches {mu} "
                      f"as @e[tag=nw.welle,distance=..{bogi_reichweite(rg)},sort=nearest,limit={1 + mu}] run function {NS}:bogi/treffer")
schuss += [
    "execute unless score #btreffer nw.tmp2 matches 1.. run return 0",
    "scoreboard players set #btreffer nw.tmp2 0",
    "playsound minecraft:entity.arrow.shoot player @a[distance=..16] ~ ~ ~ 0.7 1.2",
    f"execute as @e[type=item_display,tag=nw.bogi_a,distance=..0.1] run data merge entity @s {{start_interpolation:0,interpolation_duration:2,transformation:{_arm_transform(-25)}}}",
    # Pfeil abziehen, wenn keine Unendlichkeit gekauft ist
    *[f"execute if score @s nw.b_inf matches 0 if score #bpf nw.tmp2 matches {sl} run item modify block ~ ~ ~ container.{sl} {NS}:pfeil_weg" for sl in BOGI_PFEIL_SLOTS],
]
fn("bogi/schuss", schuss)
w(f"{NS}/item_modifier/pfeil_weg.json", {"function": "minecraft:set_count", "count": -1, "add": True})

fn("bogi/treffer", [
    "scoreboard players set #btreffer nw.tmp2 1",
    # der Schuetze dreht sich zum Ziel, die Spur fliegt hin
    "execute facing entity @s eyes run function " + f"{NS}:bogi/zielen",
    "execute store result storage nachtwache:tmp dmg int 1 run scoreboard players get #bdmg nw.tmp2",
    f"function {NS}:bogi/schaden with storage nachtwache:tmp",
    "execute if score #bfl nw.tmp2 matches 1 run data modify entity @s Fire set value 100s",
    "execute if score #bkb nw.tmp2 matches 1.. facing entity @s feet run tp @s ^ ^ ^0.8",
    "execute if score #bkb nw.tmp2 matches 2 facing entity @s feet run tp @s ^ ^ ^0.8",
    "playsound minecraft:entity.arrow.hit_player player @a[distance=..16] ~ ~ ~ 0.5 1.4",
])
fn("bogi/schaden", ["$damage @s $(dmg) minecraft:arrow"])
fn("bogi/zielen", [
    "tp @e[type=item_display,tag=nw.bogi_k,distance=..0.6] ~ ~ ~ ~ 0",
    "tp @e[type=item_display,tag=nw.bogi_a,distance=..0.6] ~ ~ ~ ~ 0",
    "scoreboard players set #spur nw.tmp 16",
    f"execute positioned ~ ~0.7 ~ run function {NS}:bogi/spur",
])
fn("bogi/spur", [
    "particle minecraft:crit ~ ~ ~ 0 0 0 0 1 force",
    "scoreboard players remove #spur nw.tmp 1",
    f"execute if score #spur nw.tmp matches 1.. positioned ^ ^ ^0.5 run function {NS}:bogi/spur",
])

# Knoepfe (rechts nach links), gesperrte Faecher und Kauf
BOGI_SPERRE = ('minecraft:gray_stained_glass_pane[custom_data={nw_bogi_lock:1b},custom_name={text:"Locked",color:"dark_gray",italic:false},'
               'lore=[{text:"Bogi only carries one row",color:"dark_gray",italic:false}]]')
symbol_b = []
for k, name, ikon, maxst, preis, text in BOGI_UPGRADES:
    for n in range(maxst + 1):
        if n < maxst:
            it = (f'{ikon}[custom_data={{nw_bogi_{k}:1b}},custom_name={{text:"{name}",color:"yellow",italic:false}},'
                  f'lore=[{{text:"Now: {text(n)}",color:"gray",italic:false}},'
                  f'[{{text:"Next: {text(n + 1)} for {preis * (n + 1)} ",color:"gold",italic:false}},{{text:"{COIN}",color:"white",italic:false}}],'
                  f'{{text:"Take this to buy",color:"dark_gray",italic:false}}]]')
        else:
            it = (f'{ikon}[enchantment_glint_override=true,custom_data={{nw_bogi_{k}:1b}},custom_name={{text:"{name} (max)",color:"yellow",italic:false}},'
                  f'lore=[{{text:"{text(n)}",color:"gray",italic:false}}]]')
        symbol_b.append(f"execute if score @s nw.b_{k} matches {n} run item replace block ~ ~ ~ container.{BOGI_SLOT[k]} with {it}")
symbol_b += [f"execute if items block ~ ~ ~ container.{sl} *[custom_data~{{nw_bogi_lock:1b}}] run item replace block ~ ~ ~ container.{sl} with minecraft:air" for sl in BOGI_PFEIL_SLOTS]
symbol_b += [f"execute unless items block ~ ~ ~ container.{sl} * run item replace block ~ ~ ~ container.{sl} with {BOGI_SPERRE}" for sl in range(BOGI_LAGER, 27)]
for _n, _nm in enumerate(["Bogi"] + BOGI_NAMEN):
    symbol_b.append(f'execute if score @s nw.b_nm matches {_n} run data merge block ~ ~ ~ '
                    f'{{CustomName:{{text:"{_nm}",color:"green"}}}}')
symbol_b.append('execute unless score @s nw.b_nm matches 0..%d run data merge block ~ ~ ~ {CustomName:{text:"Bogi",color:"green"}}' % len(BOGI_NAMEN))
fn("bogi/symbol", symbol_b)

for k, name, ikon, maxst, preis, text in BOGI_UPGRADES:
    fn(f"bogi/kauf_{k}", [
        f"scoreboard players operation #bs nw.tmp2 = @s nw.b_{k}",
        *[f"execute if score #bs nw.tmp2 matches {n} run scoreboard players set #bp nw.tmp2 {preis * (n + 1)}" for n in range(maxst)],
        f"execute as @a[distance=..8] store result score @s nw.tmp run clear @s *[custom_data~{{nw_bogi_{k}:1b}}] 0",
        f"execute as @a[distance=..8,scores={{nw.tmp=1..}}] run function {NS}:bogi/kauf_{k}_ab",
        f"scoreboard players operation @s nw.b_{k} = #bs nw.tmp2",
        f"execute store result entity @s data.{k} int 1 run scoreboard players get #bs nw.tmp2",
        f"function {NS}:bogi/symbol",
    ])
    fn(f"bogi/kauf_{k}_ab", [
        f"clear @s *[custom_data~{{nw_bogi_{k}:1b}}]",
        f"execute if score #bs nw.tmp2 matches {maxst}.. run return run tellraw @s " + J([txt("[Bogi] ", "green"), txt("That one is already at its best.", "gray")]),
        "execute if score #konto nw.konto < #bp nw.tmp2 run tellraw @s " + J([txt("[Bogi] ", "green"), txt("Not enough coins. ", "gray"), {"score": {"name": "#bp", "objective": "nw.tmp2"}, "color": "gold"}, txt(" needed.", "gray")]),
        "execute if score #konto nw.konto < #bp nw.tmp2 run return run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
        "scoreboard players operation #konto nw.konto -= #bp nw.tmp2",
        "scoreboard players add #bs nw.tmp2 1",
        "playsound minecraft:block.smithing_table.use block @s ~ ~ ~ 0.8 1.2",
        "tellraw @s " + J([txt("[Bogi] ", "green"), txt(f"{name} improved.", "gray")]),
    ])

fn("bogi/kaputt", [
    "kill @e[type=item_display,tag=nw.bogi_k,distance=..0.1]", "kill @e[type=item_display,tag=nw.bogi_a,distance=..0.1]",
    'kill @e[type=item,distance=..2.5,nbt={Item:{id:"minecraft:trapped_chest"}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_bogi_lock:1b}}}}]',
    *[f'kill @e[type=item,distance=..2.5,nbt={{Item:{{components:{{"minecraft:custom_data":{{nw_bogi_{k}:1b}}}}}}}}]' for k, *_ in BOGI_UPGRADES],
    *[f"execute store result storage nachtwache:tmp {k} int 1 run scoreboard players get @s nw.b_{k}" for k, *_ in BOGI_UPGRADES],
    "data modify storage nachtwache:tmp nm set from entity @s data.nm",
    "execute store result score #bnm nw.tmp2 run data get entity @s data.nm",
    f"execute as @p[distance=..10] run function {NS}:bogi/geben",
    "tellraw @p[distance=..10] " + J([txt("[Bogi] ", "green"), txt("Packing up. I am in your inventory.", "gray")]),
    "playsound minecraft:entity.item.pickup player @p[distance=..10] ~ ~ ~ 1 0.8",
    "kill @s",
])

# ----------------------------------------------------------------------------
# Leben: der rote Beacon ist das Herz der Insel. Die Gegner laufen darauf zu (ein unsichtbarer
# Eisengolem darauf zieht sie an), stehen sie fuenf Sekunden ungestoert davor, loesen sie sich auf
# und kosten ein Leben. Ein Treffer bricht das ab. Bei null Leben ist Schluss.
# ----------------------------------------------------------------------------
BX, BY, BZ = BEACON
fn("beacon/aufbauen", [
    f"execute unless block {BX} {BY} {BZ} minecraft:beacon run setblock {BX} {BY} {BZ} minecraft:beacon",
    f"execute unless block {BX} {BY+1} {BZ} minecraft:red_stained_glass run setblock {BX} {BY+1} {BZ} minecraft:red_stained_glass",
    f"fill {BX-1} {BY-1} {BZ-1} {BX+1} {BY-1} {BZ+1} minecraft:iron_block replace #{NS}:beacon_sockel",
    f"kill @e[type=item,x={BX-2},y={BY-2},z={BZ-2},dx=4,dy=4,dz=4,nbt={{Item:{{id:\"minecraft:iron_block\"}}}}]",
    f"kill @e[type=item,x={BX-2},y={BY-2},z={BZ-2},dx=4,dy=4,dz=4,nbt={{Item:{{id:\"minecraft:beacon\"}}}}]",
    # Zielpunkt der Gegner: ein winziger, unverwundbarer Dorfbewohner auf dem Beacon. Zombies suchen Dorfbewohner
    # auch ohne Sichtlinie, deshalb laufen sie zuverlaessig hierher. Unsichtbare Entities werden dagegen ignoriert.
    f"execute unless entity @e[tag=nw.herz] run summon minecraft:villager {BX+0.5} {BY+1.1} {BZ+0.5} "
    f'{{Tags:["nw.herz"],NoAI:1b,Silent:1b,Invulnerable:1b,PersistenceRequired:1b,NoGravity:1b,Offers:{{Recipes:[]}},'
    f'VillagerData:{{profession:"minecraft:nitwit",level:1,type:"minecraft:swamp"}},'
    f'attributes:[{{id:"minecraft:scale",base:0.2d}},{{id:"minecraft:max_health",base:1024d}}],Health:1024f}}',
    # Lebensanzeige ueber dem Beacon
    f"execute unless entity @e[tag=nw.herz_text] run summon minecraft:text_display {BX+0.5} {BY+2.1} {BZ+0.5} "
    f'{{Tags:["nw.herz_text"],billboard:"center",background:0,see_through:false,text:{J([txt(icons.ZEICHEN["heart"] + " ", "red"), {"score": {"name": "#leben", "objective": "nw.leben"}, "color": "red", "bold": True}])}}}',
])
w(f"{NS}/tags/block/beacon_sockel.json", {"values": ["minecraft:air", "minecraft:grass_block", "minecraft:dirt", "minecraft:water", "minecraft:cave_air"]})
fn("beacon/anzeige", [
    f'data modify entity @e[tag=nw.herz_text,limit=1] text set value {J([txt(icons.ZEICHEN["heart"] + " ", "red"), {"score": {"name": "#leben", "objective": "nw.leben"}, "color": "red", "bold": True}])}',
])
fn("beacon/verlust", [
    "scoreboard players remove #leben nw.leben 1",
    f"particle minecraft:dust{{color:[1.0,0.1,0.1],scale:2.0}} {BX+0.5} {BY+1.5} {BZ+0.5} 0.8 1.2 0.8 0 60",
    f"playsound minecraft:entity.wither.hurt hostile @a {BX} {BY} {BZ} 1.4 0.6",
    "tellraw @a " + J([txt("Something reached the beacon. ", "dark_red"), txt("-1 ", "red"), txt(icons.ZEICHEN["heart"], "red")]),
    "title @a actionbar " + J([txt("Lives: ", "red"), {"score": {"name": "#leben", "objective": "nw.leben"}, "color": "white"}]),
    f"function {NS}:beacon/anzeige",
    f"execute if score #leben nw.leben matches ..0 run function {NS}:beacon/ende",
])
fn("beacon/ende", [
    "scoreboard players set #leben nw.leben 0",
    "scoreboard players set #ende nw.status 1",
    "kill @e[tag=nw.welle]", f"function {NS}:gegner/vergessen",
    "scoreboard players set #gegner nw.gegner 0", "scoreboard players set #boss nw.boss 0",
    "bossbar set nw:welle visible false", "bossbar set nw:boss visible false", "bossbar set nw:uhr visible false",
    f"function {NS}:strasse/entfernen", "scoreboard players set #status nw.status 0",
    'title @a times 10 120 20',
    "title @a title " + J([txt("GAME OVER", "dark_red", bold=True)]),
    "title @a subtitle " + J([txt("The beacon is dark.", "gray")]),
    "playsound minecraft:entity.wither.death master @a ~ ~ ~ 1 0.6",
    "tellraw @a " + J([txt("The beacon went out on night ", "dark_red"), {"score": {"name": "#nacht", "objective": "nw.nacht"}, "color": "white"}, txt(".", "dark_red")]),
    "tellraw @a " + J([txt("Enemies killed: ", "gray"), {"score": {"name": "#kills", "objective": "nw.kills"}, "color": "white"},
                       txt("   Coins earned: ", "gray"), {"score": {"name": "#verdient", "objective": "nw.verdient"}, "color": "gold"},
                       txt("   Blocks mined: ", "gray"), {"score": {"name": "#abbau", "objective": "nw.abbau"}, "color": "white"}]),
    "tellraw @a " + J([txt("An admin can start over with ", "gray"), txt("/trigger reset", "yellow"), txt(".", "gray")]),
])

# ----------------------------------------------------------------------------
# Generatoren: der Quell als Gegenstand. Jeder Generator ist ein Marker, ein Fass mit facing=down
# (im Ressourcenpaket unsichtbar) und ein block_display in der Farbe der aktuellen Stufe.
# Rechtsklick oeffnet das Fass und zeigt die Drops der Stufe mit Wahrscheinlichkeit, unten rechts
# liegt der Knopf zum Mitnehmen. Alle Generatoren zaehlen auf denselben Fortschritt ein.
# ----------------------------------------------------------------------------
GEN_PREIS = 20000
GEN_SLOT_TAKE = 26
GEN_ZEIGE = 26                      # so viele Eintraege passen in die Uebersicht
def gen_item(stufe=0):
    """Der Generator als Gegenstand. Muss ein Spawn-Ei sein: nur dort wirkt entity_data, ein Blockitem
    wuerde beim Setzen einfach seinen eigenen Block legen (Fehler bis v0.15, Luis 08.09.2026)."""
    modell = 'item_model="nachtwache:generator",' if RESSOURCENPAKET else ""
    tier = f'[{{text:"Tier {stufe}",color:"light_purple",italic:false}}]' if stufe else '[{text:"Tier follows the Source",color:"light_purple",italic:false}]'
    lore = ('[{text:"Put it down anywhere on your island.",color:"gray",italic:false},'
            '{text:"Mine it for blocks and coins, right-click to see what it gives.",color:"gray",italic:false},'
            '{text:"Every generator counts towards the same tier.",color:"gray",italic:false},'
            f'{tier}]')
    daten = f",tier:{stufe}" if stufe else ""
    return (f'minecraft:zombie_spawn_egg[{modell}custom_name={{text:"Source Generator",color:"light_purple",italic:false}},'
            f'custom_data={{nw_gen:1b{daten}}},'
            f'entity_data={{id:"minecraft:marker",Tags:["nw.gen_neu"]}},lore={lore}]')

GEN_TAKE_KNOPF = ('minecraft:ender_eye[custom_data={nw_gen_take:1b},custom_name={text:"Take the generator",color:"yellow",italic:false},'
                  'lore=[{text:"Take this and it goes back into your inventory",color:"gray",italic:false},'
                  '{text:"Everything it dropped so far stays with you",color:"dark_gray",italic:false}]]')

fn("gen/tick", [
    f"execute as @e[type=marker,tag=nw.gen_neu] at @s run function {NS}:gen/neu",
    f"execute as @e[type=marker,tag=nw.gen] at @s run function {NS}:gen/einer",
])
fn("gen/neu", [
    "tag @s remove nw.gen_neu",
    "execute align xyz positioned ~0.5 ~0.5 ~0.5 run tp @s ~ ~ ~",
    f"execute at @s unless block ~ ~ ~ minecraft:air run return run function {NS}:gen/zurueck",
    "tag @s add nw.gen",
    f"execute at @s run function {NS}:gen/aufbauen",
    "playsound minecraft:block.amethyst_cluster.place block @a ~ ~ ~ 1 0.8",
    "tellraw @a[distance=..12] " + J([txt("A generator hums. Mine it, right-click it to look inside.", "light_purple")]),
])
fn("gen/zurueck", [
    f"execute as @p[distance=..10] run give @s {gen_item()}",
    "tellraw @p[distance=..10] " + J([txt("The generator needs a free block.", "gray", italic=True)]),
    "kill @s",
])
fn("gen/aufbauen", [
    "setblock ~ ~ ~ minecraft:barrel[facing=down]",
    f"function {NS}:gen/farbe",
    f"function {NS}:gen/anzeige",
])
# Das sichtbare Aussehen: ein block_display in der Farbe der Stufe
# Der Generator ist ein sichtbares Fass in Steinoptik. Der kleine Stufenkristall obendrauf ist seit v0.18
# raus (Luis 08.09.2026: stoert optisch und blieb beim Umstellen in der Luft haengen). gen/farbe raeumt nur
# noch alte Displays weg, damit auch Reste aus aelteren Fassungen verschwinden.
fn("gen/farbe", ["kill @e[type=block_display,tag=nw.gen_block,distance=..2.5]"])

# Uebersicht im Fass: die Drops der aktuellen Stufe mit Wahrscheinlichkeit, unten rechts der Mitnehmen-Knopf
def gen_uebersicht_zeilen(p):
    eintraege = []
    for r in rows:                                   # rows = quell.csv
        if p not in phasen_von(r["phasen"]): continue
        eintraege.append((r["item"], int(r["gewicht"]), int(r["min"]), int(r["max"])))
    gesamt = sum(g for _, g, _, _ in eintraege) or 1
    eintraege.sort(key=lambda e: -e[1])
    zeilen, rest = [], 0.0
    for i, (item, g, mn, mx) in enumerate(eintraege):
        pz = 100.0 * g / gesamt
        if i >= GEN_ZEIGE - 1 and len(eintraege) > GEN_ZEIGE:
            rest += pz; continue
        ist_kiste = item.startswith("KISTE_")
        iid = "minecraft:chest" if ist_kiste else f"minecraft:{item}"
        nm = "Crate" if ist_kiste else item.replace("_", " ").title()
        menge = f"{mn}" if mn == mx else f"{mn} to {mx}"
        lore = [f'[{{text:"{pz:.2f} %",color:"gold",italic:false}}]', f'{{text:"{menge} per block",color:"gray",italic:false}}']
        zeilen.append(f'{iid}[custom_data={{nw_gen_show:1b}},custom_name={{text:"{nm}",color:"white",italic:false}},lore=[{",".join(lore)}]]')
    if rest > 0:
        zeilen.append(f'minecraft:paper[custom_data={{nw_gen_show:1b}},custom_name={{text:"... and more",color:"gray",italic:false}},'
                      f'lore=[[{{text:"{rest:.2f} %",color:"gold",italic:false}}],{{text:"rare leftovers",color:"dark_gray",italic:false}}]]')
    return zeilen

anzeige = []
for p in range(1, ANZ_STUFEN + 1):
    zeilen = gen_uebersicht_zeilen(p)
    for slot in range(27):
        if slot == GEN_SLOT_TAKE:
            anzeige.append(f"execute if score #phase nw.phase matches {p} run item replace block ~ ~ ~ container.{slot} with {GEN_TAKE_KNOPF}")
        elif slot < len(zeilen):
            anzeige.append(f"execute if score #phase nw.phase matches {p} run item replace block ~ ~ ~ container.{slot} with {zeilen[slot]}")
        else:
            anzeige.append(f"execute if score #phase nw.phase matches {p} run item replace block ~ ~ ~ container.{slot} with minecraft:air")
# Fenstername je Stufe statt "Barrel"
for p_ in range(1, ANZ_STUFEN + 1):
    anzeige.append(f'execute if score #phase nw.phase matches {p_} run data merge block ~ ~ ~ '
                   f'{{CustomName:[{{text:"Source Generator   ",color:"light_purple"}},{{text:"Tier {p_}",color:"gray"}}]}}')
fn("gen/anzeige", anzeige)

fn("gen/einer", [
    # Block weg? Dann hat ihn jemand abgebaut: Ertrag geben und wieder aufstellen
    f"execute unless block ~ ~ ~ minecraft:barrel run function {NS}:gen/abgebaut",
    # Anzeigegegenstaende gehoeren nicht ins Spielerinventar
    "clear @a[distance=..8] *[custom_data~{nw_gen_show:1b}]",
    f"execute unless items block ~ ~ ~ container.{GEN_SLOT_TAKE} *[custom_data~{{nw_gen_take:1b}}] run function {NS}:gen/mitnehmen",
    f"execute if score #m20 nw.tmp matches 7 run function {NS}:gen/anzeige",
])
gen_abgebaut = [
    'kill @e[type=item,distance=..2.5,nbt={Item:{id:"minecraft:barrel"}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_gen_show:1b}}}}]',
    'kill @e[type=item,distance=..2.5,nbt={Item:{components:{"minecraft:custom_data":{nw_gen_take:1b}}}}]',
    "scoreboard players set #wer nw.tmp 0",
    f"execute as @a[distance=..8,scores={{nw.mined_gen=1..}},limit=1] run function {NS}:quell/abbau",
    "scoreboard players reset @a nw.mined_gen",
    "setblock ~ ~ ~ minecraft:barrel[facing=down]",
    f"function {NS}:gen/anzeige",
]
fn("gen/abgebaut", gen_abgebaut)
fn("gen/mitnehmen", [
    f"clear @a[distance=..8] *[custom_data~{{nw_gen_take:1b}}]",
    "clear @a[distance=..8] *[custom_data~{nw_gen_show:1b}]",
    f"execute if score #phase nw.phase matches 1 as @p[distance=..8] run give @s {gen_item(1)}",
    f"execute if score #phase nw.phase matches 2 as @p[distance=..8] run give @s {gen_item(2)}",
    f"execute if score #phase nw.phase matches 3 as @p[distance=..8] run give @s {gen_item(3)}",
    f"execute if score #phase nw.phase matches 4 as @p[distance=..8] run give @s {gen_item(4)}",
    f"execute if score #phase nw.phase matches 5 as @p[distance=..8] run give @s {gen_item(5)}",
    f"execute if score #phase nw.phase matches 6 as @p[distance=..8] run give @s {gen_item(6)}",
    f"execute if score #phase nw.phase matches 7 as @p[distance=..8] run give @s {gen_item(7)}",
    "kill @e[type=block_display,tag=nw.gen_block,distance=..1.2]",
    "setblock ~ ~ ~ minecraft:air",
    'kill @e[type=item,distance=..2.5,nbt={Item:{id:"minecraft:barrel"}}]',
    "playsound minecraft:entity.item.pickup player @p[distance=..8] ~ ~ ~ 1 0.8",
    "tellraw @p[distance=..8] " + J([txt("The generator is in your inventory.", "light_purple")]),
    "kill @s",
])

# ----------------------------------------------------------------------------
# Source Focus (10 Minuten doppelte Coins) und Decoy Totem (zieht die Gegner auf sich)
# ----------------------------------------------------------------------------
MODELL_FOCUS = 'item_model="nachtwache:focus",' if RESSOURCENPAKET else ""
MODELL_DECOY = 'item_model="nachtwache:decoy",' if RESSOURCENPAKET else ""
FOCUS_TICKS = 12000                     # 10 Minuten
DECOY_HP = 60                           # rund 20 Treffer
LORE_LEBEN_L = ['{text:"Repairs the beacon by one heart.",color:"gray",italic:false}',
                '{text:"Buy before the wave, not during it.",color:"gray",italic:false}']
LORE_FOCUS_L = ['{text:"Right-click: the Source pays double for 10 minutes.",color:"gray",italic:false}',
                '{text:"Burns up when used.",color:"gray",italic:false}']
LORE_DECOY_L = ['{text:"Right-click: puts up a decoy where you stand.",color:"gray",italic:false}',
                '{text:"Enemies go for it instead of you until it breaks.",color:"gray",italic:false}']
KONSUM = 'consumable={consume_seconds:0.6f,animation:"drink",sound:"minecraft:block.amethyst_block.chime",has_consume_particles:false},max_stack_size=16'

w(f"{NS}/advancement/focus_benutzt.json", {"criteria": {"benutzt": {"trigger": "minecraft:consume_item", "conditions": {
    "item": {"predicates": {"minecraft:custom_data": "{nw_focus:1b}"}}}}},
    "rewards": {"function": f"{NS}:focus/start"}})
w(f"{NS}/advancement/decoy_benutzt.json", {"criteria": {"benutzt": {"trigger": "minecraft:consume_item", "conditions": {
    "item": {"predicates": {"minecraft:custom_data": "{nw_decoy:1b}"}}}}},
    "rewards": {"function": f"{NS}:decoy/setzen"}})

fn("focus/start", [
    f"advancement revoke @s only {NS}:focus_benutzt",
    f"scoreboard players set #focus nw.upgrade {FOCUS_TICKS}",
    "tellraw @a " + J([txt("The Source glows. Double coins for ten minutes.", "light_purple")]),
    "playsound minecraft:block.beacon.activate master @a ~ ~ ~ 1 1.4",
    "execute at @a run particle minecraft:witch ~ ~1 ~ 0.6 1 0.6 0.1 30",
])
fn("focus/sekunde", [
    "execute if score #focus nw.upgrade matches 1.. run scoreboard players remove #focus nw.upgrade 20",
    f"execute if score #focus nw.upgrade matches 1.. run particle minecraft:end_rod {QUELL[0]+0.5} {QUELL[1]+1.2} {QUELL[2]+0.5} 0.3 0.2 0.3 0.01 3",
    f"execute if score #focus nw.upgrade matches 0 run function {NS}:focus/ende",
])
fn("focus/ende", [
    "scoreboard players set #focus nw.upgrade -1",
    "tellraw @a " + J([txt("The Source dims again.", "gray", italic=True)]),
])

fn("decoy/setzen", [
    f"advancement revoke @s only {NS}:decoy_benutzt",
    "execute at @s align xyz positioned ~0.5 ~ ~0.5 run function " + f"{NS}:decoy/bauen",
])
fn("decoy/bauen", [
    'summon minecraft:armor_stand ~ ~ ~ {Tags:["nw.decoy_stand"],Invulnerable:1b,NoGravity:1b,NoBasePlate:1b,ShowArms:1b,PersistenceRequired:1b,'
    'CustomName:{"text":"Decoy","color":"gold"},CustomNameVisible:1b,'
    'equipment:{head:{id:"minecraft:carved_pumpkin",count:1},chest:{id:"minecraft:leather_chestplate",count:1,components:{"minecraft:dyed_color":9127187}},'
    'mainhand:{id:"minecraft:stick",count:1}},DisabledSlots:4144959}',
    f'summon minecraft:iron_golem ~ ~ ~ {{Tags:["nw.decoy"],NoAI:1b,Silent:1b,Invisible:1b,PersistenceRequired:1b,NoGravity:1b,'
    f'attributes:[{{id:"minecraft:max_health",base:{DECOY_HP}d}}],Health:{DECOY_HP}f}}',
    "playsound minecraft:block.wood.place block @a ~ ~ ~ 1 0.8",
    "tellraw @a[distance=..20] " + J([txt("A decoy stands. It will hold them for a while.", "gold")]),
])
fn("decoy/sekunde", [
    "execute unless entity @e[tag=nw.decoy] run return 0",
    # Vogelscheuche und Golem gehoeren zusammen: fehlt einer, verschwindet auch der andere
    f"execute as @e[tag=nw.decoy] at @s run function {NS}:decoy/einer",
    "execute as @e[tag=nw.decoy_stand] at @s unless entity @e[tag=nw.decoy,distance=..1.5] run function " + f"{NS}:decoy/zerbricht",
])
fn("decoy/einer", [
    "execute at @s run particle minecraft:smoke ~ ~1.2 ~ 0.2 0.2 0.2 0.01 2",
    "execute unless entity @e[tag=nw.decoy_stand,distance=..1.5] run kill @s",
])
fn("decoy/zerbricht", [
    "playsound minecraft:entity.item.break block @a ~ ~ ~ 1 0.7",
    "particle minecraft:block{block_state:\"minecraft:carved_pumpkin\"} ~ ~1 ~ 0.3 0.6 0.3 0.1 30",
    "tellraw @a[distance=..20] " + J([txt("The decoy is torn apart.", "gray", italic=True)]),
    "kill @s",
])

# ----------------------------------------------------------------------------
# Laden: Kaufen-Truhe (Doppeltruhe, 54 Felder) und Verkaufen-Fass am Tresen. Geld bleibt virtuell (Konto).
# Kaufen: Klick auf ein Symbol = 1 Stueck, Shift-Klick = max (meist 64). Verkaufen: Ware ins Fass legen
# (Shift-Klick aus dem Inventar), wird sofort verkauft. Nur Ware aus preise.csv, nie Werkzeug.
# ----------------------------------------------------------------------------
REITER_SLOTS = 9           # oberste Reihe: Reiter (Starter, Tier 2..7, Books)
PLATZ_PRO_REITER = 45      # fuenf Reihen Ware je Reiter

def kauf_block(slot):
    return (KAUF_A if slot < 27 else KAUF_B), slot % 27

MODELL_GLOCKE = 'item_model="nachtwache:watch_bell",' if RESSOURCENPAKET else ""
MODELL_KIT = 'item_model="nachtwache:kit",' if RESSOURCENPAKET else ""
MODELL_ZWERG = 'item_model="nachtwache:dwarf",' if RESSOURCENPAKET else ""
MODELL_LATERNE = 'item_model="nachtwache:lantern",' if RESSOURCENPAKET else ""
MODELL_KONTRAKT = 'item_model="nachtwache:contract",' if RESSOURCENPAKET else ""
LORE_LATERNE_L = ['{text:"Place it on the road or on your island.",color:"gray",italic:false}', '{text:"Enemies within 8 blocks are slowed.",color:"gray",italic:false}', '{text:"Burns for three nights, then goes out.",color:"gray",italic:false}']
LORE_KONTRAKT_L = ['{text:"Tonight: double bounty, wave 50% bigger.",color:"gray",italic:false}', '{text:"One contract at a time. Signed by daylight only.",color:"gray",italic:false}']
LORE_LATERNE = "[" + ",".join(LORE_LATERNE_L) + "]"
LORE_KONTRAKT = "[" + ",".join(LORE_KONTRAKT_L) + "]"


def item_spec(spec):
    """Angebots-Item -> (id, components-string ohne Klammern oder '', count) fuer das echte Item."""
    if spec in SONDERITEMS:
        iid, cnt, comp = SONDERITEMS[spec]
        return iid, comp[1:-1], cnt
    if spec == "BOGI":
        g = bogi_item()
        return g[:g.index("[")], g[g.index("[") + 1:-1], 1
    if spec == "ZWERG":
        g = zwerg_item(0)
        return g[:g.index("[")], g[g.index("[") + 1:-1], 1
    if spec == "GENERATOR":
        g = gen_item()
        return g[:g.index("[")], g[g.index("[") + 1:-1], 1
    if spec == "LEBEN":
        modell = 'item_model="nachtwache:life",' if RESSOURCENPAKET else ""
        return "minecraft:red_dye", modell + 'custom_name={text:"One more Life",color:"red",italic:false},custom_data={nw_leben:1b},lore=[' + ",".join(LORE_LEBEN_L) + ']', 1
    if spec == "FOCUS":
        return "minecraft:amethyst_shard", MODELL_FOCUS + 'custom_name={text:"Source Focus",color:"light_purple",italic:false},custom_data={nw_focus:1b},' + KONSUM + ',lore=[' + ",".join(LORE_FOCUS_L) + ']', 1
    if spec == "DECOY":
        return "minecraft:carved_pumpkin", MODELL_DECOY + 'custom_name={text:"Decoy Totem",color:"gold",italic:false},custom_data={nw_decoy:1b},' + KONSUM + ',lore=[' + ",".join(LORE_DECOY_L) + ']', 1
    if spec == "LATERNE":
        return "minecraft:soul_lantern", MODELL_LATERNE + 'custom_name={text:"Collector Lantern",color:"aqua",italic:false},custom_data={nw_laterne:1b},lore=' + LORE_LATERNE, 1
    if spec == "KONTRAKT":
        return "minecraft:paper", MODELL_KONTRAKT + 'custom_name={text:"Bounty Contract",color:"red",italic:false},custom_data={nw_kontrakt:1b},lore=' + LORE_KONTRAKT, 1
    if spec == "GLOCKE":
        return "minecraft:bell", MODELL_GLOCKE + 'custom_name={text:"Watch Bell",color:"gold",italic:false},custom_data={nw_glocke:1b},lore=[{text:"Rings when something steps onto the road",color:"gray",italic:false}]', 1
    if spec.startswith("SET:"):
        einzeln = []
        for t in spec[4:].split(";"):
            it, cnt = t.split(":")[0], int(t.split(":")[1])
            if it.endswith("bucket") or cnt > 64:      # nicht stapelbar: ein Feld je Stueck
                einzeln += [(it, 1)] * cnt
            else:
                einzeln.append((it, cnt))
        inhalt = ",".join('{slot:%d,item:{id:"minecraft:%s",count:%d}}' % (i, it, cnt) for i, (it, cnt) in enumerate(einzeln))
        return "minecraft:chest", MODELL_KIT + 'container=[%s],custom_name={text:"Kit",color:"gold",italic:false},lore=[{text:"Place the chest and empty it",color:"gray",italic:false}]' % inhalt, 1
    return f"minecraft:{spec}", "", 1

def menue_item(r):
    """Symbol in der Kaufen-Truhe: das Item selbst, mit Preis in der Beschreibung und Marker in custom_data."""
    iid, comp, _ = item_spec(r["item"])
    preis, mx, name = int(r["preis"]), int(r["max"]), r["name"]
    lore = [f'[{{text:"Price: {preis} ",color:"gold",italic:false}},{{text:"{COIN}",color:"white",italic:false}}]',
            f'{{text:"Click: buy 1",color:"gray",italic:false}}']
    if r["item"] == "LATERNE":
        lore = LORE_LATERNE_L + lore
    if r["item"] == "KONTRAKT":
        lore = LORE_KONTRAKT_L + lore
    if r["item"] == "LEBEN":
        lore = LORE_LEBEN_L + lore
    if r["item"] == "FOCUS":
        lore = LORE_FOCUS_L + lore
    if r["item"] == "DECOY":
        lore = LORE_DECOY_L + lore
    if mx > 1:
        lore.append(f'[{{text:"Shift-click: buy {mx} for {preis * mx} ",color:"gray",italic:false}},{{text:"{COIN}",color:"white",italic:false}}]')
    comps = [f'custom_data={{nw_menu:{int(r["id"])}}}', f'custom_name={{text:"{name}",color:"white",italic:false}}', "lore=[" + ",".join(lore) + "]"]
    if comp and not r["item"].startswith("SET:") and r["item"] not in ("GLOCKE", "LATERNE", "KONTRAKT", "ZWERG", "FOCUS", "DECOY", "BOGI", "LEBEN", "GENERATOR"):
        comps.insert(0, comp)
    elif r["item"] == "GLOCKE" and MODELL_GLOCKE:
        comps.insert(0, MODELL_GLOCKE[:-1])
    elif r["item"] == "LATERNE" and MODELL_LATERNE:
        comps.insert(0, MODELL_LATERNE[:-1])
    elif r["item"] == "ZWERG" and MODELL_ZWERG:
        comps.insert(0, MODELL_ZWERG[:-1])
    elif r["item"] == "BOGI" and RESSOURCENPAKET:
        comps.insert(0, 'item_model="nachtwache:archer"')
    elif r["item"] == "KONTRAKT" and MODELL_KONTRAKT:
        comps.insert(0, MODELL_KONTRAKT[:-1])
    elif r["item"] == "GENERATOR" and RESSOURCENPAKET:
        comps.insert(0, 'item_model="nachtwache:generator"')
    elif r["item"] == "LEBEN" and RESSOURCENPAKET:
        comps.insert(0, 'item_model="nachtwache:life"')
    elif r["item"] == "FOCUS" and MODELL_FOCUS:
        comps.insert(0, MODELL_FOCUS[:-1])
    elif r["item"] == "DECOY" and MODELL_DECOY:
        comps.insert(0, MODELL_DECOY[:-1])
    elif r["item"].startswith("SET:") and MODELL_KIT:
        comps.insert(0, MODELL_KIT[:-1])
    return f"{iid}[{','.join(comps)}]"

# Reiter des Ladens: feste Kategorien, die sich mit jeder Quellstufe weiter fuellen (Luis 07.09.2026)
KATEGORIEN = [
    ("BLOCKS",   "Building Blocks",  "minecraft:stone"),
    ("MINERALS", "Minerals & Drops", "minecraft:iron_ingot"),
    ("MOB",      "Mob Drops",        "minecraft:rotten_flesh"),
    ("FOOD",     "Food & Farming",   "minecraft:bread"),
    ("TOOLS",    "Tools & Redstone", "minecraft:redstone"),
    ("BREW",     "Brewing & Magic",  "minecraft:brewing_stand"),
    ("BOOKS",    "Enchanted Books",  "minecraft:enchanted_book"),
    ("SPECIAL",  "Special",          "minecraft:nether_star"),
]
def reiter_liste(phase):
    """Reiter der Kaufen-Truhe fuer eine Quellstufe: [(idx, slot, name, tab-item, zeilen)].
    Ein Reiter je Kategorie, sichtbar sobald er in dieser Stufe mindestens ein Angebot hat."""
    out = []
    for i, (key, name, icon) in enumerate(KATEGORIEN, 1):
        rows = sorted((r for r in angebot if r["kat"] == key and int(r["stufe"]) <= phase),
                      key=lambda r: (int(r["stufe"]), int(r["id"])))
        if not rows: continue
        out.append((i, len(out), name, icon, rows))
    return out

def reiter_item(idx, name, iid, aktiv):
    glanz = "enchantment_glint_override=true," if aktiv else ""
    hint = "Open" if aktiv else "Click to open"
    return f'{iid}[{glanz}custom_data={{nw_menu:{9000 + idx}}},custom_name={{text:"{name}",color:"yellow",italic:false}},lore=[{{text:"{hint}",color:"gray",italic:false}}]]'

for p in range(1, ANZ_STUFEN + 1):
    reiter = reiter_liste(p)
    for idx, _, _, _, rows in reiter:
        lines = []
        belegt = {}
        for ridx, slot, name, iid, _ in reiter:
            belegt[slot] = reiter_item(ridx, name, iid, ridx == idx)
        for i, r in enumerate(rows[:PLATZ_PRO_REITER]):
            belegt[REITER_SLOTS + i] = menue_item(r)
        for slot in range(54):
            blk, ls = kauf_block(slot)
            lines.append(f"item replace block {blk[0]} {blk[1]} {blk[2]} container.{ls} with {belegt.get(slot, 'minecraft:air')}")
        fn(f"sammler/kaufmenue_{p}_{idx}", lines)

# #seite nw.status = aktiver Reiter (1..7 = Kategorie); leerer Reiter -> erster Reiter
kaufmenue = ["execute unless score #seite nw.status matches 1.. run scoreboard players set #seite nw.status 1"]
for p in range(1, ANZ_STUFEN + 1):
    gueltig = {idx for idx, _, _, _, _ in reiter_liste(p)}
    for idx in range(2, len(KATEGORIEN) + 2):
        if idx not in gueltig:
            kaufmenue.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {idx}{'..' if idx > len(KATEGORIEN) else ''} run scoreboard players set #seite nw.status 1")
    for idx, _, _, _, _ in reiter_liste(p):
        kaufmenue.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {idx} run function {NS}:sammler/kaufmenue_{p}_{idx}")
fn("sammler/kaufmenue", kaufmenue)

# Tresen (Truhen und Fass nur setzen, wenn sie fehlen, sonst waere der Inhalt weg)
fn("sammler/tresen", [
    f"execute unless block {KAUF_A[0]} {KAUF_A[1]} {KAUF_A[2]} minecraft:chest run setblock {KAUF_A[0]} {KAUF_A[1]} {KAUF_A[2]} minecraft:chest[facing=south,type=right]",
    f"execute unless block {KAUF_B[0]} {KAUF_B[1]} {KAUF_B[2]} minecraft:chest run setblock {KAUF_B[0]} {KAUF_B[1]} {KAUF_B[2]} minecraft:chest[facing=south,type=left]",
    f"execute unless block {VERKAUF[0]} {VERKAUF[1]} {VERKAUF[2]} minecraft:barrel run setblock {VERKAUF[0]} {VERKAUF[1]} {VERKAUF[2]} minecraft:barrel[facing=up]",
    f"data merge block {KAUF_A[0]} {KAUF_A[1]} {KAUF_A[2]} {{CustomName:[{{text:\"BUY   \",color:\"dark_red\"}},{{text:\"● \",color:\"white\"}},{{score:{{name:\"#konto\",objective:\"nw.konto\"}},color:\"gold\"}}]}}",
    f"data merge block {KAUF_B[0]} {KAUF_B[1]} {KAUF_B[2]} {{CustomName:[{{text:\"BUY   \",color:\"dark_red\"}},{{text:\"● \",color:\"white\"}},{{score:{{name:\"#konto\",objective:\"nw.konto\"}},color:\"gold\"}}]}}",
    f"data merge block {VERKAUF[0]} {VERKAUF[1]} {VERKAUF[2]} {{CustomName:[{{text:\"SELL   \",color:\"dark_red\"}},{{text:\"put goods here\",color:\"gray\"}}]}}",
])

fn("sammler/erscheinen", [
    "kill @e[tag=nw.villager]", "kill @e[tag=nw.sammler]", "kill @e[tag=nw.kasse]",
    f'summon minecraft:zombie_villager {sx} {sy} {sz} {{Tags:["nw.villager"],NoAI:1b,Silent:1b,Invulnerable:1b,PersistenceRequired:1b,NoGravity:1b,CustomName:{{text:"The Collector",color:"dark_red"}},CustomNameVisible:1b,VillagerData:{{profession:"minecraft:nitwit",level:1,type:"minecraft:swamp"}},Offers:{{Recipes:[]}},IsBaby:0b,Rotation:[0f,0f]}}',
    f'summon minecraft:interaction {sx} {sy} {sz} {{Tags:["nw.sammler"],width:1.6f,height:2.4f}}',
    f"function {NS}:sammler/tresen", f"function {NS}:sammler/kaufmenue",
])

# Klick auf den Sammler selbst: Hinweis
fn("sammler/interaktion", [
    f"execute as @e[tag=nw.sammler] if data entity @s interaction on target run function {NS}:sammler/hinweis",
    f"execute as @e[tag=nw.sammler] if data entity @s interaction run data remove entity @s interaction",
    f"execute as @e[tag=nw.sammler] if data entity @s attack run data remove entity @s attack",
    f"execute if score #glocke nw.upgrade matches 0 if score #m20 nw.tmp matches 7 as @a if items entity @s container.* minecraft:bell[custom_data~{{nw_glocke:1b}}] run function {NS}:sammler/glocke_an",
])
fn("sammler/hinweis", [
    "tellraw @s " + J([txt("[The Collector] ", "dark_red"), txt("The chest on the left: buy. Click for one, shift-click for a stack. The barrel on the right: sell, put goods in, coins go to the account. I do not take tools.", "gray")]),
    f"tellraw @s {J([coin(), txt(' Coins: ', 'gold'), {'score': {'name': '#konto', 'objective': 'nw.konto'}, 'color': 'yellow'}])}",
])
fn("sammler/glocke_an", [
    "scoreboard players set #glocke nw.upgrade 1",
    "tellraw @a " + J([txt("The watch bell is active. It rings when something steps onto the road.", "gold")]),
])

# Kaufen: jeden Tick pruefen, ob ein Symbol (Ware oder Reiter) aus der Truhe genommen wurde
kauf_tick = [f"execute unless entity @a[x={KAUF_A[0]},y={KAUF_A[1]},z={KAUF_A[2]},distance=..8] run return 0"]
for p in range(1, ANZ_STUFEN + 1):
    reiter = reiter_liste(p)
    for idx, _, _, _, rows in reiter:
        for i, r in enumerate(rows[:PLATZ_PRO_REITER]):
            blk, ls = kauf_block(REITER_SLOTS + i)
            kauf_tick.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {idx} unless items block {blk[0]} {blk[1]} {blk[2]} container.{ls} *[custom_data~{{nw_menu:{int(r['id'])}}}] run function {NS}:sammler/kauf/{int(r['id'])}")
        for ridx, slot, _, _, _ in reiter:
            blk, ls = kauf_block(slot)
            kauf_tick.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {idx} unless items block {blk[0]} {blk[1]} {blk[2]} container.{ls} *[custom_data~{{nw_menu:{9000 + ridx}}}] run function {NS}:sammler/reiter/{ridx}")
fn("sammler/kauf_tick", kauf_tick)
for idx in range(1, len(KATEGORIEN) + 1):
    fn(f"sammler/reiter/{idx}", [
        f"clear @a[x={KAUF_A[0]},y={KAUF_A[1]},z={KAUF_A[2]},distance=..8] *[custom_data~{{nw_menu:{9000 + idx}}}]",
        f"scoreboard players set #seite nw.status {idx}",
        f"playsound minecraft:ui.button.click master @a[x={KAUF_A[0]},y={KAUF_A[1]},z={KAUF_A[2]},distance=..8] ~ ~ ~ 0.5 1.4",
        f"function {NS}:sammler/kaufmenue",
    ])

for r in angebot:
    rid, preis, mx, name = int(r["id"]), int(r["preis"]), int(r["max"]), r["name"]
    iid, comp, cnt = item_spec(r["item"])
    give_arg = f"{iid}[{comp}]" if comp else iid
    pred = f"*[custom_data~{{nw_menu:{rid}}}]"
    fn(f"sammler/kauf/{rid}", [
        # Wer hat es? (Cursor oder Inventar)
        f"execute as @a[x={KAUF_A[0]},y={KAUF_A[1]},z={KAUF_A[2]},distance=..8] store result score @s nw.tmp run clear @s {pred} 0",
        f"execute as @a[x={KAUF_A[0]},y={KAUF_A[1]},z={KAUF_A[2]},distance=..8,scores={{nw.tmp=1..}}] run function {NS}:sammler/kauf_abwickeln/{rid}",
        f"function {NS}:sammler/kaufmenue",
    ])
    if r["item"] == "KONTRAKT":
        fn(f"sammler/kauf_abwickeln/{rid}", [
            f"clear @s {pred}",
            f"execute if score #status nw.status matches 1 run tellraw @s {J([txt('[The Collector] ', 'dark_red'), txt('Contracts are signed by daylight. Come back in the morning.', 'gray')])}",
            "execute if score #status nw.status matches 1 run return run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
            f"execute if score #kontrakt nw.upgrade matches 1.. run tellraw @s {J([txt('[The Collector] ', 'dark_red'), txt('One contract at a time. Tonight is already spoken for.', 'gray')])}",
            "execute if score #kontrakt nw.upgrade matches 1.. run return run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
            f"scoreboard players set #preis nw.tmp {preis}",
            f"execute if score #konto nw.konto < #preis nw.tmp run tellraw @s {J([txt('[The Collector] ', 'dark_red'), txt('Not enough coins. ', 'gray'), {'score': {'name': '#preis', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' needed.', 'gray')])}",
            "execute if score #konto nw.konto < #preis nw.tmp run return run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
            "scoreboard players operation #konto nw.konto -= #preis nw.tmp",
            "scoreboard players set #kontrakt nw.upgrade 1",
            "playsound minecraft:item.book.page_turn neutral @a ~ ~ ~ 1 0.8",
            f"tellraw @a {J([txt('[The Collector] ', 'dark_red'), txt('A bounty contract is signed. Tonight: double bounty, and I send more of them. ', 'gold'), star()])}",
            f"function {NS}:uhr/anzeige",
        ])
        continue
    fn(f"sammler/kauf_abwickeln/{rid}", [
        f"scoreboard players set #anz nw.tmp 1",
        f"execute if items entity @s container.* {pred} run scoreboard players set #anz nw.tmp {mx}",   # Shift-Klick: im Inventar statt am Cursor
        f"clear @s {pred}",
        f"scoreboard players set #preis nw.tmp {preis}",
        "scoreboard players operation #preis nw.tmp *= #anz nw.tmp",
        f"execute if score #konto nw.konto < #preis nw.tmp run tellraw @s {J([txt('[The Collector] ', 'dark_red'), txt('Not enough coins. ', 'gray'), {'score': {'name': '#preis', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' needed, ', 'gray'), {'score': {'name': '#konto', 'objective': 'nw.konto'}, 'color': 'gold'}, txt(' on the account.', 'gray')])}",
        "execute if score #konto nw.konto < #preis nw.tmp run playsound minecraft:entity.villager.no neutral @s ~ ~ ~ 1 1",
        "execute if score #konto nw.konto < #preis nw.tmp run return 0",
        "scoreboard players operation #konto nw.konto -= #preis nw.tmp",
        "execute store result storage nachtwache:tmp n int 1 run scoreboard players get #anz nw.tmp",
        *([f"execute if score #leben nw.leben matches {LEBEN_MAX}.. run scoreboard players add #konto nw.konto {preis}",
           f"execute if score #leben nw.leben matches {LEBEN_MAX}.. run return run tellraw @s " + J([txt("[The Collector] ", "dark_red"), txt("The beacon is already whole.", "gray")]),
           "scoreboard players add #leben nw.leben 1",
           f"function {NS}:beacon/anzeige",
           f"particle minecraft:heart {BEACON[0]+0.5} {BEACON[1]+1.6} {BEACON[2]+0.5} 0.4 0.5 0.4 0 12",
           "tellraw @a " + J([txt("The beacon burns brighter. Lives: ", "red"), {"score": {"name": "#leben", "objective": "nw.leben"}, "color": "white"}]),
        ] if r["item"] == "LEBEN" else
        [f'data modify storage nachtwache:tmp item set value "{give_arg}"' if not comp else f"data modify storage nachtwache:tmp item set value '{give_arg}'",
           f"function {NS}:sammler/geben with storage nachtwache:tmp"] if r["item"] != "BOGI" else [
           # Bogis heissen der Reihe nach Tombo, Svenjo, Harzo, Django ...
           "scoreboard players add #bogi_nr nw.status 1",
           f"execute unless score #bogi_nr nw.status matches 1..{len(BOGI_NAMEN)} run scoreboard players set #bogi_nr nw.status 1",
           "scoreboard players operation #bnm nw.tmp2 = #bogi_nr nw.status",
           *[f"data modify storage nachtwache:tmp {k} set value 0" for k, *_ in BOGI_UPGRADES],
           "data modify storage nachtwache:tmp nm set value 0",
           f"function {NS}:bogi/geben",
        ]),
        "playsound minecraft:entity.villager.yes neutral @s ~ ~ ~ 1 0.9",
        f"title @s actionbar {J([txt('Bought: ', 'green'), {'score': {'name': '#anz', 'objective': 'nw.tmp'}, 'color': 'white'}, txt(f' {name}  (-', 'green'), {'score': {'name': '#preis', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' ', 'green'), coin(), txt(')', 'green')])}",
        "execute store result score #r nw.tmp2 run random value 1..4",
        f"execute if score #r nw.tmp2 matches 1 run function {NS}:sammler/spruch/kauf",
    ])
fn("sammler/geben", ["$give @s $(item) $(n)"])

# Verkaufen: Fass am Tresen, alle 5 Ticks (die Lieferrampe ist seit v0.13 raus, Luis: wird nicht benutzt)
# Preis je Gegenstand als eigene Funktion preis/<item>: Fach lesen, Namensraum abschneiden, Funktion mit dem Namen aufrufen.
for r in preise:
    fn(f"preis/{r['item']}", [f"scoreboard players set #w nw.tmp2 {int(r['wert'])}"])
fn("sammler/preis", ["$function nachtwache:preis/$(id)"])
def verkauf_funktionen(name, pos, slots, prozent):
    x, y, z = pos
    lines = [f"execute unless items block {x} {y} {z} container.* * run return 0"]
    for slot in range(slots):
        lines.append(f"execute if items block {x} {y} {z} container.{slot} * run function {NS}:sammler/{name}_slot {{slot:{slot}}}")
    fn(f"sammler/{name}", lines)
    fn(f"sammler/{name}_slot", [
        f"$execute store result score #n nw.tmp run data get block {x} {y} {z} Items[{{Slot:$(slot)b}}].count",
        f"$data modify storage nachtwache:tmp id set string block {x} {y} {z} Items[{{Slot:$(slot)b}}].id 10",
        "scoreboard players set #w nw.tmp2 0",
        f"function {NS}:sammler/preis with storage nachtwache:tmp",
        "execute if score #w nw.tmp2 matches ..0 run return 0",
        "scoreboard players operation #gain nw.tmp = #n nw.tmp", "scoreboard players operation #gain nw.tmp *= #w nw.tmp2",
        f"scoreboard players set #pz nw.tmp2 {prozent}", "scoreboard players operation #gain nw.tmp *= #pz nw.tmp2", "scoreboard players operation #gain nw.tmp /= #100 nw.const",
        "execute if score #gain nw.tmp matches ..0 run return 0",     # zu wenig fuer einen Splitter: liegen lassen, bis mehr da ist
        "scoreboard players operation #konto nw.konto += #gain nw.tmp", "scoreboard players operation #verdient nw.verdient += #gain nw.tmp",
        f"$item replace block {x} {y} {z} container.$(slot) with minecraft:air",
        f"playsound minecraft:entity.villager.trade neutral @a[distance=..12] {x} {y} {z} 0.7 1",
        f"title @a[distance=..12] actionbar {J([txt('Sold: +', 'gold'), {'score': {'name': '#gain', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' ', 'gold'), coin()])}",
    ])
verkauf_funktionen("verkauf", VERKAUF, 27, 100)

# ----------------------------------------------------------------------------
# Uhr
# ----------------------------------------------------------------------------
fn("uhr/tick", [
    "execute if score #ende nw.status matches 1 run return 0",     # nach dem Verlust steht die Zeit
    "execute unless entity @a run return 0",          # Zeit laeuft nur, wenn jemand auf dem Server ist
    "scoreboard players set #tagphase nw.tmp 1",
    f"execute if score #zeit nw.zeit matches {NACHT_START}..{TAG_START - 1} run scoreboard players set #tagphase nw.tmp 0",
    # Akkumulator: je Tick ZAEHLER dazu, je volle NENNER eine Zeiteinheit
    f"execute if score #tagphase nw.tmp matches 1 run scoreboard players add #uhr_akku nw.tmp2 {TAG_ZAEHLER}",
    f"execute if score #tagphase nw.tmp matches 1 run scoreboard players set #uhr_nenner nw.tmp2 {TAG_NENNER}",
    f"execute if score #tagphase nw.tmp matches 0 run scoreboard players add #uhr_akku nw.tmp2 {NACHT_ZAEHLER}",
    f"execute if score #tagphase nw.tmp matches 0 run scoreboard players set #uhr_nenner nw.tmp2 {NACHT_NENNER}",
    "execute unless score #uhr_akku nw.tmp2 >= #uhr_nenner nw.tmp2 run return 0",
    "scoreboard players operation #schritt nw.tmp2 = #uhr_akku nw.tmp2", "scoreboard players operation #schritt nw.tmp2 /= #uhr_nenner nw.tmp2",
    "scoreboard players operation #uhr_akku nw.tmp2 %= #uhr_nenner nw.tmp2",
    # Nacht: ab 23000 bleibt die Uhr stehen, solange noch Gegner leben. Sind alle tot, springt sie auf den Morgen.
    f"execute if score #status nw.status matches 1 if score #gegner nw.gegner matches 0 if score #zeit nw.zeit matches {NACHT_START + 300}.. run function {NS}:nacht/alles_tot",
    "execute if score #status nw.status matches 1 if score #zeit nw.zeit matches 23000.. if score #gegner nw.gegner matches 1.. run return run function nachtwache:nacht/haelt",
    "scoreboard players operation #zeit nw.zeit += #schritt nw.tmp2",
    # nach dem Sieg bleibt es Tag
    f"execute if score #modus nw.status matches 3 if score #zeit nw.zeit matches 12000.. run scoreboard players set #zeit nw.zeit 0",
    "execute if score #zeit nw.zeit matches 24000.. run scoreboard players remove #zeit nw.zeit 24000",
    "execute store result storage nachtwache:tmp t int 1 run scoreboard players get #zeit nw.zeit",
    f"function {NS}:uhr/setzen with storage nachtwache:tmp",
    f"execute if score #status nw.status matches 0 unless score #modus nw.status matches 3 if score #zeit nw.zeit matches {NACHT_START}..{TAG_START - 1} run function {NS}:nacht/start",
    f"execute if score #status nw.status matches 1 unless score #zeit nw.zeit matches {NACHT_START}..{TAG_START - 1} run function {NS}:nacht/ende",
])
fn("uhr/setzen", ["$time set $(t)"])
fn("nacht/alles_tot", [
    f"scoreboard players set #zeit nw.zeit {TAG_START}",
    f"tellraw @a {J([txt('Nothing is left alive. Dawn breaks.', 'green')])}",
])
fn("nacht/haelt", [
    "execute if score #nacht_haelt nw.status matches 1 run return 0",
    "scoreboard players set #nacht_haelt nw.status 1",
    f"tellraw @a {J([txt('The night stays until nothing is left alive.', 'dark_red', italic=True)])}",
    "playsound minecraft:entity.warden.heartbeat hostile @a ~ ~ ~ 1 0.5",
])
# Tages-Uhr als Bossleiste: wie lange noch bis zur Nacht (in echten Minuten)
uhr_name = lambda pad, stern=False: J([txt("Day  ", "green"), txt("night in ", "gray"), {"score": {"name": "#umin", "objective": "nw.tmp2"}, "color": "white"}, txt(":" + ("0" if pad else ""), "white"), {"score": {"name": "#usek", "objective": "nw.tmp2"}, "color": "white"}] + ([txt("  ", "white"), star()] if stern else []))
fn("uhr/anzeige", [
    "execute if score #status nw.status matches 1 run return run bossbar set nw:uhr visible false",
    "execute if score #modus nw.status matches 3 run return run bossbar set nw:uhr visible false",
    f"scoreboard players set #rest nw.tmp2 {NACHT_START}",
    "scoreboard players operation #rest nw.tmp2 -= #zeit nw.zeit",
    "execute if score #rest nw.tmp2 matches ..0 run scoreboard players add #rest nw.tmp2 24000",
    "execute store result bossbar nw:uhr value run scoreboard players get #rest nw.tmp2",
    # echte Sekunden = rest * NENNER / (ZAEHLER * 20)
    "scoreboard players operation #usek nw.tmp2 = #rest nw.tmp2",
    f"scoreboard players set #uhr_n nw.tmp2 {TAG_NENNER}", "scoreboard players operation #usek nw.tmp2 *= #uhr_n nw.tmp2",
    f"scoreboard players set #uhr_z nw.tmp2 {TAG_ZAEHLER * 20}", "scoreboard players operation #usek nw.tmp2 /= #uhr_z nw.tmp2",
    "scoreboard players operation #umin nw.tmp2 = #usek nw.tmp2",
    "scoreboard players set #sechzig nw.tmp2 60",
    "scoreboard players operation #umin nw.tmp2 /= #sechzig nw.tmp2",
    "scoreboard players operation #usek nw.tmp2 %= #sechzig nw.tmp2",
    f"execute if score #usek nw.tmp2 matches 0..9 run bossbar set nw:uhr name {uhr_name(True)}",
    f"execute if score #usek nw.tmp2 matches 10.. run bossbar set nw:uhr name {uhr_name(False)}",
    f"execute if score #kontrakt nw.upgrade matches 1.. if score #usek nw.tmp2 matches 0..9 run bossbar set nw:uhr name {uhr_name(True, True)}",
    f"execute if score #kontrakt nw.upgrade matches 1.. if score #usek nw.tmp2 matches 10.. run bossbar set nw:uhr name {uhr_name(False, True)}",
    "bossbar set nw:uhr color green",
    "execute if score #rest nw.tmp2 matches ..4000 run bossbar set nw:uhr color yellow",
    "execute if score #rest nw.tmp2 matches ..1000 run bossbar set nw:uhr color red",
    "execute if score #rest nw.tmp2 matches 1000..1020 run playsound minecraft:block.bell.use block @a ~ ~ ~ 1 0.6",
    "bossbar set nw:uhr players @a", "bossbar set nw:uhr visible true",
])

# ----------------------------------------------------------------------------
# Naechte
# ----------------------------------------------------------------------------
wellen = read_csv("wellen.csv")
brackets = {}
for r in wellen:
    brackets.setdefault((int(r["von"]), int(r["bis"])), []).append((r["mob"], int(r["gewicht"])))

SPAWN_GEGNER = (0.5, 64, GEGNER_Z - 4.5)   # Spawnpunkt der Wellen: vor dem Seelenfeuer in der Inselmitte, sonst brennen alle (Boss-Bug Nacht 10)
def summon_mob(key, extra_tags=(), pos=SPAWN_GEGNER):
    ent, nbt = MOBS[key]
    tags = '"nw.welle"' + "".join(f',"{t}"' for t in extra_tags)
    return f"summon {ent} {pos[0]} {pos[1]} {pos[2]} {{Tags:[{tags}],{nbt}}}"

typ_dispatch = []
for i, ((a, b), lst) in enumerate(sorted(brackets.items()), 1):
    total = sum(g for _, g in lst)
    lines = [f"execute store result score #r nw.tmp2 run random value 1..{total}"]
    lo = 1
    for mob, g in lst:
        lines.append(f"execute if score #r nw.tmp2 matches {lo}..{lo + g - 1} run " + summon_mob(mob, ["nw.neu"]))
        lo += g
    fn(f"nacht/typ_{i}", lines)
    typ_dispatch.append(f"execute if score #nacht nw.nacht matches {a}..{b} run return run function {NS}:nacht/typ_{i}")
fn("nacht/spawn_einer", typ_dispatch)
fn("nacht/spawn_schleife", [
    "execute if score #anz nw.tmp matches ..0 run return 0",
    f"function {NS}:nacht/spawn_einer",
    "scoreboard players remove #anz nw.tmp 1",
    f"function {NS}:nacht/spawn_schleife",
])

welle = [
    "scoreboard players operation #anz nw.tmp = #nacht nw.nacht",
    f"scoreboard players set #k nw.tmp2 {WELLE_PRO_NACHT}",
    "scoreboard players operation #anz nw.tmp *= #k nw.tmp2",
]
welle.append(f"scoreboard players add #anz nw.tmp {WELLE_BASIS}")
if WELLE_QUADRAT:
    welle += ["scoreboard players operation #q nw.tmp2 = #nacht nw.nacht", "scoreboard players operation #q nw.tmp2 *= #nacht nw.nacht",
              f"scoreboard players operation #q nw.tmp2 /= #{WELLE_QUADRAT} nw.const", "scoreboard players operation #anz nw.tmp += #q nw.tmp2"]
for p, f in PHASEN_FAKTOR.items():
    welle.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #f nw.tmp2 {f}")
welle += [
    "scoreboard players operation #anz nw.tmp *= #f nw.tmp2", "scoreboard players operation #anz nw.tmp /= #10 nw.const",
    f"execute if score #nacht nw.nacht matches {LETZTE_NACHT} unless score #modus nw.status matches 2 run scoreboard players operation #anz nw.tmp *= #2 nw.const",
    "execute if score #kontrakt nw.upgrade matches 1.. run scoreboard players operation #anz nw.tmp *= #3 nw.const",
    "execute if score #kontrakt nw.upgrade matches 1.. run scoreboard players operation #anz nw.tmp /= #2 nw.const",
    "execute if score #kontrakt nw.upgrade matches 1 run scoreboard players set #kontrakt nw.upgrade 2",
    "execute if score #anz nw.tmp matches 151.. run scoreboard players set #anz nw.tmp 150",
    "scoreboard players operation #anz0 nw.tmp = #anz nw.tmp",
    f"function {NS}:nacht/spawn_schleife",
    f"spreadplayers 0 {GEGNER_Z} 2 {GEGNER_RADIUS - 2} false @e[tag=nw.neu]",
    "tag @e[tag=nw.neu] remove nw.neu",
    "execute store result bossbar nw:welle max run scoreboard players get #anz0 nw.tmp",
    "bossbar set nw:welle players @a", "bossbar set nw:welle visible true",
]
fn("nacht/welle", welle)
w(f"{NS}/tags/block/grabbar.json", {"values": [f"#{NS}:weich", f"#{NS}:mittel", f"#{NS}:hart"]})

# Bosse
BOSS_NBT = {
    "zombie_eisen": 'CanBreakDoors:1b,equipment:{head:{id:"minecraft:iron_helmet",count:1},chest:{id:"minecraft:iron_chestplate",count:1},legs:{id:"minecraft:iron_leggings",count:1},mainhand:{id:"minecraft:iron_sword",count:1}},drop_chances:{head:0.0f,chest:0.0f,legs:0.0f,mainhand:0.0f}',
    "spider": '',
    "skeleton": 'equipment:{head:%s,mainhand:{id:"minecraft:bow",count:1,components:{"minecraft:enchantments":{"minecraft:power":5}}}},drop_chances:{head:0.0f,mainhand:0.0f}' % HELM,
    "ravager": '',
    "witch": '',
    "warden": '',
}
BOSS_ENTITY = {"zombie_eisen": "minecraft:zombie", "spider": "minecraft:spider", "skeleton": "minecraft:skeleton", "ravager": "minecraft:ravager", "witch": "minecraft:witch", "warden": "minecraft:warden"}

def boss_summon(key, name, hp, ability):
    extra = BOSS_NBT[key]
    tags = '"nw.welle","nw.boss"' + (f',"nw.boss_{ability}"' if ability else "")
    nbt = (f'Tags:[{tags}],CustomName:{{text:"{name}",color:"dark_purple",bold:true}},CustomNameVisible:1b,PersistenceRequired:1b,Glowing:1b,'
           f'attributes:[{{id:"minecraft:follow_range",base:100d}},{{id:"minecraft:max_health",base:{hp}d}}],Health:{hp}f')
    if extra:
        nbt += "," + extra
    if key == "warden":   # sonst graebt er sich nach dem Auftauchen sofort wieder ein
        nbt += ',Brain:{memories:{"minecraft:dig_cooldown":{value:{},ttl:6000L}}}'
    return f"summon {BOSS_ENTITY[key]} {SPAWN_GEGNER[0]} {SPAWN_GEGNER[1]} {SPAWN_GEGNER[2]} {{{nbt}}}"

for n, (key, name, hp, ability) in BOSSE.items():
    fn(f"nacht/boss_{n}", [
        boss_summon(key, name, hp, ability),
        f'bossbar set nw:boss name {J([txt(name, "dark_purple", bold=True)])}',
        f"bossbar set nw:boss max {hp}", f"bossbar set nw:boss value {hp}", "bossbar set nw:boss players @a", "bossbar set nw:boss visible true",
        "scoreboard players set #boss nw.boss 1",
        f'title @a subtitle {J([txt(f"{name} is on the road.", "dark_purple")])}',
        f'title @a title {J([txt("Night ", "dark_red"), {"score": {"name": "#nacht", "objective": "nw.nacht"}, "color": "dark_red"}])}',
        "playsound minecraft:entity.ender_dragon.growl hostile @a ~ ~ ~ 0.7 0.5",
        f"function {NS}:nacht/warden_wut",
    ])
boss_random = ["execute store result score #r nw.tmp2 run random value 1..5"]
for i, n in enumerate([5, 10, 15, 20, 25], 1):
    boss_random.append(f"execute if score #r nw.tmp2 matches {i} run function {NS}:nacht/boss_{n}")
fn("nacht/boss_zufall", boss_random)

nacht_start = [
    "scoreboard players set #status nw.status 1",
    "bossbar set nw:uhr visible false", "scoreboard players set #nacht_haelt nw.status 0",
    "scoreboard players add #nacht nw.nacht 1",
    f"function {NS}:strasse/bauen",
    "effect give @a minecraft:darkness 3 0 true",
    "playsound minecraft:entity.wither.spawn hostile @a ~ ~ ~ 0.5 0.5",
    "playsound minecraft:block.bell.use block @a ~ ~ ~ 1 0.5",
    f'title @a times 10 60 20',
    f'title @a title {J([txt("Night ", "dark_red"), {"score": {"name": "#nacht", "objective": "nw.nacht"}, "color": "dark_red"}])}',
    f'title @a subtitle {J([txt("The road is growing.", "gray")])}',
    f"execute if score #nacht nw.nacht matches {LETZTE_NACHT} unless score #modus nw.status matches 2 run function {NS}:nacht/finale_start",
    f"function {NS}:nacht/welle",
]
for n in BOSSE:
    nacht_start.append(f"execute if score #nacht nw.nacht matches {n} unless score #modus nw.status matches 2 run function {NS}:nacht/boss_{n}")
nacht_start += [
    # Endlosmodus: alle fuenf Naechte ein zufaelliger Boss
    "scoreboard players operation #m5 nw.tmp2 = #nacht nw.nacht", "scoreboard players operation #m5 nw.tmp2 %= #5 nw.const",
    f"execute if score #modus nw.status matches 2 if score #m5 nw.tmp2 matches 0 run function {NS}:nacht/boss_zufall",
    f"execute unless score #nacht nw.nacht matches {LETZTE_NACHT} run function {NS}:sammler/spruch/nacht",
    "scoreboard players set #glocke_geklingelt nw.upgrade 0",
]
fn("nacht/start", nacht_start)

fn("nacht/finale_start", [
    "scoreboard players set #finale nw.status 1",
    f"function {NS}:sammler/spruch/finale",
    "kill @e[tag=nw.villager]", "kill @e[tag=nw.sammler]",
    f'title @a subtitle {J([txt("The last night. The stall is empty.", "dark_purple")])}',
])

fn("nacht/ende", [
    "scoreboard players set #status nw.status 0",
    f"function {NS}:strasse/entfernen",
    "execute as @a[scores={nw.schlaf=1..}] run tp @s ~ ~ ~",
    "effect give @e[tag=nw.welle] minecraft:glowing infinite 0 true",
    # Ueberlebende auf der Gegnerinsel zur Strassenmuendung
    f"execute as @e[tag=nw.welle,x=-30,y=0,z={GEGNER_Z - GEGNER_RADIUS - 1},dx=60,dy=200,dz=40] run tp @s {STRASSENMUND[0]} {STRASSENMUND[1]} {STRASSENMUND[2]}",
    f"execute if score #gegner nw.gegner matches 0 unless score #stumm nw.status matches 1 run function {NS}:nacht/bonus",
    f"execute if score #gegner nw.gegner matches 1.. run tellraw @a {J([txt('Dawn breaks. ', 'gray'), {'score': {'name': '#gegner', 'objective': 'nw.gegner'}, 'color': 'red'}, txt(' enemies are still alive. They glow, and they are coming.', 'gray')])}",
    f"execute if score #gegner nw.gegner matches 1.. run playsound minecraft:entity.zombie.ambient hostile @a ~ ~ ~ 1 0.5",
    f"function {NS}:sammler/spruch/morgen",
    f"execute if score #kontrakt nw.upgrade matches 2 run tellraw @a {J([txt('[The Collector] ', 'dark_red'), txt('The contract is fulfilled. Pleasure doing business.', 'gray')])}",
    "execute if score #kontrakt nw.upgrade matches 2 run scoreboard players set #kontrakt nw.upgrade 0",
    "scoreboard players add @e[type=marker,tag=nw.laterne] nw.laterne 1",
    f"execute as @e[type=marker,tag=nw.laterne,scores={{nw.laterne=3..}}] at @s run function {NS}:laterne/erloschen",
])
fn("nacht/bonus", [
    "scoreboard players operation #b nw.tmp = #nacht nw.nacht", f"scoreboard players operation #b nw.tmp *= #{BONUS_PRO_NACHT} nw.const",
    "scoreboard players operation #konto nw.konto += #b nw.tmp", "scoreboard players operation #verdient nw.verdient += #b nw.tmp",
    f"tellraw @a {J([txt('The whole wave is dead. Bonus: ', 'green'), {'score': {'name': '#b', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' ', 'green'), coin()])}",
    f"execute if score #nacht nw.nacht matches 10.. run loot give @a loot {NS}:belohnung",
    f"execute if score #nacht nw.nacht matches 10.. run tellraw @a {J([txt('Something extra is in your inventory. From the Collector. Supposedly.', 'gray', italic=True)])}",
    "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1",
])
fn("nacht/schlafen", [
    f"scoreboard players set #zeit nw.zeit {TAG_START}",
    f"tellraw @a {J([txt('You sleep. The night passes.', 'gray', italic=True)])}",
])

# Boss-Tick, Finale, Sieg, Endlos
w(f"{NS}/loot_table/bossbeute.json", {"pools": [{"rolls": 1, "entries": [
    {"type": "minecraft:item", "name": "minecraft:saddle", "weight": 3},
    {"type": "minecraft:item", "name": "minecraft:netherite_ingot", "weight": 3},
    {"type": "minecraft:item", "name": "minecraft:enchanted_book", "weight": 4, "functions": [{"function": "minecraft:enchant_with_levels", "levels": 30}]},
    {"type": "minecraft:item", "name": "minecraft:totem_of_undying", "weight": 2},
    {"type": "minecraft:item", "name": "minecraft:golden_apple", "weight": 3, "functions": [{"function": "minecraft:set_count", "count": {"min": 2, "max": 4}}]},
    {"type": "minecraft:item", "name": "minecraft:diamond", "weight": 4, "functions": [{"function": "minecraft:set_count", "count": {"min": 3, "max": 5}}]},
]}]})
fn("nacht/boss_tick", [
    "execute unless score #boss nw.boss matches 1 run return 0",
    "execute store result bossbar nw:boss value run data get entity @e[tag=nw.boss,limit=1] Health",
    f"execute unless entity @e[tag=nw.boss] run return run function {NS}:nacht/boss_tot",
    "scoreboard players operation #m200 nw.tmp2 = #tick nw.tick", "scoreboard players operation #m200 nw.tmp2 %= #200 nw.const",
    "execute unless score #m200 nw.tmp2 matches 0 run return 0",
    "execute store result score #cs nw.tmp2 if entity @e[type=cave_spider,tag=nw.welle]",
    f"execute if score #cs nw.tmp2 matches ..7 as @e[tag=nw.boss_mutter] at @s run " + summon_mob("cave_spider", pos=("~", "~", "~")),
    f"execute if score #cs nw.tmp2 matches ..6 as @e[tag=nw.boss_mutter] at @s run " + summon_mob("cave_spider", pos=("~", "~", "~")),
    f"execute as @e[tag=nw.boss_hexe] at @s run " + summon_mob("zombie", pos=("~", "~", "~")),
    f"execute as @e[tag=nw.boss_hexe] at @s run " + summon_mob("zombie", pos=("~", "~", "~")),
    f"function {NS}:nacht/warden_wut",
])
# Der Sammler (Warden) bleibt wuetend auf den naechsten Spieler und graebt sich nicht ein
fn("nacht/warden_wut", [
    "execute unless entity @e[tag=nw.boss_finale] run return 0",
    'execute as @e[tag=nw.boss_finale] run data modify entity @s Brain.memories."minecraft:dig_cooldown" set value {value:{},ttl:6000L}',
    "execute as @e[tag=nw.boss_finale] run data modify entity @s anger set value {suspects:[{uuid:[I;0,0,0,0],anger:150}]}",
    "execute as @e[tag=nw.boss_finale] at @s if entity @p run data modify entity @s anger.suspects[0].uuid set from entity @p UUID",
])
fn("nacht/boss_tot", [
    "scoreboard players set #boss nw.boss 0", "bossbar set nw:boss visible false",
    f"scoreboard players set #d nw.tmp {KOPFGELD_BOSS}", "execute if score #kontrakt nw.upgrade matches 2 run scoreboard players operation #d nw.tmp *= #2 nw.const",
    "scoreboard players operation #konto nw.konto += #d nw.tmp", "scoreboard players operation #verdient nw.verdient += #d nw.tmp",
    f"execute if score #finale nw.status matches 1 run return run function {NS}:nacht/sieg",
    f"tellraw @a {J([txt('The boss is dead. ', 'dark_purple'), txt(f'+{KOPFGELD_BOSS} ', 'gray'), coin(), txt(' and something from his pocket.', 'gray')])}",
    f"loot give @a loot {NS}:bossbeute",
    "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 0.8",
])
fn("nacht/sieg", [
    "scoreboard players set #modus nw.status 3", "scoreboard players set #finale nw.status 0", "scoreboard players set #status nw.status 0",
    "kill @e[tag=nw.welle]", f"function {NS}:strasse/entfernen", "bossbar set nw:welle visible false",
    "scoreboard players set #zeit nw.zeit 1000", "time set 1000", "weather clear 1000000",
    "title @a times 20 100 40", f'title @a title {J([txt("DAWN BREAKS", "gold", bold=True)])}', f'title @a subtitle {J([txt("Night 30 is over. The Collector is dead.", "gray")])}',
    "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1", "playsound minecraft:entity.ender_dragon.death master @a ~ ~ ~ 0.5 1.2",
    f"tellraw @a {J([txt('--- NIGHTWATCH: STATS ---', 'gold', bold=True)])}",
    f"tellraw @a {J([txt('Nights: ', 'gray'), {'score': {'name': '#nacht', 'objective': 'nw.nacht'}, 'color': 'white'}, txt('   Deaths: ', 'gray'), {'score': {'name': '#tode', 'objective': 'nw.tode'}, 'color': 'white'}, txt('   Blocks mined at the Source: ', 'gray'), {'score': {'name': '#abbau', 'objective': 'nw.abbau'}, 'color': 'white'}])}",
    f"tellraw @a {J([txt('Enemies killed: ', 'gray'), {'score': {'name': '#kills', 'objective': 'nw.kills'}, 'color': 'white'}, txt('   Coins earned: ', 'gray'), {'score': {'name': '#verdient', 'objective': 'nw.verdient'}, 'color': 'gold'}])}",
    f"tellraw @a {J([txt('Keep playing without nights, or ', 'gray'), txt('[start endless mode]', 'yellow', click_event={'action': 'run_command', 'command': 'trigger nw.endlos'}), txt(' (waves keep growing, a boss every five nights).', 'gray')])}",
    f"function {NS}:sammler/erscheinen", f"function {NS}:sammler/spruch/sieg",
    "scoreboard players enable @a nw.endlos",
])
fn("nacht/endlos_an", [
    "scoreboard players reset @s nw.endlos", "scoreboard players enable @s nw.endlos",
    "execute unless score #modus nw.status matches 3 run return 0",
    "scoreboard players set #modus nw.status 2", "weather thunder 1000000",
    f"tellraw @a {J([txt('Endless mode. The nights are back.', 'dark_red')])}",
])

# ----------------------------------------------------------------------------
# Gegner: Zaehlung, Kopfgeld, Durchbruch
# ----------------------------------------------------------------------------
gt = [
    "execute store result score #gegner nw.gegner if entity @e[tag=nw.welle]",
    "execute store result bossbar nw:welle value run scoreboard players get #gegner nw.gegner",
    "execute unless score #gegner nw.gegner = #gegner_prev nw.gegner run " + f"bossbar set nw:welle name {J([txt('Night ', 'red'), {'score': {'name': '#nacht', 'objective': 'nw.nacht'}, 'color': 'red'}, txt(':  ', 'red'), {'score': {'name': '#gegner', 'objective': 'nw.gegner'}, 'color': 'white'}, txt(' enemies', 'red')])}",
    "execute unless score #gegner nw.gegner = #gegner_prev nw.gegner if score #kontrakt nw.upgrade matches 2 run " + f"bossbar set nw:welle name {J([txt('Night ', 'red'), {'score': {'name': '#nacht', 'objective': 'nw.nacht'}, 'color': 'red'}, txt(':  ', 'red'), {'score': {'name': '#gegner', 'objective': 'nw.gegner'}, 'color': 'white'}, txt(' enemies  ', 'red'), star()])}",
    "execute if score #gegner nw.gegner matches 0 if score #status nw.status matches 0 run bossbar set nw:welle visible false",
    "scoreboard players operation #gegner_prev nw.gegner = #gegner nw.gegner",
    "execute if score #m20 nw.tmp matches 3 if score #status nw.status matches 1 run bossbar set nw:welle players @a",
]
for t, kg in KOPFGELD.items():
    gt += [
        f"execute store result score #c_{t} nw.tmp2 if entity @e[tag=nw.welle,type=minecraft:{t},tag=!nw.boss]",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players operation #d nw.tmp = #p_{t} nw.tmp2",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players operation #d nw.tmp -= #c_{t} nw.tmp2",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players operation #kills nw.kills += #d nw.tmp",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players set #kg nw.tmp {kg}",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players operation #d nw.tmp *= #kg nw.tmp",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 if score #kontrakt nw.upgrade matches 2 run scoreboard players operation #d nw.tmp *= #2 nw.const",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players operation #konto nw.konto += #d nw.tmp",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run scoreboard players operation #verdient nw.verdient += #d nw.tmp",
        f"execute if score #c_{t} nw.tmp2 < #p_{t} nw.tmp2 run title @a actionbar {J([txt('Bounty +', 'gold'), {'score': {'name': '#d', 'objective': 'nw.tmp'}, 'color': 'gold'}])}",
        f"scoreboard players operation #p_{t} nw.tmp2 = #c_{t} nw.tmp2",
    ]
gt += [
    f"execute as @e[tag=nw.welle] at @s run function {NS}:gegner/einer",
    # Waechterglocke
    f"execute if score #glocke nw.upgrade matches 1 if score #glocke_geklingelt nw.upgrade matches 0 if entity @e[tag=nw.welle,x=-4,y=55,z={STRASSE_Z[0]},dx=8,dy=20,dz=25] run function {NS}:gegner/glocke",
]
fn("gegner/tick", gt)
# Nach einem Admin-Kill kein Kopfgeld: Vorzaehler auf null
fn("gegner/durchbruch", [
    "execute at @s run particle minecraft:soul ~ ~1 ~ 0.3 0.5 0.3 0.05 30",
    "execute at @s run playsound minecraft:entity.evoker.cast_spell hostile @a ~ ~ ~ 1 0.5",
    "kill @s",
    f"function {NS}:gegner/vergessen",
    f"function {NS}:beacon/verlust",
])
fn("gegner/vergessen", [f"scoreboard players set #p_{t} nw.tmp2 0" for t in KOPFGELD])
# Endermen sind von Haus aus neutral: jede Sekunde auf den naechsten Spieler wuetend machen
fn("gegner/enderman_wut", [        # 1.21.11: angry_at (UUID) und anger_end_time (Spielzeit, absolut)
    "execute unless entity @e[type=enderman,tag=nw.welle] run return 0",
    "execute store result score #t nw.tmp2 run time query gametime",
    "scoreboard players add #t nw.tmp2 600",
    "execute as @e[type=enderman,tag=nw.welle] at @s if entity @p run data modify entity @s angry_at set from entity @p UUID",
    "execute as @e[type=enderman,tag=nw.welle] store result entity @s anger_end_time long 1 run scoreboard players get #t nw.tmp2",
])
fn("gegner/glocke", [
    "scoreboard players set #glocke_geklingelt nw.upgrade 1",
    "playsound minecraft:block.bell.use block @a ~ ~ ~ 2 0.7", "playsound minecraft:block.bell.resonate block @a ~ ~ ~ 2 0.7",
    f"tellraw @a {J([txt('The watch bell rings. Something is on the road.', 'red')])}",
])
fn("gegner/einer", [
    # Am Beacon: fuenf Sekunden ungestoert, dann loest sich der Gegner auf und kostet ein Leben
    "execute store result score @s nw.hpv run data get entity @s Health",
    "execute if score @s nw.hpv < @s nw.hpp run scoreboard players set @s nw.chan 0",
    "scoreboard players operation @s nw.hpp = @s nw.hpv",
    f"execute unless entity @s[x={BEACON[0]+0.5},y={BEACON[1]+0.5},z={BEACON[2]+0.5},distance=..{DURCHBRUCH_RADIUS}] run scoreboard players set @s nw.chan 0",
    f"execute if entity @s[x={BEACON[0]+0.5},y={BEACON[1]+0.5},z={BEACON[2]+0.5},distance=..{DURCHBRUCH_RADIUS}] run scoreboard players add @s nw.chan 1",
    "execute if score @s nw.chan matches 1.. if score #m20 nw.tmp matches 0 at @s run particle minecraft:dust{color:[1.0,0.2,0.2],scale:1.0} ~ ~1 ~ 0.3 0.5 0.3 0 6",
    f"execute if score @s nw.chan matches {DURCHBRUCH_TICKS}.. run return run function {NS}:gegner/durchbruch",
    "execute store result score @s nw.px run data get entity @s Pos[0]",
    "execute store result score @s nw.py run data get entity @s Pos[1]",
    "execute store result score @s nw.pz run data get entity @s Pos[2]",
    # in den Nebel gefallen: zurueck an den Inselrand, kein Kopfgeld
    f"execute if score @s nw.py matches ..{BODEN_Y - 8} run return run function {NS}:gegner/festgefahren",
    "scoreboard players add @s nw.still 1",
    "execute unless score @s nw.px = @s nw.qx run scoreboard players set @s nw.still 0",
    "execute unless score @s nw.py = @s nw.qy run scoreboard players set @s nw.still 0",
    "execute unless score @s nw.pz = @s nw.qz run scoreboard players set @s nw.still 0",
    "scoreboard players operation @s nw.qx = @s nw.px", "scoreboard players operation @s nw.qy = @s nw.py", "scoreboard players operation @s nw.qz = @s nw.pz",
    # Kommt der Gegner dem naechsten Spieler laenger nicht naeher (egal ob er dabei herumlaeuft), taucht er neben ihm auf
    f"execute if score @s nw.still matches {EINGEBAUT_TICKS}.. if entity @a run function {NS}:gegner/eingebaut",
    f"execute if score @s nw.still matches {STILL_TICKS}.. if entity @a run function {NS}:gegner/blockiert",
    f"execute if score #m20 nw.tmp matches 3 run function {NS}:gegner/fokus",
])
# Zielwahl (Luis 08.09.2026): Gegner wollen IMMER zum Beacon, egal wie weit weg sie sind. Nur wenn ein
# Spieler naeher ist als der Beacon, gehen sie auf den Spieler. Vanilla gibt dem Spielerziel immer Vorrang,
# also wird die Sichtweite auf die Beacon-Entfernung gedrueckt: der Anker liegt dann drin, weiter entfernte
# Spieler draussen. Untergrenze FOKUS_MIN, sonst findet der Wegfinder keinen Weg mehr und der Gegner steht.
FOKUS_STUFEN = [4, 6, 8, 11, 14, 18, 23, 29, 36, 45, 56, 70, 88, 110, 128]
FOKUS_WEIT = 128
_bp = f"x={BEACON[0]+0.5},y={BEACON[1]+0.5},z={BEACON[2]+0.5}"
_ziel = "@a[distance=..%d,gamemode=!spectator,gamemode=!creative]"
fokus = ["scoreboard players set #bk nw.tmp2 0"]
fokus += [f"execute if entity @s[{_bp},distance=..{r}] run scoreboard players set #bk nw.tmp2 {r}" for r in reversed(FOKUS_STUFEN)]
for r in FOKUS_STUFEN:
    fokus.append(f"execute if score #bk nw.tmp2 matches {r} unless entity {_ziel % (r + 1)} run attribute @s minecraft:follow_range base set {r + 1}")
    fokus.append(f"execute if score #bk nw.tmp2 matches {r} if entity {_ziel % (r + 1)} run attribute @s minecraft:follow_range base set {FOKUS_WEIT}")
# Weiter weg als die groesste Stufe: volle Sichtweite, damit sie den Beacon trotzdem kennen und loslaufen
fokus.append(f"execute if score #bk nw.tmp2 matches 0 run attribute @s minecraft:follow_range base set {FOKUS_WEIT}")
fn("gegner/fokus", fokus)
# Komplett eingebaut: lange still und der Block Richtung Spieler ist weder Luft noch grabbar (Obsidian, Portalrahmen, Grundgestein)
fn("gegner/eingebaut", [
    f"execute facing entity @p feet rotated ~ 0 positioned ^ ^ ^1 unless block ~ ~ ~ minecraft:air unless block ~ ~ ~ #{NS}:grabbar run function {NS}:gegner/festgefahren",
])
fn("gegner/blockiert", [
    f"execute facing entity @p feet rotated ~ 0 positioned ^ ^ ^1 run function {NS}:gegner/graben",
])
fn("gegner/graben", [
    "scoreboard players set #klasse nw.tmp 0",
    f"execute if block ~ ~ ~ #{NS}:weich run scoreboard players set #klasse nw.tmp 1",
    f"execute if block ~ ~1 ~ #{NS}:weich run scoreboard players set #klasse nw.tmp 1",
    f"execute if block ~ ~ ~ #{NS}:mittel run scoreboard players set #klasse nw.tmp 2",
    f"execute if block ~ ~1 ~ #{NS}:mittel run scoreboard players set #klasse nw.tmp 2",
    f"execute if block ~ ~ ~ #{NS}:hart run scoreboard players set #klasse nw.tmp 3",
    f"execute if block ~ ~1 ~ #{NS}:hart run scoreboard players set #klasse nw.tmp 3",
    # nichts zu graben: Luecke vor den Fuessen? dann ein Hopser
    f"execute if score #klasse nw.tmp matches 0 if block ~ ~ ~ minecraft:air if block ~ ~-1 ~ minecraft:air unless entity @a[distance=..2] run tp @s ^ ^0.6 ^0.4",
    "execute if score #klasse nw.tmp matches 0 run return 0",
    f"execute if score #klasse nw.tmp matches 1 unless score @s nw.still matches {STILL_TICKS + GRAB_WEICH}.. run return run function {NS}:gegner/klopfen",
    f"execute if score #klasse nw.tmp matches 2 unless score @s nw.still matches {STILL_TICKS + GRAB_MITTEL}.. run return run function {NS}:gegner/klopfen",
    f"execute if score #klasse nw.tmp matches 3 unless score @s nw.still matches {STILL_TICKS + GRAB_HART}.. run return run function {NS}:gegner/klopfen",
    f"execute if block ~ ~ ~ #{NS}:grabbar run setblock ~ ~ ~ minecraft:air destroy",
    f"execute if block ~ ~1 ~ #{NS}:grabbar run setblock ~ ~1 ~ minecraft:air destroy",
    "playsound minecraft:block.stone.break hostile @a ~ ~ ~ 1 0.5",
    "playsound minecraft:entity.zombie.break_wooden_door hostile @a ~ ~ ~ 0.6 0.6",
    f"scoreboard players set @s nw.still {STILL_TICKS - 20}",
])
fn("gegner/klopfen", [
    "execute if score #m20 nw.tmp matches 0 run playsound minecraft:entity.zombie.attack_wooden_door hostile @a ~ ~ ~ 1 0.7",
])
# Festgefahren oder in den Nebel gefallen: der Gegner taucht 10 bis 16 Bloecke vor dem naechsten Spieler wieder auf
# (in dessen Blickrichtung, auf festem Boden). Ist dort nichts, seitlich oder hinter ihm, zuletzt am Strassenmund.
AM_MUND = f"x={STRASSENMUND[0]},y={STRASSENMUND[1]},z={STRASSENMUND[2]},distance=..1.5"
fn("gegner/zum_spieler", [
    f"execute at @p rotated ~ 0 positioned ^ ^ ^13 run spreadplayers ~ ~ 0 3 under 320 false @s",
    *[f"execute if entity @s[{AM_MUND}] at @p rotated ~{w} 0 positioned ^ ^ ^13 run spreadplayers ~ ~ 0 3 under 320 false @s" for w in (45, -45, 90, -90, 135, -135, 180)],
    # Insel zu klein fuer 10 Bloecke Abstand und der Spieler steht am Strassenmund: hinter ihn, so weit weg wie es geht
    f"execute if entity @s[{AM_MUND}] at @s if entity @p[distance=..8] at @p rotated ~180 0 positioned ^ ^ ^5 run spreadplayers ~ ~ 0 2 under 320 false @s",
    "execute at @s run particle minecraft:portal ~ ~1 ~ 0.5 1 0.5 0.5 40",
])

# ----------------------------------------------------------------------------
# Schutz, Spieler, Atmosphaere, Admin
# ----------------------------------------------------------------------------
fn("schutz/tick", [
    # Gegnerinsel und Strasse: jeden Tick zuruecksetzen, nichts darf abgebaut oder gebaut werden
    "scoreboard players operation #m2 nw.tmp2 = #tick nw.tick", "scoreboard players operation #m2 nw.tmp2 %= #2 nw.const",
    f"execute if score #m2 nw.tmp2 matches 0 run function {NS}:welt/gegnerinsel",
    f"function {NS}:welt/stand",
    f"execute if score #m2 nw.tmp2 matches 1 if score #status nw.status matches 1 run function {NS}:strasse/bauen",
    f"execute if score #m2 nw.tmp2 matches 1 if score #status nw.status matches 0 run function {NS}:strasse/entfernen",
    f"kill @e[type=item,x={-GEGNER_RADIUS-2},y={BODEN_Y-8},z={GEGNER_Z-GEGNER_RADIUS-1},dx={2*GEGNER_RADIUS+4},dy=25,dz={2*GEGNER_RADIUS+2}]",
    f"kill @e[type=item,x=-4,y={BODEN_Y-1},z={STRASSE_Z[0]},dx=8,dy=6,dz={STRASSE_Z[1]-STRASSE_Z[0]}]",
])
fn("schutz/sekunde", [
    *[f"tag @a[name={n}] add nw.admin" for n in ADMINS],
    "scoreboard players enable @a[tag=nw.admin] reset", "scoreboard players enable @a[tag=nw.admin] yes", "scoreboard players enable @a[tag=nw.admin] night", "scoreboard players enable @a[tag=nw.admin] boss", "scoreboard players enable @a[tag=nw.admin] fraggle", "scoreboard players enable @a[tag=nw.admin] endnight", "scoreboard players enable @a[tag=nw.admin] money",
    f"function {NS}:laterne/sekunde",
    f"function {NS}:focus/sekunde",
    f"function {NS}:beacon/aufbauen",
    f"function {NS}:beacon/anzeige",
    f"function {NS}:decoy/sekunde",
    "kill @e[type=block_display,tag=nw.gen_block]",
    f"function {NS}:gegner/enderman_wut",
    # Sammler fehlt laenger als 5 s (nicht nur beim Start, wenn die Entities noch nicht geladen sind)? Dann neu.
    "execute if entity @e[tag=nw.villager] run scoreboard players set #fehlt nw.tmp2 0",
    "execute unless entity @e[tag=nw.villager] run scoreboard players add #fehlt nw.tmp2 1",
    f"execute unless score #finale nw.status matches 1 if score #fehlt nw.tmp2 matches 5.. run function {NS}:sammler/erscheinen",
    # Doppelte (durch spaet geladene Entities) wegraeumen
    f"execute if score #migrieren nw.status matches 1 if score #tick nw.tick matches 100.. run function {NS}:migration",
    'kill @e[tag=nw.villager,name=!"The Collector"]',   # alte Fassungen (anderer Name) weg, Nachschub kommt nach 5 s
    "execute store result score #cv nw.tmp2 if entity @e[tag=nw.villager]",
    "execute if score #cv nw.tmp2 matches 2.. run kill @e[tag=nw.villager,limit=1,sort=arbitrary]",
    "execute store result score #ci nw.tmp2 if entity @e[tag=nw.sammler]",
    "execute if score #ci nw.tmp2 matches 2.. run kill @e[tag=nw.sammler,limit=1,sort=arbitrary]",
    "execute if score #tick nw.tick matches 6000.. run scoreboard players operation #m6000 nw.tmp2 = #tick nw.tick",
    "scoreboard players operation #m6000 nw.tmp2 %= #6000 nw.const",
    "execute if score #m6000 nw.tmp2 matches 0..19 unless score #modus nw.status matches 3 run weather thunder 1000000",
    "scoreboard players enable @a nw.kauf", "scoreboard players enable @a nw.hilfe",
])
fn("spieler/tod", [
    "scoreboard players reset @s nw.tode",
    "scoreboard players add #tode nw.tode 1",
    "scoreboard players operation #abzug nw.tmp = #konto nw.konto", f"scoreboard players operation #abzug nw.tmp /= #{100 // TOD_ABZUG_PROZENT} nw.const",
    "scoreboard players operation #konto nw.konto -= #abzug nw.tmp",
    f"tellraw @a {J([{'selector': '@s', 'color': 'red'}, txt(' died. ', 'gray'), txt('-', 'gold'), {'score': {'name': '#abzug', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' ', 'gold'), coin()])}",
    f"spawnpoint @s {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    f"function {NS}:sammler/spruch/tod",
])
fn("spieler/bett", [
    "execute as @a store result score @s nw.schlaf run data get entity @s SleepTimer",
    f"execute if score #gegner nw.gegner matches 1.. as @a[scores={{nw.schlaf=1..}}] run function {NS}:spieler/aufwecken",
    f"execute if score #gegner nw.gegner matches 0 if score #status nw.status matches 1 if entity @a unless entity @a[scores={{nw.schlaf=..0}}] run function {NS}:nacht/schlafen",
])
fn("spieler/aufwecken", [
    "tp @s ~ ~ ~",
    f"tellraw @s {J([txt('Not while something is alive.', 'red', italic=True)])}",
])
fn("atmo/sekunde", [
    "execute store result score #r nw.tmp2 run random value 1..45",
    "execute if score #r nw.tmp2 matches 1 as @a at @s run playsound minecraft:ambient.cave ambient @s ~ ~ ~ 1 0.5",
    "execute if score #r nw.tmp2 matches 2 if score #nacht nw.nacht matches 8.. as @a at @s run playsound minecraft:entity.warden.heartbeat hostile @s ~ ~ ~ 0.7 0.6",
    "execute if score #r nw.tmp2 matches 3 if score #nacht nw.nacht matches 16.. as @a at @s run playsound minecraft:entity.warden.nearby_closer hostile @s ~ ~ ~ 0.5 0.7",
    "execute if score #r nw.tmp2 matches 4 if score #status nw.status matches 1 as @a at @s run playsound minecraft:ambient.basalt_deltas.mood ambient @s ~ ~ ~ 1 0.5",
    "execute if score #r nw.tmp2 matches 5 if score #nacht nw.nacht matches 20.. as @a at @s run effect give @s minecraft:darkness 2 0 true",
])
fn("admin/neustart", [
    "kill @e[tag=nw.welle]", "kill @e[tag=nw.villager]", "kill @e[tag=nw.sammler]",
    f"function {NS}:strasse/entfernen",
    "scoreboard players set #init nw.status 0", "bossbar set nw:welle visible false", "bossbar set nw:boss visible false",
    f"function {NS}:init",
    "tellraw @a " + J([txt("[Nightwatch] Restart. All values reset, islands rebuilt (your own builds stay).", "yellow")]),
])
# Kompletter Neuanfang (nur Op): Welt im Spielbereich leer, Spieler leer, dann normaler Neustart. Zwei Schritte, damit nichts aus Versehen passiert.
RESET_X, RESET_Z = (-48, 47), (-48, 127)
RESET_Y = (0, 160)
fn("admin/reset_trigger", ["scoreboard players set @s reset 0", "scoreboard players enable @s reset", f"function {NS}:admin/reset"])
fn("admin/yes_trigger", ["scoreboard players set @s yes 0", "scoreboard players enable @s yes", f"function {NS}:admin/reset_ja"])
fn("admin/reset", [
    "scoreboard players operation #reset_frist nw.status = #tick nw.tick", "scoreboard players add #reset_frist nw.status 1200",
    "tellraw @a " + J([txt("[Nightwatch] FULL RESET requested: every block in the play area, all inventories, coins, night, tier. ", "red"), txt("Type ", "gray"), txt("/trigger yes", "yellow"), txt(" within 60 seconds to confirm.", "gray")]),
])
reset_ja = [
    "execute unless score #reset_frist nw.status >= #tick nw.tick run return run tellraw @a " + J([txt("[Nightwatch] No reset pending. Type /trigger reset first.", "yellow")]),
    "scoreboard players set #reset_frist nw.status 0",
    "tellraw @a " + J([txt("[Nightwatch] Resetting the world. This takes a moment.", "red")]),
    "gamemode survival @a", "clear @a", "experience set @a 0 points", "experience set @a 0 levels", "effect clear @a",
    "kill @e[type=item]", "kill @e[type=!player]",
    f"tp @a {SPAWN[0]} {SPAWN[1] + 2} {SPAWN[2]}", f"spawnpoint @a {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    f"forceload add {RESET_X[0]} {RESET_Z[0]} {RESET_X[1]} {RESET_Z[1]}",
]
reset_ja += [f"item replace entity @a enderchest.{i} with minecraft:air" for i in range(27)]
reset_ja += [f"fill {RESET_X[0]} {y} {RESET_Z[0]} {RESET_X[1]} {y} {RESET_Z[1]} minecraft:air" for y in range(RESET_Y[0], RESET_Y[1] + 1)]
reset_ja += [
    "kill @e[type=!player]",
    f"forceload remove {RESET_X[0]} {RESET_Z[0]} {RESET_X[1]} {RESET_Z[1]}",
    "scoreboard players reset * nw.tode", "scoreboard players reset * nw.schlaf",
    f"function {NS}:admin/neustart",
    "tellraw @a " + J([txt("[Nightwatch] Fresh start. Day 1, tier 1, empty pockets. Nether and End are untouched.", "yellow")]),
]
fn("admin/reset_ja", reset_ja)
# /trigger night set N: laufende Welle weg, Nacht N startet sofort (Uhr auf Nachtbeginn, nacht/start zaehlt hoch)
fn("admin/night_trigger", [
    "scoreboard players operation #n nw.tmp = @s night", "scoreboard players set @s night 0", "scoreboard players enable @s night",
    f"execute unless score #n nw.tmp matches 1..{LETZTE_NACHT} run return run tellraw @s " + J([txt(f"[Nightwatch] /trigger night set <1..{LETZTE_NACHT}>", "yellow")]),
    "kill @e[tag=nw.welle]", f"function {NS}:gegner/vergessen", "scoreboard players set #gegner nw.gegner 0", "scoreboard players set #boss nw.boss 0", "bossbar set nw:boss visible false",
    "scoreboard players set #status nw.status 0", "scoreboard players set #nacht_haelt nw.status 0",
    "scoreboard players operation #nacht nw.nacht = #n nw.tmp", "scoreboard players remove #nacht nw.nacht 1",
    f"scoreboard players set #zeit nw.zeit {NACHT_START}",
    "tellraw @a " + J([txt("[Nightwatch] Night ", "yellow"), {"score": {"name": "#n", "objective": "nw.tmp"}, "color": "yellow"}, txt(" starts now.", "yellow")]),
])
# /trigger fraggle set <Grad>: Blickrichtungs-Versatz aller Zwerge (1 = 0 Grad, sonst 90/180/270), Zwerge neu zeichnen
fn("admin/fraggle_trigger", [
    "scoreboard players operation #zoff nw.status = @s fraggle", "scoreboard players set @s fraggle 0", "scoreboard players enable @s fraggle",
    "execute if score #zoff nw.status matches 1 run scoreboard players set #zoff nw.status 0",
    f"scoreboard players set #zoff nw.status {ZWERG_YAW_VERSATZ}",
    # Fraggles Rucksack ist jetzt eine Doppeltruhe: bestehende Zwerge einmal neu aufbauen, der alte Inhalt faellt heraus
    f"execute as @e[type=marker,tag=nw.zwerg] at @s run function {NS}:zwerg/migrieren",
    f"function {NS}:zwerg/altlast",
    # Starttruhe und Brunnen aus aelteren Fassungen abraeumen (Luis 07.09.2026), nur die eigenen Bloecke
    f"execute if block {TRUHE[0]} {TRUHE[1]} {TRUHE[2]} minecraft:chest run setblock {TRUHE[0]} {TRUHE[1]} {TRUHE[2]} minecraft:air destroy",
    "fill -1 64 4 1 64 6 minecraft:air replace minecraft:cobblestone_wall",
    "fill -1 65 4 1 65 6 minecraft:air replace minecraft:oak_fence",
    "setblock 0 66 5 minecraft:air",
    "fill -1 63 4 1 63 6 minecraft:grass_block replace minecraft:cobblestone",
    "fill -1 63 4 1 63 6 minecraft:grass_block replace minecraft:water",
    "tellraw @s " + J([txt("[Nightwatch] Fraggle turned by ", "yellow"), {"score": {"name": "#zoff", "objective": "nw.status"}, "color": "yellow"}, txt(" degrees (all dwarves redrawn).", "yellow")]),
])
# /trigger endnight: alle Gegner weg, Nacht sofort beendet (ohne Bonus)
fn("admin/endnight_trigger", [
    "scoreboard players set @s endnight 0", "scoreboard players enable @s endnight",
    "kill @e[tag=nw.welle]", f"function {NS}:gegner/vergessen", "scoreboard players set #gegner nw.gegner 0", "scoreboard players set #boss nw.boss 0", "bossbar set nw:boss visible false",
    f"scoreboard players set #zeit nw.zeit {TAG_START}",
    "scoreboard players set #stumm nw.status 1",
    f"execute if score #status nw.status matches 1 run function {NS}:nacht/ende",
    "scoreboard players set #stumm nw.status 0",
    "tellraw @a " + J([txt("[Nightwatch] Night ended by an admin.", "yellow")]),
])
# /trigger money set N: N Coins aufs Konto (negativ zieht ab)
fn("admin/money_trigger", [
    "scoreboard players operation #n nw.tmp = @s money", "scoreboard players set @s money 0", "scoreboard players enable @s money",
    "scoreboard players operation #konto nw.konto += #n nw.tmp",
    "execute if score #konto nw.konto matches ..-1 run scoreboard players set #konto nw.konto 0",
    "tellraw @a " + J([txt("[Nightwatch] Account changed by ", "yellow"), {"score": {"name": "#n", "objective": "nw.tmp"}, "color": "gold"}, txt(" ", "yellow"), coin(), txt(" (admin).", "yellow")]),
])
# /trigger boss set N: nur den Boss der Nacht N rufen (alter Boss weg)
boss_trigger = [
    "scoreboard players operation #n nw.tmp = @s boss", "scoreboard players set @s boss 0", "scoreboard players enable @s boss",
    "kill @e[tag=nw.boss]", "scoreboard players set #boss nw.boss 0",
]
for n in BOSSE:
    boss_trigger.append(f"execute if score #n nw.tmp matches {n} run return run function {NS}:nacht/boss_{n}")
boss_trigger.append("tellraw @s " + J([txt("[Nightwatch] /trigger boss set <" + "|".join(str(n) for n in BOSSE) + ">", "yellow")]))
fn("admin/boss_trigger", boss_trigger)
fn("admin/zeit_nacht", [f"scoreboard players set #zeit nw.zeit {NACHT_START - 50}", "tellraw @a " + J([txt("[Nightwatch] Night is coming.", "yellow")])])
fn("admin/zeit_tag", [f"scoreboard players set #zeit nw.zeit {TAG_START - 50}", "tellraw @a " + J([txt("[Nightwatch] Day is coming.", "yellow")])])
fn("admin/welle_toeten", ["kill @e[tag=nw.welle]", f"function {NS}:gegner/vergessen", "tellraw @a " + J([txt("[Nightwatch] Wave removed.", "yellow")])])
fn("admin/splitter", ["$scoreboard players add #konto nw.konto $(n)", "tellraw @a " + J([txt("[Nightwatch] Coins credited.", "yellow")])])
# Admin-Phasenwechsel: Abbauzaehler auf den Anfang der Stufe heben, sonst zeigt die Anzeige Minus-Prozent
admin_phase = ["$function nachtwache:quell/phase_wechsel {phase:$(p)}"]
for i, g in enumerate(PHASEN_GRENZEN):
    admin_phase.append(f"execute if score #phase nw.phase matches {i + 2} if score #abbau nw.abbau matches ..{g - 1} run scoreboard players set #abbau nw.abbau {g}")
admin_phase.append(f"function {NS}:anzeige/aktualisieren")
fn("admin/phase", admin_phase)

# ----------------------------------------------------------------------------
# Schreiben
# ----------------------------------------------------------------------------
if OUT.exists():
    shutil.rmtree(OUT)
for path, content in files.items():
    if path.startswith("../"):
        target = OUT / path[3:]
    else:
        target = OUT / "data" / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
zpath = OUT.parent / "nachtwache.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, fs in os.walk(OUT):
        for f in fs:
            full = Path(root) / f
            z.write(full, full.relative_to(OUT))
print(f"{len(files)} Dateien -> {OUT}  und  {zpath}")
try:
    import rp_build
    rp_build.build(OUT.parent)
except ImportError as e:
    print("Ressourcenpaket nicht gebaut (Pillow fehlt?):", e)
