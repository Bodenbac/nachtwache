#!/usr/bin/env python3
"""Symbole der Upgrade-Station (Reiter Enchanting), 32x32.

Bis v0.46 waren es 5x5-Zeichen aus buecher.py, verdoppelt auf eine 16er-Textur. Luis am 10.09.2026:
"die Icons sehen scheisse aus", und weil das Symbol den ganzen Slot fuellt, darf die Textur hoeher
aufloesen. Seit v0.47 ist jedes Symbol echte Pixelgrafik auf 32x32, ohne Kantenglaettung.

Regeln, die sich beim Entwerfen bewaehrt haben:
- Werkzeug und Waffe kommen als Originaltextur aus dem Client (`vanilla()`), nicht selbst gepixelt.
  Selbst gezeichnete Schwerter und Spitzhacken hat Luis reihenweise verworfen.
- Jedes Symbol bekommt eine dunkle Kontur (`umriss()`). Ohne die verschwimmt ein helles Symbol auf
  der goldenen Maximum-Platte.
- Unten bleiben fuenf Pixel frei, dort zeichnet rp_build die Stufenbalken.
- Symbole, die nie auf demselben Teil vorkommen, duerfen sich aehneln (Fire Aspect nur Schwert,
  Flame nur Bogen). Die Flamme sitzt bei beiden oben links.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

G = 32
HERE = Path(__file__).resolve().parent
VORLAGEN = HERE / "vorlagen"

def neu():
    return Image.new("RGBA", (G, G), (0, 0, 0, 0))

def d(im):
    return ImageDraw.Draw(im)

def vanilla(name, versatz=(0, 0), zoom=2):
    """Originaltextur aus dem Client auf 32x32 vergroessert. `vorlagen_holen.py` holt sie."""
    q = Image.open(VORLAGEN / f"{name}.png").convert("RGBA").crop((0, 0, 16, 16))
    q = q.resize((16 * zoom, 16 * zoom), Image.NEAREST)
    im = neu()
    im.alpha_composite(q, versatz)
    return im

def flamme(im, x, y, h=17, warm=(240, 140, 30), heiss=(255, 225, 120), rand=(190, 60, 20)):
    """Flamme, (x, y) ist die Mitte der Unterkante."""
    z = d(im)
    b = h * 2 // 3
    z.polygon([(x, y - h), (x + b // 2, y - h // 2), (x + b // 2, y), (x - b // 2, y), (x - b // 2, y - h // 2)], fill=rand)
    z.ellipse([x - b // 2, y - h * 3 // 5, x + b // 2, y], fill=warm)
    z.polygon([(x, y - h + 2), (x + b // 3, y - h // 3), (x - b // 3, y - h // 3)], fill=warm)
    z.ellipse([x - b // 5, y - h // 3, x + b // 5, y - 2], fill=heiss)

def pfeilspitze(z, x, y, r, farbe, richtung=1):
    z.polygon([(x, y - r), (x + r * richtung, y), (x, y + r)], fill=farbe)

def umriss(sym, farbe=(24, 20, 30, 255)):
    """Ein Pixel dunkle Kontur um alles Sichtbare, damit das Symbol auf jeder Plattenfarbe steht."""
    aus = Image.new("RGBA", (G, G), (0, 0, 0, 0))
    sp, ap = sym.load(), aus.load()
    for y in range(G):
        for x in range(G):
            if sp[x, y][3] < 40:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < G and 0 <= ny < G and sp[nx, ny][3] >= 40:
                        ap[x, y] = farbe
                        break
    aus.alpha_composite(sym)
    return aus

# ---------------------------------------------------------------- die siebzehn Symbole
def sharpness():
    im = vanilla("diamond_sword")
    z = d(im)
    for x, y, g in ((25, 3, 2), (29, 7, 1), (21, 6, 1), (27, 12, 1)):     # Schneide blitzt
        z.rectangle([x, y, x + g, y + g], fill=(255, 255, 255))
        z.rectangle([x - 1, y + g // 2, x + g + 1, y + g // 2], fill=(210, 240, 255))
        z.rectangle([x + g // 2, y - 1, x + g // 2, y + g + 1], fill=(210, 240, 255))
    return im

def protection():
    im = neu(); z = d(im)
    z.polygon([(16, 3), (28, 8), (28, 17), (16, 29), (4, 17), (4, 8)], fill=(58, 96, 180))
    z.polygon([(16, 6), (25, 10), (25, 16), (16, 25), (7, 16), (7, 10)], fill=(120, 165, 240))
    z.polygon([(16, 9), (22, 12), (22, 16), (16, 21), (10, 16), (10, 12)], fill=(58, 96, 180))
    z.rectangle([15, 10, 17, 20], fill=(225, 235, 255))
    z.rectangle([11, 13, 21, 15], fill=(225, 235, 255))
    return im

def efficiency():
    im = vanilla("diamond_pickaxe", versatz=(4, 0))
    z = d(im)
    for i, y in enumerate((7, 14, 21)):                                   # Tempolinien dahinter
        z.rectangle([0, y, 7 - i * 2, y + 3], fill=(110, 200, 255))
        z.rectangle([0, y, 7 - i * 2, y + 1], fill=(190, 235, 255))
    return im

def power():
    im = neu(); z = d(im)
    z.arc([4, 2, 22, 30], start=292, end=68, fill=(126, 84, 44), width=5)
    z.arc([5, 3, 21, 29], start=292, end=68, fill=(168, 118, 66), width=2)
    z.line([19, 6, 19, 26], fill=(238, 238, 228), width=1)                # Sehne
    z.line([9, 16, 28, 16], fill=(222, 228, 240), width=3)                # Pfeilschaft
    pfeilspitze(z, 31, 16, 5, (208, 216, 232))
    z.polygon([(9, 16), (14, 11), (14, 21)], fill=(150, 235, 170))
    return im

def feather_falling():
    im = neu(); z = d(im)
    z.polygon([(25, 4), (29, 10), (20, 21), (11, 27), (8, 24), (14, 14)], fill=(232, 238, 250))
    z.polygon([(25, 4), (27, 12), (16, 22), (11, 26), (16, 15)], fill=(255, 255, 255))
    z.line([26, 5, 9, 26], fill=(176, 186, 208), width=2)                 # Kiel
    for i in range(4):
        z.line([22 - i * 4, 9 + i * 4, 26 - i * 4, 8 + i * 4], fill=(198, 208, 228), width=1)
    z.line([9, 26, 6, 30], fill=(176, 186, 208), width=2)
    return im

def fortune():
    im = neu(); z = d(im)
    def gem(cx, cy, r, hell, dunkel):
        z.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=dunkel)
        z.polygon([(cx, cy - r + 2), (cx + r - 2, cy), (cx, cy + 1)], fill=hell)
    gem(16, 18, 10, (140, 255, 200), (40, 165, 110))
    gem(7, 9, 5, (170, 255, 215), (52, 185, 125))
    gem(26, 11, 4, (170, 255, 215), (52, 185, 125))
    z.rectangle([15, 13, 17, 15], fill=(255, 255, 255))
    return im

def looting():
    im = neu(); z = d(im)
    def muenze(cx, cy, r=8):
        z.ellipse([cx - r, cy - r // 2 - 2, cx + r, cy + r // 2 + 2], fill=(150, 110, 30))
        z.ellipse([cx - r + 1, cy - r // 2 - 1, cx + r - 1, cy + r // 2 + 1], fill=(228, 188, 78))
        z.ellipse([cx - r + 4, cy - 2, cx + r - 4, cy + 2], fill=(255, 235, 150))
    muenze(16, 25); muenze(12, 18); muenze(19, 11)
    return im

def unbreaking():
    im = neu(); z = d(im)
    z.rectangle([3, 5, 29, 11], fill=(150, 158, 172))
    z.rectangle([3, 5, 29, 7], fill=(196, 204, 220))
    z.polygon([(8, 11), (24, 11), (20, 17), (12, 17)], fill=(120, 128, 142))
    z.rectangle([12, 17, 20, 21], fill=(150, 158, 172))
    z.rectangle([7, 21, 25, 28], fill=(120, 128, 142))
    z.rectangle([7, 21, 25, 23], fill=(168, 176, 190))
    return im

def thorns():
    im = neu(); z = d(im)
    z.line([4, 27, 27, 5], fill=(58, 110, 58), width=5)                   # Ranke
    z.line([5, 26, 26, 6], fill=(96, 160, 84), width=2)
    for x, y, s in ((9, 21, -1), (15, 15, 1), (21, 9, -1), (12, 18, 1), (24, 7, 1)):
        z.polygon([(x, y), (x + 8 * s, y - 5 * s), (x + 3 * s, y + 3 * s)], fill=(214, 78, 66))
        z.polygon([(x, y), (x + 6 * s, y - 4 * s), (x + 3 * s, y + 1 * s)], fill=(250, 140, 124))
    return im

def sweeping_edge():
    im = neu(); z = d(im)
    for i, (r, farbe) in enumerate(((14, (255, 255, 255)), (11, (215, 225, 245)), (8, (150, 165, 200)))):
        z.arc([16 - r, 16 - r, 16 + r, 16 + r], start=120, end=300, fill=farbe, width=3 - i // 2)
    z.polygon([(6, 6), (12, 8), (8, 12)], fill=(255, 255, 255))
    return im

def fire_aspect():
    im = vanilla("diamond_sword", versatz=(2, 3))
    flamme(im, 8, 15, 17)                                                 # Flamme oben links auf dem Ruecken
    return im

def knockback():
    """Druckwelle, mittig, ohne Einschlagzeichen (Luis 10.09.2026)."""
    im = neu(); z = d(im)
    for r, w, farbe in ((7, 5, (215, 245, 255)), (13, 4, (150, 220, 255)), (19, 3, (100, 180, 235))):
        z.arc([4 - r, 16 - r, 4 + r, 16 + r], start=298, end=62, fill=farbe, width=w)
    return im

def punch():
    im = neu(); z = d(im)
    for i, x in enumerate((2, 12)):
        z.polygon([(x, 8), (x + 10, 16), (x, 24), (x + 4, 16)], fill=(150, 220, 255) if i else (100, 175, 225))
    z.polygon([(22, 8), (32, 16), (22, 24), (26, 16)], fill=(210, 245, 255))
    return im

def silk_touch():
    """Der Block bleibt heil: Steinwuerfel mit Kristallen darin."""
    im = neu(); z = d(im)
    z.rectangle([4, 6, 27, 27], fill=(118, 122, 132))
    z.rectangle([4, 6, 27, 9], fill=(158, 162, 172))
    z.rectangle([4, 24, 27, 27], fill=(92, 96, 106))
    for cx, cy, r in ((11, 14, 4), (21, 12, 3), (18, 21, 4)):
        z.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(120, 230, 255))
        z.polygon([(cx, cy - r + 1), (cx + r - 1, cy), (cx, cy)], fill=(220, 250, 255))
    z.rectangle([4, 6, 27, 27], outline=(70, 74, 84), width=1)
    return im

def flame():
    im = vanilla("bow", versatz=(2, 3))
    flamme(im, 8, 15, 17)
    return im

def infinity():
    im = neu(); z = d(im)
    for cx in (11, 21):
        z.ellipse([cx - 8, 8, cx + 8, 24], outline=(150, 110, 235), width=5)
        z.ellipse([cx - 7, 9, cx + 7, 23], outline=(206, 176, 255), width=2)
    z.ellipse([13, 12, 19, 20], fill=(0, 0, 0, 0))
    z.line([13, 12, 19, 20], fill=(150, 110, 235), width=5)
    z.line([13, 20, 19, 12], fill=(150, 110, 235), width=5)
    return im

def mending():
    im = neu(); z = d(im)
    z.rectangle([13, 4, 19, 28], fill=(60, 190, 110))
    z.rectangle([4, 13, 28, 19], fill=(60, 190, 110))
    z.rectangle([14, 5, 18, 27], fill=(140, 240, 175))
    z.rectangle([5, 14, 27, 18], fill=(140, 240, 175))
    for p in ((7, 7), (25, 8), (24, 25)):
        z.rectangle([p[0], p[1], p[0] + 2, p[1] + 2], fill=(220, 255, 235))
    return im

# Schluessel wie in rp_build.ENCH
SYMBOL = {
    "sharpness": sharpness, "protection": protection, "efficiency": efficiency, "power": power,
    "feather_falling": feather_falling, "fortune": fortune, "looting": looting,
    "unbreaking": unbreaking, "thorns": thorns, "sweeping_edge": sweeping_edge,
    "fire_aspect": fire_aspect, "knockback": knockback, "punch": punch,
    "silk_touch": silk_touch, "flame": flame, "infinity": infinity, "mending": mending,
}

def einlegen():
    """Der gruene Einlegeslot: Pfeil nach unten in den Slot."""
    im = neu(); z = d(im)
    z.rectangle([13, 3, 19, 17], fill=(196, 245, 186))
    z.polygon([(8, 15), (24, 15), (16, 27)], fill=(226, 255, 216))
    z.polygon([(11, 17), (21, 17), (16, 24)], fill=(150, 220, 140))
    return im
