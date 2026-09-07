"""Pixel-Icons fuer die Seitenleiste. 16x16-Grafik, gezeichnet wird in Zeile 0..13 und Spalte 1..14 (14x14),
im Spiel mit Hoehe 8 und Ascent 7 -> 7 Pixel hoch, genau wie ein Grossbuchstabe, gleiche Grundlinie.
Muenze, Stufenscheiben (gleiche Form wie die Muenze, eigene Farbe), Mond, Zombie, Totenkopf."""
from PIL import Image

def bild(rows, P):
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if P.get(ch):
                px[x, y] = P[ch] + (255,)
    return im

# Scheibe 14x14: o = Rand, b = Koerper, B = hell, h = Glanz, d = dunkel (Praegung: Ring wie der Quell)
SCHEIBE = [
    ".....oooooo.....",
    "...oobBBBBboo...",
    "..obBhhBBBBbbo..",
    ".obBhBBddBBBbbo.",
    ".obBBBddddBBbbo.",
    ".obBBddBBddBbbdo",
    ".obBBddBBddBbbdo",
    ".obBBddBBddBbbdo",
    ".obBBBddddBBbddo",
    ".obbBBBddBBbbddo",
    ".obbbBBBBbbbddo.",
    "..obbbbbbbbddo..",
    "...oobbbbddoo...",
    ".....oooooo.....",
    "................",
    "................",
]

def scheibe(rand, koerper, hell, glanz, dunkel):
    return bild(SCHEIBE, {"o": rand, "b": koerper, "B": hell, "h": glanz, "d": dunkel})

def muenze():
    return scheibe((96, 62, 10), (214, 160, 36), (240, 198, 70), (255, 240, 170), (170, 116, 22))

# Stufenscheiben in der Farbe der Stufe (Reihenfolge wie STUFEN in build.py)
STUFEN_SCHEIBEN = {
    1: ((40, 40, 46),   (118, 118, 126), (160, 160, 168), (215, 215, 222), (88, 88, 96)),     # Grau
    2: ((14, 52, 22),   (56, 150, 66),   (92, 196, 100),  (180, 240, 160), (36, 110, 46)),    # Gruen
    3: ((14, 30, 90),   (56, 104, 214),  (100, 150, 240), (170, 205, 255), (36, 76, 170)),    # Blau
    4: ((60, 30, 110),  (146, 96, 218),  (182, 140, 240), (228, 196, 255), (110, 66, 180)),   # Lila
    5: ((110, 82, 6),   (226, 186, 36),  (244, 214, 80),  (255, 246, 172), (180, 142, 20)),   # Gelb
    6: ((120, 44, 6),   (232, 118, 28),  (246, 156, 70),  (255, 212, 150), (186, 86, 16)),    # Orange
    7: ((4, 4, 8),      (34, 30, 42),    (68, 60, 80),    (110, 98, 128),  (18, 16, 24)),     # Schwarz
}

def stufe(n):
    return scheibe(*STUFEN_SCHEIBEN[n])

MOND = [
    "......ooooo.....",
    "....oommmmmoo...",
    "...ommmmmmmmmo..",
    "..ommmmmooooooo.",
    ".ommmmmo........",
    ".ommmmo.........",
    ".ommmmo.........",
    ".ommmmo.........",
    ".ommmmo.........",
    ".ommmmmo........",
    "..ommmmmooooooo.",
    "...ommmmmmmmmo..",
    "....oommmmmoo...",
    "......ooooo.....",
    "................",
    "................",
]

def mond():
    return bild(MOND, {"o": (90, 90, 60), "m": (236, 232, 190)})

ZOMBIE = [
    ".oooooooooooooo.",
    ".oddddddddddddo.",
    ".odggddgggddggo.",
    ".odgggggggggggo.",
    ".oggkkgggggkkgo.",
    ".oggkkgggggkkgo.",
    ".ogggggggggggdo.",
    ".ogggggkkkkggdo.",
    ".odgggkkkkkkgdo.",
    ".odggggkkkkggdo.",
    ".odgggggggggddo.",
    ".oddgggggggdddo.",
    ".odddddgggddddo.",
    ".oooooooooooooo.",
    "................",
    "................",
]

def zombie():
    return bild(ZOMBIE, {"o": (20, 40, 16), "d": (46, 96, 40), "g": (74, 140, 62), "k": (10, 14, 8)})

SKULL = [
    "....oooooooo....",
    "..oowwwwwwwwoo..",
    ".owwwwwwwwwwwwo.",
    ".owwwwwwwwwwwwo.",
    ".owwkkkwwwkkkwo.",
    ".owkkkkwwwkkkkwo",
    ".owkkkkwwwkkkkwo",
    ".owwkkkwwwkkkwo.",
    ".owwwwwwkwwwwwo.",
    "..owwwwkkkwwwo..",
    "..oowwwwwwwwoo..",
    "...owkwkwkwkwo..",
    "...oowwwwwwwoo..",
    ".....oooooooo...",
    "................",
    "................",
]

def totenkopf():
    return bild(SKULL, {"o": (60, 60, 66), "w": (228, 228, 224), "k": (20, 20, 24)})

# Zeichen in der Standardschrift: Muenze bleibt ● (U+25CF), Rest im Private-Use-Bereich
ZEICHEN = {"coin": "●", "moon": "", "zombie": "", "skull": ""}
for _n in range(1, 8):
    ZEICHEN[f"tier{_n}"] = chr(0xE000 + _n)

ALLE = {"coin": muenze, "moon": mond, "zombie": zombie, "skull": totenkopf}
for _n in range(1, 8):
    ALLE[f"tier{_n}"] = (lambda n: (lambda: stufe(n)))(_n)
