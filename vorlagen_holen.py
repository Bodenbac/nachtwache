#!/usr/bin/env python3
"""Holt die drei Vorlagen fuer rp_build.py aus dem offiziellen 1.21.11-Client (Mojang), liegen danach in vorlagen/."""
import io, json, urllib.request, zipfile
from pathlib import Path
VERSION = "1.21.11"
DATEIEN = {"assets/minecraft/textures/block/amethyst_block.png": "amethyst_block.png",
           "assets/minecraft/textures/item/bell.png": "bell.png",
           "assets/minecraft/textures/gui/container/generic_54.png": "generic_54.png"}
ziel = Path(__file__).resolve().parent / "vorlagen"; ziel.mkdir(exist_ok=True)
m = json.load(urllib.request.urlopen("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
v = json.load(urllib.request.urlopen([x for x in m["versions"] if x["id"] == VERSION][0]["url"]))
print("lade client.jar (30 MB) ...")
jar = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(v["downloads"]["client"]["url"]).read()))
for quelle, name in DATEIEN.items():
    (ziel / name).write_bytes(jar.read(quelle)); print("ok", name)
