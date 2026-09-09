#!/usr/bin/env python3
"""
Baut das Ressourcenpaket (Client-Seite) fuer Nachtwache: out/nachtwache-rp.zip

Inhalt:
  - Icons der Seitenleiste als Schriftzeichen (icons.py): Muenze = ● (U+25CF, ohne Paket ein Punkt),
    Stufenscheiben U+E001..E007, Mond U+E010, Zombie U+E011, Totenkopf U+E012 (ohne Paket leere Kaestchen).
  - Sieben Quell-Stufen im Amethyst-Stil (Tuff, Gruen, Blau, Amethyst, Gelb, Orange, Schwarz).
  - Eigene Symbole fuer Watch Bell, Kits, Collector Lantern und Bounty Contract (item_model nachtwache:watch_bell / kit / lantern / contract).
  - Stern (U+2605) als Goldstern fuer den laufenden Kontrakt.
  - Der Zwerg (zwerg.py): zwei 3D-Modelle fuer item_display (Koerper, Axt-Arm), 2D-Symbol, und das Fass mit facing=down
    ist unsichtbar (sein Rucksack steckt im Zwerg).
  - Truhen-Oberflaeche in Daemmerungs-Toenen (gilt fuer alle Truhen, Faesser und den Laden).
  - Pack-Icon.

Aufruf:  python3 rp_build.py          (wird auch von build.py am Ende aufgerufen)
Braucht Pillow (pip install pillow). Vorlagen liegen in vorlagen/ (aus dem 1.21.11-Client kopiert).
"""
import hashlib, json, os, shutil, zipfile
from pathlib import Path
from PIL import Image, ImageDraw
import icons
import buecher, zwerg

HERE = Path(__file__).resolve().parent
VORLAGEN = HERE / "vorlagen"
RP_MIN, RP_MAX = 75, 90              # Ressourcenpaket-Format 1.21.11 = 75

# Stufenbloecke -> Farbverlauf (dunkel, mittel, hell). Reihenfolge wie STUFEN in build.py.
STUFEN_FARBEN = {
    "tuff":             ((52, 52, 58),   (118, 118, 126), (205, 205, 212)),
    "green_concrete":   ((18, 66, 28),   (58, 158, 70),   (175, 242, 150)),
    "blue_concrete":    ((18, 38, 112),  (58, 108, 222),  (165, 205, 255)),
    "budding_amethyst": ((82, 44, 142),  (150, 100, 222), (228, 192, 255)),
    "yellow_concrete":  ((122, 90, 8),   (232, 192, 40),  (255, 246, 172)),
    "orange_concrete":  ((132, 48, 8),   (240, 122, 30),  (255, 212, 150)),
    "black_concrete":   ((6, 6, 10),     (34, 30, 42),    (98, 86, 114)),
}

# Gehaeuse des Generators: dunkler Schiefer mit hellen Kanten, im Amethyst-Stil wie die Stufenbloecke
GENERATOR_FARBEN = ((26, 26, 34), (74, 76, 92), (162, 164, 186))

def verlauf(t, stops):
    """t in 0..1 -> Farbe aus drei Stuetzstellen."""
    a, b, c = stops
    if t < 0.5:
        u = t / 0.5; p, q = a, b
    else:
        u = (t - 0.5) / 0.5; p, q = b, c
    return tuple(int(round(p[i] + (q[i] - p[i]) * u)) for i in range(3))

def umfaerben(src, stops):
    """Helligkeit der Vorlage auf einen Farbverlauf abbilden (Struktur bleibt, Farbe wechselt)."""
    im = Image.open(src).convert("RGBA")
    px = im.load()
    lums = [0.299 * px[x, y][0] + 0.587 * px[x, y][1] + 0.114 * px[x, y][2]
            for y in range(im.height) for x in range(im.width) if px[x, y][3] > 0]
    lo, hi = min(lums), max(lums)
    out = Image.new("RGBA", im.size)
    op = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0:
                op[x, y] = (0, 0, 0, 0); continue
            l = 0.299 * r + 0.587 * g + 0.114 * b
            t = (l - lo) / (hi - lo) if hi > lo else 0.5
            op[x, y] = verlauf(t, stops) + (a,)
    return out

def muenze(size=16):
    return icons.muenze()

def glocke():
    """Watch Bell: Bronzeglocke an rotem Seil, Schallwellen links und rechts (Pixelbild)."""
    P = {".": None,
         "s": (150, 30, 30),    # Seil
         "S": (210, 60, 50),
         "o": (60, 34, 14),     # Rand dunkel
         "b": (168, 112, 40),   # Bronze
         "B": (214, 158, 64),   # Bronze hell
         "h": (255, 226, 150),  # Glanz
         "k": (40, 24, 10),     # Kloeppel
         "w": (255, 90, 70)}    # Schallwelle
    rows = [
        ".......ss.......",
        ".......Ss.......",
        "......oooo......",
        ".....obBBbo.....",
        ".....obhBbo.....",
        "w....obBBbo....w",
        ".w...obBBbo...w.",
        "w....obBBbo....w",
        ".w..obBBBBbo..w.",
        "w..obbBBBBbbo..w",
        "...obbbbbbbbo...",
        "...oooooooooo...",
        ".......kk.......",
        ".......kk.......",
        "................",
        "................",
    ]
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if P[ch]:
                px[x, y] = P[ch] + (255,)
    return im

def pixel(rows, P):
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if P.get(ch):
                px[x, y] = P[ch] + (255,)
    return im

def laterne():
    """Collector Lantern: Seelenlaterne mit violettem Schein, dunkler Rahmen, Haken."""
    return pixel([
        ".......kk.......",
        "......kook......",
        ".......kk.......",
        ".....kkkkkk.....",
        "....kddddddk....",
        "....kdffffdk....",
        "....kdfFFfdk....",
        "....kdfFhFdk....",
        "....kdfFFfdk....",
        "....kdffffdk....",
        "....kddddddk....",
        "....kkkkkkkk....",
        ".....kddddk.....",
        "......kkkk......",
        "................",
        "................",
    ], {"k": (28, 22, 34), "o": (90, 80, 100), "d": (70, 56, 90), "f": (120, 60, 200), "F": (170, 110, 255), "h": (240, 220, 255)})

def kontrakt():
    """Bounty Contract: Pergament mit Zeilen und rotem Siegel."""
    return pixel([
        "..pppppppppppp..",
        ".pPPPPPPPPPPPPp.",
        ".pPllllllllllPp.",
        ".pPPPPPPPPPPPPp.",
        ".pPllllllllPPPp.",
        ".pPPPPPPPPPPPPp.",
        ".pPlllllllllPPp.",
        ".pPPPPPPPPPPPPp.",
        ".pPllllllPPPPPp.",
        ".pPPPPPPPPrrPPp.",
        ".pPllllPPrRRrPp.",
        ".pPPPPPPPrRrrPp.",
        ".pPPPPPPPPrrPPp.",
        ".pPPPPPPPPPPPPp.",
        "..pppppppppppp..",
        "................",
    ], {"p": (120, 90, 50), "P": (226, 206, 160), "l": (110, 90, 70), "r": (150, 20, 20), "R": (220, 60, 50)})

def bogi_icon():
    """Bogi als 2D-Symbol: Zwergenkopf mit Kappe und Bogen."""
    return pixel([
        "....kkkkkkkk....",
        "...kKKKKKKKKk...",
        "..kKKKKKKKKKKk..",
        "..kkkkkkkkkkkk..",
        "..khhwkhhkwhhk..",
        "..khhhhnnhhhhk..",
        ".bkbBbbnnbbBbk..",
        "b.kbbBbbbbBbbk..",
        "b.kBbbbBbbbbBk..",
        "b.kggkbbbbbbkg..",
        "b.kggkbBbbBbkg..",
        "b.kggkkbbbbkkg..",
        "b.khhkggggggkh..",
        ".b..kggggggk....",
        "....kddkkddk....",
        "................",
    ], {"k": (24, 18, 14), "K": (96, 66, 36), "h": (222, 176, 138), "w": (250, 250, 250), "n": (196, 148, 112),
        "b": (178, 74, 32), "B": (208, 104, 52), "g": (46, 96, 56), "d": (36, 24, 14)})

def generator():
    """Source Generator: violetter Kristallwuerfel mit Kanten."""
    return pixel([
        "................",
        "....kkkkkkkk....",
        "...kvvvvvvvvk...",
        "..kvVVVVVVVVvk..",
        ".kvVVwwVVwwVVvk.",
        ".kvVVwwVVwwVVvk.",
        ".kvVVVVVVVVVVvk.",
        ".kvVVVVVVVVVVvk.",
        ".kvVwwVVVVwwVvk.",
        ".kvVwwVVVVwwVvk.",
        ".kvVVVVVVVVVVvk.",
        "..kvVVVVVVVVvk..",
        "...kvvvvvvvvk...",
        "....kkkkkkkk....",
        "................",
        "................",
    ], {"k": (34, 14, 52), "v": (110, 58, 168), "V": (156, 96, 224), "w": (226, 196, 255)})

def focus():
    """Source Focus: violettes Auge im Amethystrahmen."""
    return pixel([
        "................",
        ".....kkkkkk.....",
        "...kkddddddkk...",
        "..kdvvvvvvvvdk..",
        ".kdvvVVVVVVvvdk.",
        ".kdvVVwwwwVVvdk.",
        "kdvVVwwPPwwVVvdk",
        "kdvVwwPPPPwwVvdk",
        "kdvVVwwPPwwVVvdk",
        ".kdvVVwwwwVVvdk.",
        ".kdvvVVVVVVvvdk.",
        "..kdvvvvvvvvdk..",
        "...kkddddddkk...",
        ".....kkkkkk.....",
        "................",
        "................",
    ], {"k": (30, 16, 44), "d": (78, 40, 116), "v": (128, 72, 190), "V": (170, 110, 240), "w": (226, 196, 255), "P": (54, 20, 80)})

def decoy():
    """Decoy Totem: Kuerbiskopf auf einem Kreuz aus Holz."""
    return pixel([
        "................",
        "....kkkkkkkk....",
        "...kooooooook...",
        "..kooKKooKKook..",
        "..kooooooooook..",
        "..kooKooooKook..",
        "..kookKKKKkook..",
        "...kooooooook...",
        "....kkkkkkkk....",
        ".......hh.......",
        "..hhhhhHHhhhhh..",
        "..hHHHHHHHHHHh..",
        "..hhhhhHHhhhhh..",
        ".......hh.......",
        ".......hh.......",
        "................",
    ], {"k": (92, 48, 8), "o": (226, 130, 26), "O": (250, 170, 60), "K": (60, 26, 4), "h": (96, 68, 38), "H": (140, 102, 58)})

def schaedel():
    """Reaper's Skull: bleicher Totenkopf mit gruen gluehenden Augenhoehlen."""
    return pixel([
        "................",
        "....dddddddd....",
        "...dwwwwwwwwd...",
        "..dwWWWWWWWWwd..",
        "..dWWWWWWWWWWd..",
        ".dWWggWWWWggWWd.",
        ".dWWgGWWWWGgWWd.",
        ".dWWggWWWWggWWd.",
        ".dWWWWWdWWWWWWd.",
        "..dWWWddWWWWWd..",
        "..dwWWWWWWWWd...",
        "...dWdWdWdWdd...",
        "...dWdWdWdWdd...",
        "....dddddddd....",
        "................",
        "................",
    ], {"d": (24, 22, 26), "w": (150, 148, 138), "W": (214, 212, 200),
        "g": (54, 200, 96), "G": (168, 255, 190)})

def zwerg_icon():
    """Der Zwerg als 2D-Symbol (Ei im Laden und in der Hand)."""
    return pixel([
        "....kkkkkkkk....",
        "...kHHHHHHHHk...",
        "..kHHHHHHHHHHk..",
        "..kkkkkkkkkkkk..",
        "..khhwkhhkwhhk..",
        "..khhhhnnhhhhk..",
        "..kbBbbnnbbBbk..",
        "..kbbBbbbbBbbk..",
        "..kBbbbBbbbbBk..",
        ".kttkbbbbbbkttk.",
        ".kttkbBbbBbkttk.",
        ".kttkkbbbbkkttk.",
        ".khhkttggttkhhk.",
        "....kttttttk....",
        "....kddkkddk....",
        "....kkkk.kkkk...",
    ], {"k": (28, 22, 20), "H": (150, 156, 164), "h": (222, 176, 138), "w": (250, 250, 250), "n": (196, 148, 112),
        "b": (178, 74, 32), "B": (208, 104, 52), "t": (46, 74, 128), "g": (214, 166, 44), "d": (70, 48, 30)})

def kiste():
    """Kit: Versorgungskiste, dunkles Holz, Goldband, Schloss."""
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((1, 3, 14, 14), fill=(74, 46, 22, 255), outline=(38, 22, 10, 255))
    for y in (6, 9, 12):
        d.line((2, y, 13, y), fill=(58, 34, 16, 255))
    d.rectangle((1, 3, 14, 5), fill=(92, 58, 28, 255), outline=(38, 22, 10, 255))   # Deckel
    d.rectangle((6, 2, 9, 8), fill=(214, 166, 44, 255), outline=(120, 84, 12, 255)) # Goldband
    d.rectangle((7, 5, 8, 6), fill=(60, 40, 10, 255))                                # Schloss
    d.line((2, 4, 5, 4), fill=(122, 82, 44, 255)); d.line((10, 4, 13, 4), fill=(122, 82, 44, 255))
    return im

def gui_daemmerung(src):
    """Truhen-Oberflaeche: Grautoene der Vorlage nach dunkelviolett-grau abbilden. Titeltext (dunkelgrau) bleibt lesbar."""
    im = Image.open(src).convert("RGBA")
    px = im.load()
    stops = ((26, 22, 32), (128, 112, 140), (196, 180, 208))
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            l = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            px[x, y] = verlauf(l, stops) + (a,)
    return im

# Reiter des Ladens: Kategorie -> Vorlagendatei mit dem Symbol (muss zu KATEGORIEN in build.py passen)
REITER_SYMBOLE = {"BLOCKS": "stone", "MINERALS": "iron_ingot", "MOB": "rotten_flesh", "FOOD": "bread",
                  "TOOLS": "iron_pickaxe", "UTIL": "redstone", "BREW": "brewing_stand",
                  "BOOKS": "enchanted_book", "SPECIAL": "nether_star"}

def reiter_platte(quelle, fuell, rand, hell):
    """Farbplatte (16x16, Rahmen 2 px, Ecken frei) mit dem Symbol auf 12x12 in der Mitte."""
    im = Image.new("RGBA", (16, 16), fuell + (255,))
    px = im.load()
    for d in range(2):
        for i in range(16):
            px[i, d] = rand + (255,); px[i, 15 - d] = rand + (255,)
            px[d, i] = rand + (255,); px[15 - d, i] = rand + (255,)
    for x, y in ((0, 0), (15, 0), (0, 15), (15, 15)):
        px[x, y] = (0, 0, 0, 0)
    sym = Image.open(VORLAGEN / f"{quelle}.png").convert("RGBA").crop((0, 0, 16, 16))
    if not hell:                                  # inaktiv leicht abgedunkelt
        sp = sym.load()
        for y in range(16):
            for x in range(16):
                r, g, b, a = sp[x, y]
                sp[x, y] = (int(r * 0.78), int(g * 0.78), int(b * 0.78), a)
    im.alpha_composite(sym.resize((12, 12), Image.NEAREST), (2, 2))
    return im

def pack_icon():
    im = Image.new("RGBA", (128, 128), (14, 10, 20, 255))
    d = ImageDraw.Draw(im)
    for i in range(40):
        d.point(((i * 37) % 128, (i * 53) % 90), fill=(90, 80, 110, 255))
    m = muenze(16).crop((0, 0, 16, 14)).resize((80, 70), Image.NEAREST)
    im.alpha_composite(m, (24, 30))
    return im

def build(out_dir=None):
    out_dir = Path(out_dir) if out_dir else HERE / "out"
    rp = out_dir / "nachtwache-rp"
    if rp.exists():
        shutil.rmtree(rp)
    mc = rp / "assets" / "minecraft"
    nw = rp / "assets" / "nachtwache"

    def w(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, Image.Image):
            content.save(path)
        else:
            path.write_text(content, encoding="utf-8")

    w(rp / "pack.mcmeta", json.dumps({"pack": {
        "pack_format": RP_MIN, "min_format": RP_MIN, "max_format": RP_MAX,
        "description": [{"text": "Nachtwache", "color": "gold"}, {"text": " – coins, tiers, Collector", "color": "gray"}]}}, indent=2))
    w(rp / "pack.png", pack_icon())

    # Icons in der Standardschrift: Muenze = ● (U+25CF), Stufen U+E001..E007, Mond/Zombie/Totenkopf U+E010..E012.
    # 16 px Grafik bei Hoehe 8 -> halbe Skalierung, gezeichnet in 14 Zeilen = 7 px, Grundlinie wie die Buchstaben.
    provider = []
    for name, fn in icons.ALLE.items():
        w(nw / "textures" / "font" / f"{name}.png", fn())
        provider.append({"type": "bitmap", "file": f"nachtwache:font/{name}.png", "ascent": 7, "height": 8, "chars": [icons.ZEICHEN[name]]})
    w(mc / "font" / "default.json", json.dumps({"providers": provider + [
        {"type": "reference", "id": "minecraft:include/space"},
        {"type": "reference", "id": "minecraft:include/default", "filter": {"uniform": False}},
        {"type": "reference", "id": "minecraft:include/unifont"},
    ]}, indent=2))

    # Stufenbloecke
    for block, stops in STUFEN_FARBEN.items():
        w(mc / "textures" / "block" / f"{block}.png", umfaerben(VORLAGEN / "amethyst_block.png", stops))

    # Eigene Item-Symbole (item_model="nachtwache:watch_bell" / "nachtwache:kit")
    for name, img in (("watch_bell", glocke()), ("kit", kiste()), ("lantern", laterne()), ("contract", kontrakt()),
                      ("focus", focus()), ("decoy", decoy()), ("archer", bogi_icon()), ("life", icons.herz()), ("generator", generator()), ("skull_item", schaedel())):
        w(nw / "textures" / "item" / f"{name}.png", img)
        w(nw / "models" / "item" / f"{name}.json", json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": f"nachtwache:item/{name}"}}))
        w(nw / "items" / f"{name}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"nachtwache:item/{name}"}}))

    # Ladenreiter: Symbol auf einer Farbplatte, damit sich die Reiterzeile von der Ware abhebt
    # (Luis 09.09.2026). Inaktiv dunkelviolett, aktiv goldgelb, Rahmen 2 px, Symbol 12 px.
    # Der aktive Reiter glaenzt zusaetzlich, das macht das Datapack per enchantment_glint_override.
    for kat, quelle in REITER_SYMBOLE.items():
        for zustand, fuell, rand in (("aus", (74, 64, 92), (38, 32, 50)), ("an", (206, 178, 86), (255, 244, 168))):
            name = f"reiter_{kat.lower()}_{zustand}"
            w(nw / "textures" / "item" / f"{name}.png", reiter_platte(quelle, fuell, rand, zustand == "an"))
            w(nw / "models" / "item" / f"{name}.json", json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": f"nachtwache:item/{name}"}}))
            w(nw / "items" / f"{name}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"nachtwache:item/{name}"}}))

    # Verzauberungsbuecher: Buch im Farbton der Ausruestung, Zeichen der Faehigkeit, Punkte je Stufe (buecher.py)
    for kurz, img in buecher.alle().items():
        name = "buch_" + kurz.lower()
        w(nw / "textures" / "item" / f"{name}.png", img)
        w(nw / "models" / "item" / f"{name}.json", json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": f"nachtwache:item/{name}"}}))
        w(nw / "items" / f"{name}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"nachtwache:item/{name}"}}))

    # Der Zwerg: 3D-Modelle (Koerper, Axt-Arm) mit Textur-Atlas, 2D-Symbol, unsichtbares Fass (facing=down) als Rucksack
    for name, elemente in (("dwarf_body", zwerg.KOERPER), ("dwarf_arm", zwerg.ARM),
                           ("archer_body", zwerg.KOERPER_BOGI), ("archer_arm", zwerg.ARM_BOGEN)):
        atlas, model = zwerg.atlas_und_modell(elemente, f"nachtwache:item/{name}")
        w(nw / "textures" / "item" / f"{name}.png", atlas)
        w(nw / "models" / "item" / f"{name}.json", json.dumps(model))
        w(nw / "items" / f"{name}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"nachtwache:item/{name}"}}))
    w(nw / "textures" / "item" / "dwarf.png", zwerg_icon())
    w(nw / "models" / "item" / "dwarf.json", json.dumps({"parent": "minecraft:item/generated", "textures": {"layer0": "nachtwache:item/dwarf"}}))
    w(nw / "items" / "dwarf.json", json.dumps({"model": {"type": "minecraft:model", "model": "nachtwache:item/dwarf"}}))
    # Der Generator ist ein Fass mit facing=down, das hier unsichtbar wird. Darueber steht ein Block-Display
    # in der Stufenfarbe, das Verkaufsfass am Tresen (facing=up) bleibt normal sichtbar.
    # Seit v0.15 ist der Generator sichtbar: ein normaler Wuerfel in Steinoptik. Nur so zeigt Minecraft
    # beim Abbauen die Risse (unsichtbare Modelle haben keine Flaechen, auf denen sie gezeichnet werden koennten).
    # Die Stufenfarbe sitzt als kleiner Kristall oben auf dem Block (block_display aus build.py).
    w(mc / "textures" / "block" / "nw_generator.png", umfaerben(VORLAGEN / "amethyst_block.png", GENERATOR_FARBEN))
    w(nw / "models" / "block" / "generator.json", json.dumps({
        "parent": "minecraft:block/cube_all", "textures": {"all": "minecraft:block/nw_generator"}}))
    fass = json.loads((VORLAGEN / "barrel.json").read_text())
    for k in ("facing=down,open=false", "facing=down,open=true"):
        fass["variants"][k] = {"model": "nachtwache:block/generator"}
    w(mc / "blockstates" / "barrel.json", json.dumps(fass, indent=1))

    # Fraggles Rucksack ist eine Fallentruhe: unsichtbar durch leere Textur. Truhen sind keine vollen Bloecke,
    # deshalb bleiben die Flaechen der Nachbarbloecke sichtbar (mit einem Fass entstanden Loecher in der Welt).
    leer = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for name in ("trapped", "trapped_left", "trapped_right"):
        w(mc / "textures" / "entity" / "chest" / f"{name}.png", leer)

    # Truhen-Oberflaeche
    w(mc / "textures" / "gui" / "container" / "generic_54.png", gui_daemmerung(VORLAGEN / "generic_54.png"))

    zpath = out_dir / "nachtwache-rp.zip"
    # Feste Zeitstempel: gleiche Inhalte -> gleiche SHA1 (sonst muss server.properties bei jedem Build nachgezogen werden)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in sorted(os.walk(rp)):
            for f in sorted(fs):
                full = Path(root) / f
                zi = zipfile.ZipInfo(str(full.relative_to(rp)).replace(os.sep, "/"), date_time=(2026, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, full.read_bytes())
    sha1 = hashlib.sha1(zpath.read_bytes()).hexdigest()
    (out_dir / "nachtwache-rp.sha1").write_text(sha1 + "\n")
    print(f"Ressourcenpaket -> {zpath}  sha1 {sha1}")
    return zpath, sha1

if __name__ == "__main__":
    build()
