#!/usr/bin/env python3
"""Grafik fuer das Gluecksrad (v0.50): der Key und die sieben Truhen in den Stufenfarben.

Gleiche Machart wie ench_icons.py: 32x32, keine Kantenglaettung, dunkle Kontur ueber `umriss()`.
Die Farben sind genau die der sieben Quellstufen, damit die Truhe sofort ihre Wertigkeit zeigt.
"""
from PIL import Image, ImageDraw
from ench_icons import G, umriss

# (Name, dunkel, mittel, hell) in der Reihenfolge der Quellstufen
KISTEN_FARBEN = [
    ("grau",    (52, 52, 58),   (118, 118, 126), (205, 205, 212)),
    ("gruen",   (18, 66, 28),   (58, 158, 70),   (175, 242, 150)),
    ("blau",    (18, 38, 112),  (58, 108, 222),  (165, 205, 255)),
    ("lila",    (82, 44, 142),  (150, 100, 222), (228, 192, 255)),
    ("gelb",    (122, 90, 8),   (232, 192, 40),  (255, 246, 172)),
    ("orange",  (132, 48, 8),   (240, 122, 30),  (255, 212, 150)),
    ("schwarz", (6, 6, 10),     (34, 30, 42),    (98, 86, 114)),
]

def _neu():
    return Image.new("RGBA", (G, G), (0, 0, 0, 0))

def truhe(stufe):
    """Truhe von vorn: Deckel, Korpus, Goldschloss. stufe ist 1-basiert."""
    _, dunkel, mittel, hell = KISTEN_FARBEN[stufe - 1]
    im = _neu(); z = ImageDraw.Draw(im)
    z.rectangle([3, 6, 28, 13], fill=mittel)                 # Deckel
    z.rectangle([3, 6, 28, 8], fill=hell)
    z.rectangle([3, 12, 28, 13], fill=dunkel)
    z.rectangle([3, 15, 28, 27], fill=mittel)                # Korpus
    z.rectangle([3, 25, 28, 27], fill=dunkel)
    for x in (3, 27):
        z.rectangle([x, 15, x + 1, 27], fill=dunkel)
    z.rectangle([13, 11, 18, 19], fill=(60, 48, 24))         # Schloss
    z.rectangle([14, 12, 17, 18], fill=(214, 176, 74))
    z.rectangle([15, 14, 16, 16], fill=(60, 48, 24))
    return im

def key():
    """Schluessel: Ring, Schaft, zwei Baerte, zwei Funkeln."""
    im = _neu(); z = ImageDraw.Draw(im)
    z.ellipse([4, 6, 16, 18], fill=(150, 110, 30))
    z.ellipse([6, 8, 14, 16], fill=(0, 0, 0, 0))
    z.ellipse([5, 7, 15, 17], outline=(228, 188, 78), width=2)
    z.rectangle([14, 11, 28, 14], fill=(228, 188, 78))
    z.rectangle([14, 11, 28, 12], fill=(255, 235, 150))
    z.rectangle([22, 14, 24, 20], fill=(228, 188, 78))
    z.rectangle([26, 14, 28, 18], fill=(228, 188, 78))
    for p in ((8, 3), (26, 22)):
        z.rectangle([p[0], p[1], p[0] + 2, p[1] + 2], fill=(255, 255, 255))
    return im

def alle():
    """Name -> fertiges Bild mit Kontur, wie rp_build es ablegt."""
    aus = {"key": umriss(key())}
    for i, (name, *_) in enumerate(KISTEN_FARBEN, 1):
        aus[f"crate_{i}"] = umriss(truhe(i))
    return aus
