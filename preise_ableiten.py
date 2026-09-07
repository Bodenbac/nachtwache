#!/usr/bin/env python3
"""
Leitet Ankaufspreise fuer ALLE Gegenstaende aus den Rezepten des Spiels ab und schreibt tabellen/preise_abgeleitet.csv.

Grundlage: tabellen/preise.csv (von Hand gesetzte Basispreise, gewinnen immer) plus die Rezepte, Item-Tags und
Namen aus dem 1.21.11-Client in vorlagen/ (python3 vorlagen_holen.py). Regeln (Luis, 07.09.2026: Verarbeitung lohnt sich):
  Handwerk        Wert = Summe der Zutaten * 1,1 / Anzahl der Ergebnisse
  Schmelzen       Wert = Zutat * 1,25
  Steinsaege      Wert = Zutat / Anzahl (kein Gewinn, nur Form)
  Schmiedetisch   Wert = Summe der Zutaten * 1,1
Bei mehreren Rezepten zaehlt das billigste. Danach Muster fuer alles ohne Rezept (Staemme, Setzlinge, Blumen,
Musikscheiben usw.) und zuletzt 1 Coin fuer den Rest. Werkzeug, Waffen, Ruestung, Spawn-Eier und Kreativ-Bloecke
werden nie angekauft (nichts aus Versehen verkaufen).
"""
import csv, glob, json, math, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / "vorlagen"

# --- Namen und Item-Liste aus der Sprachdatei ---------------------------------------------------------
lang = json.load(open(V / "en_us.json", encoding="utf-8"))
namen = {}
for k, v in lang.items():
    m = re.fullmatch(r"(item|block)\.minecraft\.([a-z0-9_]+)", k)
    if m:
        namen.setdefault(m.group(2), v)
alle_items = set(namen)

# --- Basispreise -------------------------------------------------------------------------------------
basis = {}
for r in csv.DictReader(l for l in open(HERE / "tabellen" / "preise.csv", encoding="utf-8") if not l.startswith("#")):
    basis[r["item"]] = int(r["wert"])

# --- Nie ankaufen -------------------------------------------------------------------------------------
NIE_SUFFIX = ("_sword", "_pickaxe", "_axe", "_shovel", "_hoe", "_helmet", "_chestplate", "_leggings", "_boots",
              "_spawn_egg", "_command_block", "_armor", "_bundle", "_candle_cake", "_pottery_shard", "_minecart_x")
NIE = {"bow", "crossbow", "trident", "shield", "mace", "elytra", "fishing_rod", "shears", "flint_and_steel", "brush",
       "spyglass", "carrot_on_a_stick", "warped_fungus_on_a_stick", "totem_of_undying", "wolf_armor",
       "command_block", "structure_block", "structure_void", "jigsaw", "barrier", "light", "debug_stick", "knowledge_book",
       "bedrock", "spawner", "trial_spawner", "vault", "reinforced_deepslate", "budding_amethyst", "petrified_oak_slab",
       "player_head", "written_book", "air", "bundle", "test_block", "test_instance_block", "end_portal", "end_gateway",
       "nether_portal", "moving_piston", "piston_head", "frosted_ice", "bubble_column", "lava", "water", "fire", "soul_fire",
       "cave_air", "void_air", "farmland", "dirt_path", "candle_cake", "cake", "sweet_berry_bush", "cocoa", "kelp_plant",
       "bamboo_sapling", "attached_melon_stem", "attached_pumpkin_stem", "melon_stem", "pumpkin_stem", "beetroots",
       "carrots", "potatoes", "wheat", "tall_seagrass", "twisting_vines_plant", "weeping_vines_plant", "cave_vines",
       "cave_vines_plant", "pitcher_crop", "torchflower_crop", "powder_snow", "tripwire", "redstone_wire", "big_dripleaf_stem",
       "chorus_plant", "frogspawn", "command_block_minecart", "lava_cauldron", "water_cauldron", "powder_snow_cauldron",
       "copper_golem_statue", "copper_bars_x"}
def nie(item):
    return item in NIE or item.endswith(NIE_SUFFIX) or item.startswith("infested_") or "_wall_" in item and item.endswith(("_sign", "_banner", "_head", "_skull", "_torch", "_fan"))

# --- Rezepte ------------------------------------------------------------------------------------------
tags = {}
for f in glob.glob(str(V / "tags_item" / "*.json")):
    tags["minecraft:" + Path(f).stem] = json.load(open(f))["values"]
def tag_items(name, seen=()):
    out = []
    for v in tags.get(name.lstrip("#"), []):
        v = v["id"] if isinstance(v, dict) else v
        if v.startswith("#"):
            if v not in seen: out += tag_items(v, seen + (v,))
        else:
            out.append(v.split(":", 1)[1])
    return out
def optionen(z):
    """Zutat -> Liste moeglicher Items."""
    if isinstance(z, list):
        r = []
        for x in z: r += optionen(x)
        return r
    if isinstance(z, dict):
        return optionen(z.get("item") or z.get("tag") and "#" + z["tag"])
    if z.startswith("#"): return tag_items(z)
    return [z.split(":", 1)[1]]

rezepte = []   # (ergebnis, anzahl, art, [zutat-optionen])
for f in glob.glob(str(V / "rezepte" / "*.json")):
    d = json.load(open(f))
    t = d["type"].split(":")[1]
    res = d.get("result")
    if not isinstance(res, dict) or "id" not in res: continue
    erg, anz = res["id"].split(":", 1)[1], res.get("count", 1)
    if t == "crafting_shaped":
        zut = [optionen(d["key"][c]) for row in d["pattern"] for c in row if c != " "]
        rezepte.append((erg, anz, "handwerk", zut))
    elif t == "crafting_shapeless":
        rezepte.append((erg, anz, "handwerk", [optionen(z) for z in d["ingredients"]]))
    elif t in ("smelting", "blasting", "smoking", "campfire_cooking"):
        rezepte.append((erg, 1, "schmelzen", [optionen(d["ingredient"])]))
    elif t == "stonecutting":
        rezepte.append((erg, anz, "saege", [optionen(d["ingredient"])]))
    elif t == "smithing_transform":
        rezepte.append((erg, 1, "schmiede", [optionen(d["template"]), optionen(d["base"]), optionen(d["addition"])]))
    elif t == "crafting_transmute":
        rezepte.append((erg, 1, "handwerk", [optionen(d["input"]), optionen(d["material"])]))

# --- Muster fuer alles ohne Rezept ------------------------------------------------------------------------
def muster(item):
    if item.endswith("_log") or item.endswith("_stem") and "mushroom" not in item or item in ("bamboo_block",): return 15
    if item.startswith("stripped_"): return wert.get(item[len("stripped_"):], 15) + 1
    if item.endswith("_sapling") or item.endswith("_propagule"): return 20
    if item.endswith("_leaves"): return 1
    if item.endswith(("_coral", "_coral_fan")): return 4
    if item.endswith("_coral_block"): return 8
    if item.startswith("dead_"): return 1
    if item.startswith("music_disc_"): return 30
    if item.endswith(("_head", "_skull")): return 100
    if item.endswith("_pottery_sherd"): return 20
    if item.endswith("_smithing_template"): return 300
    if item.endswith("_froglight"): return 15
    if item.endswith("_amethyst_bud"): return 5
    if item.startswith("pale_moss") or item == "pale_hanging_moss": return 2
    if item in ("nether_gold_ore",): return 20
    if item in ("ominous_trial_key",): return 200
    if item in ("trial_key",): return 100
    if item in ("resin_clump",): return 5
    if item.startswith("deepslate_") and item.endswith("_ore"): return wert.get(item[len("deepslate_"):], 5) + 1
    for p in ("exposed_", "weathered_", "oxidized_", "waxed_"):
        if item.startswith(p):
            rest = item[len(p):]
            if rest == "copper": rest = "copper_block"
            if rest in wert: return wert[rest] + 1
            return None
    if item.endswith("_concrete") and item[:-len("_concrete")] + "_concrete_powder" in wert:
        return wert[item[:-len("_concrete")] + "_concrete_powder"] + 1
    if item.endswith(("_tulip", "_orchid", "_bluet", "_flower", "_lily", "_rose", "_bush", "_daisy")) or item in ("dandelion", "poppy", "allium", "cornflower", "lilac", "peony", "sunflower", "torchflower", "pitcher_plant", "wither_rose", "spore_blossom", "pink_petals", "wildflowers", "leaf_litter", "bush", "firefly_bush", "cactus_flower", "open_eyeblossom", "closed_eyeblossom"): return 2
    if item.endswith("_mushroom") or item.endswith("_fungus") or item.endswith("_roots") or item.endswith("_seeds"): return 2
    if item.endswith("_mushroom_block") or item == "mushroom_stem": return 5
    if item.endswith("_egg") and item not in ("dragon_egg", "sniffer_egg", "turtle_egg"): return 2
    if item.endswith("_banner_pattern"): return 20
    if item in ("carved_pumpkin",): return 10
    if item in ("experience_bottle",): return 30
    if item in ("breeze_rod",): return 20
    if item in ("heavy_core",): return 500
    if item in ("creaking_heart",): return 100
    if item in ("lodestone_compass",): return 200
    if item in ("filled_map", "firework_star", "harness"): return 10
    if item in ("nether_star",): return 3000
    if item in ("dragon_egg",): return 5000
    if item in ("dragon_head",): return 2000
    if item in ("heart_of_the_sea",): return 500
    if item in ("sniffer_egg",): return 500
    if item in ("enchanted_book",): return 200
    if item in ("bell",): return 200
    if item in ("echo_shard",): return 100
    if item in ("disc_fragment_5",): return 50
    if item in ("saddle", "name_tag", "turtle_egg", "sponge", "wet_sponge", "goat_horn", "lead"): return 50
    if item in ("potion", "splash_potion", "lingering_potion", "tipped_arrow", "ominous_bottle"): return 20
    if item in ("end_portal_frame",): return 600
    return None


# --- Ableitung bis nichts mehr billiger wird ------------------------------------------------------------
wert = dict(basis)
FAKTOR = {"handwerk": 1.1, "schmelzen": 1.25, "saege": 1.0, "schmiede": 1.1}
hat_rezept = {r[0] for r in rezepte}
for _ in range(60):
    geaendert = False
    # Muster fuer alles ohne Rezept (Staemme, Setzlinge, Sterne ...), damit Rezepte darauf aufbauen koennen
    for item in alle_items:
        if item in wert or item in hat_rezept: continue
        m = muster(item)
        if m is not None:
            wert[item] = m; geaendert = True
    for erg, anz, art, zut in rezepte:
        if erg in basis: continue
        summe = 0
        ok = True
        for opts in zut:
            w = [wert[o] for o in opts if o in wert]
            if not w: ok = False; break
            summe += min(w)
        if not ok: continue
        kand = max(1, math.ceil(summe * FAKTOR[art] / anz))
        if erg not in wert or kand < wert[erg]:
            wert[erg] = kand; geaendert = True
    if not geaendert: break

for item in sorted(alle_items):
    if item in wert or nie(item): continue
    m = muster(item)
    wert[item] = m if m is not None else 1

# --- Schreiben ----------------------------------------------------------------------------------------------
ziel = HERE / "tabellen" / "preise_abgeleitet.csv"
with open(ziel, "w", encoding="utf-8") as f:
    f.write("# Automatisch aus den Spielrezepten abgeleitet (python3 preise_ableiten.py). Nicht von Hand aendern,\n")
    f.write("# Basispreise gehoeren nach preise.csv (die gewinnen immer). quelle: basis, rezept, muster oder rest.\n")
    f.write("item,name,wert,quelle\n")
    for item in sorted(alle_items):
        if nie(item): continue
        q = "basis" if item in basis else ("rezept" if item in hat_rezept and wert[item] > 1 else ("muster" if muster(item) is not None else "rest"))
        f.write(f"{item},{namen[item].replace(',', ' ')},{wert[item]},{q}\n")
n = sum(1 for i in alle_items if not nie(i))
print(f"{n} Gegenstaende bepreist ({len(basis)} Basis, {sum(1 for i in alle_items if i not in basis and not nie(i) and muster(i) is None and wert[i] > 1)} aus Rezepten), {sum(1 for i in alle_items if nie(i))} ausgeschlossen -> {ziel}")
