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
PACK_VERSION = 10                       # hochzaehlen, wenn Stand/Sammler sich aendern (Migration beim Laden)
PACK_MIN, PACK_MAX = 94, 110          # 1.21.11 = 94, spaetere Versionen bis 110 zugelassen

QUELL = (0, 64, 0)                     # der One Block
# Sieben Stufen des Quells: (Block, Farbe, Abbauten bis zur naechsten Stufe, Splitter je Abbau, Mob-Chance, Mob)
# Alle Bloecke brauchen eine Spitzhacke, um schnell zu gehen (Haerte 1.5 bis 1.8), Drops werden weggeraeumt.
STUFEN = [
    ("minecraft:tuff",             "Grau",    500,  1, 0.02, "zombie"),
    ("minecraft:green_concrete",   "Gruen",   1000, 2, 0.025, "zombie"),
    ("minecraft:blue_concrete",    "Blau",    1500, 3, 0.03, "skeleton"),
    ("minecraft:budding_amethyst", "Lila",    2000, 4, 0.035, "creeper"),
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
MOB_CHANCE = {i + 1: st[4] for i, st in enumerate(STUFEN)}
MOB_AUS_QUELL = {i + 1: st[5] for i, st in enumerate(STUFEN)}

INSEL_RADIUS = 7                       # Startinsel
GEGNER_Z = 72                          # Mittelpunkt Gegnerinsel (x = 0)
GEGNER_RADIUS = 11
STRASSE_Z = (9, 59)                    # von .. bis (z), Breite 3 (x -1..1). Davor und dahinter feste Stege der Inseln
STRASSENMUND = (2.5, 64, 6.5)          # wohin festhaengende oder gefallene Gegner gesetzt werden (Inselrand)
BODEN_Y = 63                           # Oberkante Boden, gelaufen wird auf 64

SAMMLER_POS = (0.5, 64, -6.5)
RAMPE = (3, 64, -6)                    # Trichter der Lieferrampe
SPAWN = (0, 64, 3)
TRUHE = (2, 64, 2)

TAG_TEILER = 4                         # Uhr: am Tag alle 4 Ticks +5  (Tag dauert 8 Minuten)
NACHT_TEILER = 7                       # Uhr: nachts alle 7 Ticks +5 (Nacht laeuft bis 23000 in ca. 12 Minuten und bleibt dann stehen, bis alle Gegner tot sind)
UHR_SCHRITT = 5
NACHT_START, TAG_START = 13000, 23500  # Uhrzeiten fuer Strasse auf / Strasse weg

WELLE_BASIS, WELLE_PRO_NACHT = 1, 1    # Groesse = (1 + 1*Nacht) * Phasenfaktor, Nacht 1 = 2
PHASEN_FAKTOR = {1: 10, 2: 12, 3: 14, 4: 17, 5: 20, 6: 23, 7: 26}   # in Zehnteln
LETZTE_NACHT = 30
BONUS_PRO_NACHT = 16                    # Splitter fuer eine komplett getoetete Welle (mal Nacht)
KOPFGELD = {"zombie": 6, "husk": 6, "skeleton": 9, "spider": 9, "cave_spider": 6, "creeper": 15,
            "witch": 18, "wither_skeleton": 18, "pillager": 15, "ravager": 45, "warden": 0}
KOPFGELD_BOSS = 150
TOD_ABZUG_PROZENT = 10

STILL_TICKS = 80                       # Stillstand, bis ein Gegner anfaengt zu graben (4 s)
GRAB_WEICH, GRAB_MITTEL, GRAB_HART = 40, 100, 200   # zusaetzliche Ticks je Materialklasse
FEST_TICKS = 400                       # 20 s ohne Annaeherung an den naechsten Spieler: der Gegner taucht neben ihm auf

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
for _n, _l in [("SHARPNESS", 3), ("PROTECTION", 3), ("MENDING", 1), ("UNBREAKING", 3), ("POWER", 3), ("INFINITY", 1), ("FLAME", 1), ("EFFICIENCY", 3), ("LOOTING", 3)]:
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
for p, c in MOB_CHANCE.items():
    w(f"{NS}/predicate/quell_mob_{p}.json", {"condition": "minecraft:random_chance", "chance": c})

OBJEKTIVE = [(f"nw.mined{i+1}", "minecraft.mined:" + st[0].replace("minecraft:", "minecraft.")) for i, st in enumerate(STUFEN)] + [
    ("nw.konto", "dummy"), ("nw.abbau", "dummy"), ("nw.phase", "dummy"), ("nw.nacht", "dummy"), ("nw.gegner", "dummy"),
    ("nw.tmp", "dummy"), ("nw.tmp2", "dummy"), ("nw.zeit", "dummy"), ("nw.tick", "dummy"), ("nw.status", "dummy"),
    ("nw.kauf", "trigger"), ("nw.endlos", "trigger"), ("nw.hilfe", "trigger"),
    ("nw.tode", "deathCount"),
    ("nw.px", "dummy"), ("nw.py", "dummy"), ("nw.pz", "dummy"), ("nw.qx", "dummy"), ("nw.qy", "dummy"), ("nw.qz", "dummy"),
    ("nw.still", "dummy"), ("nw.kills", "dummy"), ("nw.verdient", "dummy"), ("nw.anzeige", "dummy"), ("nw.const", "dummy"),
    ("nw.boss", "dummy"), ("nw.upgrade", "dummy"), ("nw.laterne", "dummy"), ("nw.schlaf", "dummy"), ("nw.fest", "dummy"), ("nw.dmin", "dummy"),
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
for k in [-1, 2, 3, 4, 5, 7, 10, 16, 20, 100, 200, 1000, 6000]:
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
    f"function {NS}:sammler/kaufmenue",
    f"clear @a minecraft:echo_shard[custom_data~{{nw_splitter:1b}}]", f"clear @a minecraft:prismarine_crystals[custom_data~{{nw_buendel:1b}}]",
    "kill @e[type=item,x=-6,y=60,z=-10,dx=12,dy=10,dz=8]",
    "tellraw @a " + J([txt("[Nightwatch] Stall and Collector updated to the current version.", "yellow")]),
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
    "scoreboard players set #verdient nw.verdient 0", "scoreboard players set #tode nw.tode 0", "scoreboard players set #glocke nw.upgrade 0", "scoreboard players set #kontrakt nw.upgrade 0", "kill @e[type=marker,tag=nw.laterne]",
    "scoreboard players set #boss nw.boss 0",
    f"forceload add -20 -20 20 100",
    f"function {NS}:welt/startinsel", f"function {NS}:welt/stand", f"function {NS}:welt/gegnerinsel",
    f"function {NS}:quell/setzen",
    f"setblock {RAMPE[0]} {RAMPE[1]} {RAMPE[2]} minecraft:hopper[facing=down]",
    f"function {NS}:sammler/erscheinen",
    f"spawnpoint @a {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    f"setworldspawn {SPAWN[0]} {SPAWN[1]} {SPAWN[2]}",
    "scoreboard players set #init nw.status 1", f"scoreboard players set #version nw.status {PACK_VERSION}",
    f"function {NS}:anzeige/aktualisieren",
    f"tellraw @a {J([txt('[Nightwatch] ', 'dark_red'), txt('The world is built. The Source stands in the middle, the Collector waits at his stall.', 'gray')])}",
]
fn("init", init)

# Startinsel
R = INSEL_RADIUS
start = []
start += kreis_fills(0, 0, R, BODEN_Y, BODEN_Y, "minecraft:grass_block")
start += kreis_fills(0, 0, R, BODEN_Y - 3, BODEN_Y - 1, "minecraft:dirt")
start += kreis_fills(0, 0, R - 1, BODEN_Y - 6, BODEN_Y - 4, "minecraft:deepslate")
start += kreis_fills(0, 0, R - 3, BODEN_Y - 8, BODEN_Y - 7, "minecraft:deepslate")
start += kreis_fills(0, 0, R - 5, BODEN_Y - 9, BODEN_Y - 9, "minecraft:deepslate")
# Steg zur Strasse (Teil der Insel, luecken- und gelaenderlos)
start += [
    f"fill -1 {BODEN_Y} 6 1 {BODEN_Y} 8 minecraft:polished_deepslate", f"fill -1 {BODEN_Y+1} 6 1 {BODEN_Y+2} 8 minecraft:air",
    # verkohlter Baum
    "fill -4 64 -1 -4 68 -1 minecraft:stripped_dark_oak_log",
    "setblock -4 69 -1 minecraft:stripped_dark_oak_log", "setblock -5 68 -1 minecraft:stripped_dark_oak_log[axis=x]",
    "setblock -3 67 -1 minecraft:stripped_dark_oak_log[axis=x]", "setblock -3 67 0 minecraft:stripped_dark_oak_log[axis=z]",
    "setblock -4 70 -1 minecraft:dark_oak_leaves[persistent=true]",
    # Brunnen (Respawn)
    "fill -1 63 4 1 63 6 minecraft:cobblestone", "setblock 0 63 5 minecraft:water",
    "fill -1 64 4 1 64 6 minecraft:cobblestone_wall", "setblock 0 64 5 minecraft:air",
    "setblock 0 66 5 minecraft:oak_slab", "setblock -1 65 4 minecraft:oak_fence", "setblock 1 65 6 minecraft:oak_fence",
    # Lichter
    "setblock 5 64 3 minecraft:soul_lantern", "setblock -5 64 4 minecraft:soul_lantern", "setblock 3 64 -6 minecraft:air",
    # Starttruhe
    f'setblock {TRUHE[0]} {TRUHE[1]} {TRUHE[2]} minecraft:chest[facing=west]{{Items:[{{Slot:0b,id:"minecraft:water_bucket",count:1}},{{Slot:1b,id:"minecraft:lava_bucket",count:1}},{{Slot:2b,id:"minecraft:oak_sapling",count:1}},{{Slot:3b,id:"minecraft:bone_meal",count:4}},{{Slot:4b,id:"minecraft:bread",count:4}},{{Slot:5b,id:"minecraft:torch",count:8}},{{Slot:6b,id:"minecraft:wooden_pickaxe",count:1}}]}}',
]
fn("welt/startinsel", start)

# Stand des Sammlers (Booth): x -2..2, z -8..-4
stand = [
    "fill -2 63 -8 2 63 -4 minecraft:polished_deepslate",
    "fill -2 64 -8 2 66 -8 minecraft:deepslate_bricks",                 # Rueckwand
    "fill -2 64 -7 -2 66 -5 minecraft:deepslate_bricks", "fill 2 64 -7 2 66 -5 minecraft:deepslate_bricks",  # Seiten
    "fill -1 64 -7 1 66 -6 minecraft:air", "fill -1 65 -5 1 66 -5 minecraft:air",   # innen frei, Tresen (Truhe, Fass) bleibt
    "fill -2 67 -8 2 67 -4 minecraft:crimson_slab[type=bottom]",         # Dach
    "fill -1 67 -4 1 67 -4 minecraft:crimson_stairs[facing=south,half=top]",
    "setblock -2 67 -4 minecraft:crimson_planks", "setblock 2 67 -4 minecraft:crimson_planks",   # volle Bloecke, damit die Laternen haengen koennen
    "setblock -2 66 -4 minecraft:soul_lantern[hanging=true]", "setblock 2 66 -4 minecraft:soul_lantern[hanging=true]",
    "setblock -1 66 -8 minecraft:redstone_torch[lit=true]", "setblock 1 66 -8 minecraft:redstone_torch[lit=true]",
    'setblock 0 66 -7 minecraft:crimson_wall_sign[facing=south]{front_text:{messages:["",{text:"THE",color:"dark_red"},{text:"COLLECTOR",color:"dark_red"},""]}}',
    "setblock 0 64 -8 minecraft:barrel[facing=up]", "setblock -1 64 -7 minecraft:candle[candles=3,lit=true]",
    # Lieferrampe: Rahmen um den Trichter (der Trichter selbst wird nur ersetzt, wenn er fehlt)
    f"setblock {RAMPE[0]} {RAMPE[1]+1} {RAMPE[2]} minecraft:air",
    f"setblock {RAMPE[0]+1} {RAMPE[1]} {RAMPE[2]} minecraft:crimson_planks", f"setblock {RAMPE[0]+1} {RAMPE[1]+1} {RAMPE[2]} minecraft:soul_lantern",
    f'setblock {RAMPE[0]+1} {RAMPE[1]} {RAMPE[2]+1} minecraft:crimson_wall_sign[facing=south]{{front_text:{{messages:["",{{text:"Drop-off",color:"dark_red"}},{{text:"sells at 80%",color:"gray"}},""]}}}}',
    f"execute unless block {RAMPE[0]} {RAMPE[1]} {RAMPE[2]} minecraft:hopper run setblock {RAMPE[0]} {RAMPE[1]} {RAMPE[2]} minecraft:hopper[facing=down]",
    f"setblock {RAMPE[0]} {RAMPE[1]-1} {RAMPE[2]} minecraft:deepslate_bricks",
]
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
    f"function {NS}:quell/pruefen",
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
    f"execute if score #m20 nw.tmp matches 0 run function {NS}:sammler/rampe",
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
pruefen = []
for i, st in enumerate(STUFEN):
    pruefen.append(f"execute if score #phase nw.phase matches {i+1} if block {qx} {qy} {qz} {st[0]} run return 0")
pruefen.append("scoreboard players set #wer nw.tmp 0")
for i, st in enumerate(STUFEN):
    pruefen.append(f"execute if score #wer nw.tmp matches 0 as @a[scores={{nw.mined{i+1}=1..}},limit=1] run function {NS}:quell/abbau")
for i, st in enumerate(STUFEN):
    pruefen.append(f"scoreboard players reset @a nw.mined{i+1}")
pruefen.append(f"function {NS}:quell/setzen")
for st in STUFEN:
    pruefen.append(f"kill @e[type=item,x={qx-1},y={qy-1},z={qz-1},dx=2,dy=2,dz=2,nbt={{Item:{{id:\"{st[0]}\"}}}}]")
fn("quell/pruefen", pruefen)
fn("quell/setzen", [f"execute if score #phase nw.phase matches {i+1} run setblock {qx} {qy} {qz} {st[0]}" for i, st in enumerate(STUFEN)])

abbau = [
    "scoreboard players set #wer nw.tmp 1",
    "scoreboard players add #abbau nw.abbau 1",
    "scoreboard players operation #splitter nw.tmp = #phase nw.phase",
]
for p, s in SPLITTER_PRO_ABBAU.items():
    abbau.append(f"execute if score #phase nw.phase matches {p} run scoreboard players set #splitter nw.tmp {s}")
abbau += [
    "scoreboard players operation #konto nw.konto += #splitter nw.tmp",
    "scoreboard players operation #verdient nw.verdient += #splitter nw.tmp",
    f"playsound minecraft:block.amethyst_block.break player @s ~ ~ ~ 0.6 0.7",
]
for p in range(1, ANZ_STUFEN + 1):
    abbau.append(f"execute if score #phase nw.phase matches {p} if predicate {NS}:quell_mob_{p} run function {NS}:quell/mob_{p}")
    abbau.append(f"execute if score #phase nw.phase matches {p} unless score #mobda nw.tmp matches 1 run loot give @s loot {NS}:quell/phase{p}")
abbau += [
    "scoreboard players reset #mobda nw.tmp",
    f'title @s actionbar {J([txt("+", "gold"), {"score": {"name": "#splitter", "objective": "nw.tmp"}, "color": "gold"}, txt(" ", "gray"), coin(), txt("   mined ", "gray"), {"score": {"name": "#abbau", "objective": "nw.abbau"}, "color": "gray"}])}',
]
for i, g in enumerate(PHASEN_GRENZEN):
    abbau.append(f"execute if score #abbau nw.abbau matches {g} run function {NS}:quell/phase_wechsel {{phase:{i+2}}}")
fn("quell/abbau", abbau)

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
    "scoreboard players display name sb_2 nw.anzeige " + J([icon("zombie"), txt("Enemies  ", "dark_red"), {"score": {"name": "#gegner", "objective": "nw.gegner"}, "color": "white", "bold": True}]),
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
rx, ry, rz = RAMPE
preise = read_csv("preise.csv")
angebot = read_csv("angebot.csv")
sprueche = read_csv("sprueche.csv")


# ----------------------------------------------------------------------------
# Laden: Kaufen-Truhe (Doppeltruhe, 54 Felder) und Verkaufen-Fass am Tresen. Geld bleibt virtuell (Konto).
# Kaufen: Klick auf ein Symbol = 1 Stueck, Shift-Klick = max (meist 64). Verkaufen: Ware ins Fass legen
# (Shift-Klick aus dem Inventar), wird sofort verkauft. Nur Ware aus preise.csv, nie Werkzeug.
# ----------------------------------------------------------------------------
KAUF_A = (-1, 64, -5)      # Truhenhaelfte mit den Feldern 0..26 (oben im Fenster)   -> type=right bei facing=south
KAUF_B = (0, 64, -5)       # Truhenhaelfte mit den Feldern 27..53 (unten)            -> type=left
VERKAUF = (1, 64, -5)      # Fass
SEITE_SLOT = 53            # letztes Feld: Blaettern
PLATZ_PRO_SEITE = 53

def kauf_block(slot):
    return (KAUF_A if slot < 27 else KAUF_B), slot % 27

MODELL_GLOCKE = 'item_model="nachtwache:watch_bell",' if RESSOURCENPAKET else ""
MODELL_KIT = 'item_model="nachtwache:kit",' if RESSOURCENPAKET else ""
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
    if mx > 1:
        lore.append(f'[{{text:"Shift-click: buy {mx} for {preis * mx} ",color:"gray",italic:false}},{{text:"{COIN}",color:"white",italic:false}}]')
    comps = [f'custom_data={{nw_menu:{int(r["id"])}}}', f'custom_name={{text:"{name}",color:"white",italic:false}}', "lore=[" + ",".join(lore) + "]"]
    if comp and not r["item"].startswith("SET:") and r["item"] not in ("GLOCKE", "LATERNE", "KONTRAKT"):
        comps.insert(0, comp)
    elif r["item"] == "GLOCKE" and MODELL_GLOCKE:
        comps.insert(0, MODELL_GLOCKE[:-1])
    elif r["item"] == "LATERNE" and MODELL_LATERNE:
        comps.insert(0, MODELL_LATERNE[:-1])
    elif r["item"] == "KONTRAKT" and MODELL_KONTRAKT:
        comps.insert(0, MODELL_KONTRAKT[:-1])
    elif r["item"].startswith("SET:") and MODELL_KIT:
        comps.insert(0, MODELL_KIT[:-1])
    return f"{iid}[{','.join(comps)}]"

def seiten(phase):
    rows = [r for r in angebot if int(r["stufe"]) <= phase]
    return [rows[i:i + PLATZ_PRO_SEITE] for i in range(0, max(len(rows), 1), PLATZ_PRO_SEITE)]

BLAETTERN = 'minecraft:arrow[custom_data={nw_menu:9001},custom_name={text:"Next page",color:"yellow",italic:false}]'

for p in range(1, ANZ_STUFEN + 1):
    for si, rows in enumerate(seiten(p), 1):
        lines = []
        for slot in range(54):
            blk, ls = kauf_block(slot)
            if slot < len(rows):
                lines.append(f"item replace block {blk[0]} {blk[1]} {blk[2]} container.{ls} with {menue_item(rows[slot])}")
            elif slot == SEITE_SLOT and len(seiten(p)) > 1:
                lines.append(f"item replace block {blk[0]} {blk[1]} {blk[2]} container.{ls} with {BLAETTERN}")
            else:
                lines.append(f"item replace block {blk[0]} {blk[1]} {blk[2]} container.{ls} with minecraft:air")
        fn(f"sammler/kaufmenue_{p}_{si}", lines)

kaufmenue = ["execute unless score #seite nw.status matches 1.. run scoreboard players set #seite nw.status 1"]
for p in range(1, ANZ_STUFEN + 1):
    n = len(seiten(p))
    kaufmenue.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {n + 1}.. run scoreboard players set #seite nw.status 1")
    for si in range(1, n + 1):
        kaufmenue.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {si} run function {NS}:sammler/kaufmenue_{p}_{si}")
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
    f'summon minecraft:villager {sx} {sy} {sz} {{Tags:["nw.villager"],NoAI:1b,Silent:1b,Invulnerable:1b,PersistenceRequired:1b,NoGravity:1b,CustomName:{{text:"The Collector",color:"dark_red"}},CustomNameVisible:1b,VillagerData:{{profession:"minecraft:nitwit",level:1,type:"minecraft:swamp"}},Offers:{{Recipes:[]}},Rotation:[0f,0f]}}',
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

# Kaufen: jeden Tick pruefen, ob ein Symbol aus der Truhe genommen wurde
kauf_tick = [f"execute unless entity @a[x={KAUF_A[0]},y={KAUF_A[1]},z={KAUF_A[2]},distance=..8] run return 0"]
for p in range(1, ANZ_STUFEN + 1):
    for si, rows in enumerate(seiten(p), 1):
        for slot, r in enumerate(rows):
            blk, ls = kauf_block(slot)
            kauf_tick.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {si} unless items block {blk[0]} {blk[1]} {blk[2]} container.{ls} *[custom_data~{{nw_menu:{int(r['id'])}}}] run function {NS}:sammler/kauf/{int(r['id'])}")
        if len(seiten(p)) > 1:
            blk, ls = kauf_block(SEITE_SLOT)
            kauf_tick.append(f"execute if score #phase nw.phase matches {p} if score #seite nw.status matches {si} unless items block {blk[0]} {blk[1]} {blk[2]} container.{ls} *[custom_data~{{nw_menu:9001}}] run function {NS}:sammler/blaettern")
fn("sammler/kauf_tick", kauf_tick)
fn("sammler/blaettern", [
    "clear @a[x=-1,y=64,z=-5,distance=..8] *[custom_data~{nw_menu:9001}]",
    "scoreboard players add #seite nw.status 1",
    f"function {NS}:sammler/kaufmenue",
])

for r in angebot:
    rid, preis, mx, name = int(r["id"]), int(r["preis"]), int(r["max"]), r["name"]
    iid, comp, cnt = item_spec(r["item"])
    give_arg = f"{iid}[{comp}]" if comp else iid
    pred = f"*[custom_data~{{nw_menu:{rid}}}]"
    fn(f"sammler/kauf/{rid}", [
        # Wer hat es? (Cursor oder Inventar)
        f"execute as @a[x=-1,y=64,z=-5,distance=..8] store result score @s nw.tmp run clear @s {pred} 0",
        f"execute as @a[x=-1,y=64,z=-5,distance=..8,scores={{nw.tmp=1..}}] run function {NS}:sammler/kauf_abwickeln/{rid}",
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
        f'data modify storage nachtwache:tmp item set value "{give_arg}"' if not comp else f"data modify storage nachtwache:tmp item set value '{give_arg}'",
        f"function {NS}:sammler/geben with storage nachtwache:tmp",
        "playsound minecraft:entity.villager.yes neutral @s ~ ~ ~ 1 0.9",
        f"title @s actionbar {J([txt('Bought: ', 'green'), {'score': {'name': '#anz', 'objective': 'nw.tmp'}, 'color': 'white'}, txt(f' {name}  (-', 'green'), {'score': {'name': '#preis', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' ', 'green'), coin(), txt(')', 'green')])}",
        "execute store result score #r nw.tmp2 run random value 1..4",
        f"execute if score #r nw.tmp2 matches 1 run function {NS}:sammler/spruch/kauf",
    ])
fn("sammler/geben", ["$give @s $(item) $(n)"])

# Verkaufen: Fass am Tresen, alle 5 Ticks; Lieferrampe (Trichter) jede Sekunde zu 80 Prozent
def verkauf_funktionen(name, pos, slots, prozent):
    x, y, z = pos
    lines = [f"execute unless items block {x} {y} {z} container.* * run return 0"]
    for slot in range(slots):
        for r in preise:
            lines.append(f"execute if items block {x} {y} {z} container.{slot} minecraft:{r['item']} run function {NS}:sammler/{name}_slot {{slot:{slot},wert:{int(r['wert'])}}}")
    fn(f"sammler/{name}", lines)
    fn(f"sammler/{name}_slot", [
        f"$execute store result score #n nw.tmp run data get block {x} {y} {z} Items[{{Slot:$(slot)b}}].count",
        "$scoreboard players set #w nw.tmp2 $(wert)",
        "scoreboard players operation #gain nw.tmp = #n nw.tmp", "scoreboard players operation #gain nw.tmp *= #w nw.tmp2",
        f"scoreboard players set #pz nw.tmp2 {prozent}", "scoreboard players operation #gain nw.tmp *= #pz nw.tmp2", "scoreboard players operation #gain nw.tmp /= #100 nw.const",
        "execute if score #gain nw.tmp matches ..0 run return 0",     # zu wenig fuer einen Splitter: liegen lassen, bis mehr da ist
        "scoreboard players operation #konto nw.konto += #gain nw.tmp", "scoreboard players operation #verdient nw.verdient += #gain nw.tmp",
        f"$item replace block {x} {y} {z} container.$(slot) with minecraft:air",
        f"playsound minecraft:entity.villager.trade neutral @a[distance=..12] {x} {y} {z} 0.7 1",
        f"title @a[distance=..12] actionbar {J([txt('Sold: +', 'gold'), {'score': {'name': '#gain', 'objective': 'nw.tmp'}, 'color': 'gold'}, txt(' ', 'gold'), coin()])}",
    ])
verkauf_funktionen("verkauf", VERKAUF, 27, 100)
verkauf_funktionen("rampe", RAMPE, 5, 80)

# ----------------------------------------------------------------------------
# Uhr
# ----------------------------------------------------------------------------
fn("uhr/tick", [
    "execute unless entity @a run return 0",          # Zeit laeuft nur, wenn jemand auf dem Server ist
    "scoreboard players set #tagphase nw.tmp 1",
    f"execute if score #zeit nw.zeit matches {NACHT_START}..{TAG_START - 1} run scoreboard players set #tagphase nw.tmp 0",
    "scoreboard players operation #m nw.tmp = #tick nw.tick",
    f"execute if score #tagphase nw.tmp matches 1 run scoreboard players operation #m nw.tmp %= #{TAG_TEILER} nw.const",
    f"execute if score #tagphase nw.tmp matches 0 run scoreboard players operation #m nw.tmp %= #{NACHT_TEILER} nw.const",
    "execute unless score #m nw.tmp matches 0 run return 0",
    # Nacht: ab 23000 bleibt die Uhr stehen, solange noch Gegner leben. Sind alle tot, springt sie auf den Morgen.
    f"execute if score #status nw.status matches 1 if score #gegner nw.gegner matches 0 if score #zeit nw.zeit matches {NACHT_START + 300}.. run function {NS}:nacht/alles_tot",
    "execute if score #status nw.status matches 1 if score #zeit nw.zeit matches 23000.. if score #gegner nw.gegner matches 1.. run return run function nachtwache:nacht/haelt",
    f"execute if score #tagphase nw.tmp matches 1 run scoreboard players add #zeit nw.zeit {UHR_SCHRITT}",
    f"execute if score #tagphase nw.tmp matches 0 run scoreboard players add #zeit nw.zeit {UHR_SCHRITT}",
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
    # echte Sekunden = rest * 3 / (5 * 20)
    "scoreboard players operation #usek nw.tmp2 = #rest nw.tmp2",
    f"scoreboard players operation #usek nw.tmp2 *= #{TAG_TEILER} nw.const",
    "scoreboard players operation #usek nw.tmp2 /= #100 nw.const",
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

def summon_mob(key, extra_tags=(), pos=(0.5, 64, GEGNER_Z + 0.5)):
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
    return f"summon {BOSS_ENTITY[key]} 0.5 64 {GEGNER_Z + 0.5} {{{nbt}}}"

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
    f"execute if score #gegner nw.gegner matches 0 run function {NS}:nacht/bonus",
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
    f"execute as @e[tag=nw.boss_mutter] at @s run " + summon_mob("cave_spider", pos=("~", "~", "~")),
    f"execute as @e[tag=nw.boss_mutter] at @s run " + summon_mob("cave_spider", pos=("~", "~", "~")),
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
fn("gegner/glocke", [
    "scoreboard players set #glocke_geklingelt nw.upgrade 1",
    "playsound minecraft:block.bell.use block @a ~ ~ ~ 2 0.7", "playsound minecraft:block.bell.resonate block @a ~ ~ ~ 2 0.7",
    f"tellraw @a {J([txt('The watch bell rings. Something is on the road.', 'red')])}",
])
fn("gegner/einer", [
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
    "execute store result score #ppx nw.tmp run data get entity @p Pos[0]",
    "execute store result score #ppy nw.tmp run data get entity @p Pos[1]",
    "execute store result score #ppz nw.tmp run data get entity @p Pos[2]",
    "scoreboard players operation #ppx nw.tmp -= @s nw.px", "scoreboard players operation #ppy nw.tmp -= @s nw.py", "scoreboard players operation #ppz nw.tmp -= @s nw.pz",
    "execute if score #ppx nw.tmp matches ..-1 run scoreboard players operation #ppx nw.tmp *= #-1 nw.const",
    "execute if score #ppy nw.tmp matches ..-1 run scoreboard players operation #ppy nw.tmp *= #-1 nw.const",
    "execute if score #ppz nw.tmp matches ..-1 run scoreboard players operation #ppz nw.tmp *= #-1 nw.const",
    "scoreboard players operation #ppx nw.tmp += #ppy nw.tmp", "scoreboard players operation #ppx nw.tmp += #ppz nw.tmp",
    "execute unless score @s nw.dmin matches 0.. run scoreboard players set @s nw.dmin 9999",
    "execute if score #ppx nw.tmp < @s nw.dmin run scoreboard players operation @s nw.dmin = #ppx nw.tmp",
    "execute if score #ppx nw.tmp < @s nw.dmin run scoreboard players set @s nw.fest 0",
    "execute unless score #ppx nw.tmp < @s nw.dmin run scoreboard players add @s nw.fest 1",
    "execute if score #ppx nw.tmp matches ..3 run scoreboard players set @s nw.fest 0",
    f"execute if score @s nw.fest matches {FEST_TICKS}.. run return run function {NS}:gegner/festgefahren",
    f"execute if score @s nw.still matches {STILL_TICKS}.. if entity @a run function {NS}:gegner/blockiert",
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
# Festgefahren oder in den Nebel gefallen: der Gegner taucht neben dem naechsten Spieler wieder auf
# (auf dessen Ebene, auch auf Plattformen). Geht das nicht, an den Inselrand.
fn("gegner/festgefahren", [
    "scoreboard players set @s nw.still 0", "scoreboard players set @s nw.fest 0", "scoreboard players set @s nw.dmin 9999",
    f"tp @s {STRASSENMUND[0]} {STRASSENMUND[1]} {STRASSENMUND[2]}",
    f"execute if entity @p run function {NS}:gegner/zum_spieler",
    "playsound minecraft:entity.enderman.teleport hostile @a ~ ~ ~ 0.8 0.5",
])
fn("gegner/zum_spieler", [
    "execute at @p run spreadplayers ~ ~ 2 4 under 320 false @s",
    "execute at @s run particle minecraft:portal ~ ~1 ~ 0.5 1 0.5 0.5 40",
])

# ----------------------------------------------------------------------------
# Schutz, Spieler, Atmosphaere, Admin
# ----------------------------------------------------------------------------
fn("schutz/tick", [
    # Gegnerinsel und Strasse: jeden Tick zuruecksetzen, nichts darf abgebaut oder gebaut werden
    "scoreboard players operation #m2 nw.tmp2 = #tick nw.tick", "scoreboard players operation #m2 nw.tmp2 %= #2 nw.const",
    f"execute if score #m2 nw.tmp2 matches 0 run function {NS}:welt/gegnerinsel",
    f"execute if score #m2 nw.tmp2 matches 1 if score #status nw.status matches 1 run function {NS}:strasse/bauen",
    f"execute if score #m2 nw.tmp2 matches 1 if score #status nw.status matches 0 run function {NS}:strasse/entfernen",
    f"kill @e[type=item,x={-GEGNER_RADIUS-2},y={BODEN_Y-8},z={GEGNER_Z-GEGNER_RADIUS-1},dx={2*GEGNER_RADIUS+4},dy=25,dz={2*GEGNER_RADIUS+2}]",
    f"kill @e[type=item,x=-4,y={BODEN_Y-1},z={STRASSE_Z[0]},dx=8,dy=6,dz={STRASSE_Z[1]-STRASSE_Z[0]}]",
])
fn("schutz/sekunde", [
    f"function {NS}:welt/stand",
    f"function {NS}:laterne/sekunde",
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
    f"function {NS}:sammler/tresen",
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
fn("admin/zeit_nacht", [f"scoreboard players set #zeit nw.zeit {NACHT_START - 50}", "tellraw @a " + J([txt("[Nightwatch] Night is coming.", "yellow")])])
fn("admin/zeit_tag", [f"scoreboard players set #zeit nw.zeit {TAG_START - 50}", "tellraw @a " + J([txt("[Nightwatch] Day is coming.", "yellow")])])
fn("admin/welle_toeten", ["kill @e[tag=nw.welle]", "tellraw @a " + J([txt("[Nightwatch] Wave removed.", "yellow")])])
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
