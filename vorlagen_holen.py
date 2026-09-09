#!/usr/bin/env python3
"""Holt die drei Vorlagen fuer rp_build.py aus dem offiziellen 1.21.11-Client (Mojang), liegen danach in vorlagen/."""
import io, json, urllib.request, zipfile
from pathlib import Path
VERSION = "1.21.11"
DATEIEN = {"assets/minecraft/textures/block/amethyst_block.png": "amethyst_block.png",
           "assets/minecraft/textures/item/bell.png": "bell.png",
           "assets/minecraft/textures/gui/container/generic_54.png": "generic_54.png",
           # Grundlage der Buchsymbole: das echte Werkzeug, darauf ein eigenes Zeichen (buecher.py)
           "assets/minecraft/textures/item/diamond_sword.png": "diamond_sword.png",
           "assets/minecraft/textures/item/diamond_pickaxe.png": "diamond_pickaxe.png",
           "assets/minecraft/textures/item/bow.png": "bow.png",
           "assets/minecraft/textures/item/diamond_chestplate.png": "diamond_chestplate.png",
           "assets/minecraft/textures/item/diamond_boots.png": "diamond_boots.png",
           "assets/minecraft/textures/item/enchanted_book.png": "enchanted_book.png",
           "assets/minecraft/textures/item/book.png": "book.png",
           # Symbole der Ladenreiter, kommen in rp_build.py auf eine Farbplatte
           "assets/minecraft/textures/item/brick.png": "brick.png",
           "assets/minecraft/textures/item/rotten_flesh.png": "rotten_flesh.png",
           "assets/minecraft/textures/item/bread.png": "bread.png",
           "assets/minecraft/textures/item/iron_ingot.png": "iron_ingot.png",
           "assets/minecraft/textures/item/iron_pickaxe.png": "iron_pickaxe.png",
           "assets/minecraft/textures/item/redstone.png": "redstone.png",
           "assets/minecraft/textures/item/brewing_stand.png": "brewing_stand.png",
           "assets/minecraft/textures/item/nether_star.png": "nether_star.png",
           # Knoepfe in den Minion-Rucksaecken, ebenfalls auf einer Farbplatte
           "assets/minecraft/textures/item/hopper.png": "hopper.png",
           "assets/minecraft/textures/item/emerald.png": "emerald.png",
           "assets/minecraft/textures/item/bundle.png": "bundle.png",
           "assets/minecraft/textures/item/shulker_shell.png": "shulker_shell.png",
           "assets/minecraft/textures/item/netherite_pickaxe.png": "netherite_pickaxe.png",
           "assets/minecraft/textures/item/feather.png": "feather.png",
           "assets/minecraft/textures/item/iron_sword.png": "iron_sword.png",
           "assets/minecraft/textures/item/crossbow_arrow.png": "crossbow_arrow.png",
           "assets/minecraft/textures/item/blaze_powder.png": "blaze_powder.png",
           "assets/minecraft/textures/item/end_crystal.png": "end_crystal.png",
           "assets/minecraft/textures/item/spyglass.png": "spyglass.png",
           "assets/minecraft/textures/block/piston_top.png": "piston_top.png",
           "assets/minecraft/textures/block/gray_stained_glass.png": "gray_stained_glass.png"}
ziel = Path(__file__).resolve().parent / "vorlagen"; ziel.mkdir(exist_ok=True)
m = json.load(urllib.request.urlopen("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
v = json.load(urllib.request.urlopen([x for x in m["versions"] if x["id"] == VERSION][0]["url"]))
print("lade client.jar (30 MB) ...")
jar = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(v["downloads"]["client"]["url"]).read()))
for quelle, name in DATEIEN.items():
    (ziel / name).write_bytes(jar.read(quelle)); print("ok", name)
