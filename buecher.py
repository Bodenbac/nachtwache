#!/usr/bin/env python3
"""
Eigene 16x16-Symbole fuer die Verzauberungsbuecher im Laden.

Grundlage ist das Verzauberungsbuch aus dem Spiel, eingefaerbt nach der Ausruestung, auf die die
Verzauberung wirkt (Schwert rot, Spitzhacke blau, Bogen gruen, Ruestung violett). In der Mitte sitzt
ein eigenes 5x5-Zeichen fuer die Faehigkeit, unten rechts ein Punkt je Stufe. So sieht man die
Kategorie am Farbton und die Verzauberung am Zeichen, und es bleibt auf den ersten Blick ein Buch.
Luis' Auswahl vom 09.09.2026 aus vier Entwuerfen.
"""
from pathlib import Path
from PIL import Image

V = Path(__file__).resolve().parent / "vorlagen"

def _buch():
    return Image.open(V / "enchanted_book.png").convert("RGBA").crop((0, 0, 16, 16))

# Ausruestung, auf die die Verzauberung wirkt -> Farbton des Buches
SCHWERT     = (255, 120, 120)
SPITZHACKE  = (120, 190, 255)
BOGEN       = (150, 255, 170)
RUESTUNG    = (200, 160, 255)

# ---------------------------------------------------------------- Zeichen (5x5, Mitte des Buches)
ZEICHEN = {
    "flamme":   (["..r..", ".rRr.", "rRYRr", "rRYRr", ".rrr."], {"r": (200, 60, 20), "R": (240, 130, 30), "Y": (255, 225, 120)}),
    "funke":    (["....W", "...Ww", "..Www", ".ww..", "ww..."], {"w": (150, 195, 235), "W": (255, 255, 255)}),
    "muenze":   ([".ggg.", "gGYGg", "gYGYg", "gGYGg", ".ggg."], {"g": (150, 110, 30), "G": (215, 175, 70), "Y": (255, 230, 140)}),
    "stoss":    (["..c..", "...c.", "ccccc", "...c.", "..c.."], {"c": (150, 220, 255)}),
    "doppelstoss":(["c.c..", ".c.c.", "..c.c", ".c.c.", "c.c.."], {"c": (150, 220, 255)}),
    "bogenhieb":([".sss.", "ss...", "s....", "ss...", ".sss."], {"s": (235, 240, 255)}),
    "tempo":    (["...tt", "..tt.", ".tttt", "..tt.", ".tt.."], {"t": (110, 200, 255)}),
    "edelstein":(["..e..", ".eEe.", "eEEEe", ".eEe.", "..e.."], {"e": (40, 150, 100), "E": (110, 245, 180)}),
    "seide":    ([".www.", "wWWWw", "wWWWw", "wWWWw", ".www."], {"w": (190, 195, 210), "W": (252, 252, 255)}),
    "amboss":   (["AAAAA", "AAAAA", "..a..", ".aaa.", "AAAAA"], {"a": (110, 116, 132), "A": (175, 182, 198)}),
    "plus":     (["..m..", "..m..", "mmmmm", "..m..", "..m.."], {"m": (110, 235, 140)}),
    "schild":   (["ppppp", "pPPPp", "pPPPp", ".pPp.", "..p.."], {"p": (60, 100, 190), "P": (145, 185, 250)}),
    "feder":    (["...ff", "..fFf", ".fFFf", "fFFf.", "ff..."], {"f": (185, 198, 222), "F": (255, 255, 255)}),
    "stern":    (["y.y.y", ".yYy.", "yYYYy", ".yYy.", "y.y.y"], {"y": (230, 150, 40), "Y": (255, 228, 130)}),
    "unendlich":([".....", "II.II", "I.I.I", "II.II", "....."], {"I": (218, 185, 255)}),
}
PLATTE = (24, 21, 30, 235)   # dunkle Platte hinter dem Zeichen

def symbol(farbton, zeichen, stufe):
    """Verzauberungsbuch im Farbton der Ausruestung, mittig das Zeichen, unten rechts die Stufenpunkte."""
    im = _buch()
    px = im.load()
    r, g, b = farbton
    for y in range(16):                          # Buch einfaerben, Helligkeit der Vorlage bleibt erhalten
        for x in range(16):
            c = px[x, y]
            if c[3]:
                m = min(1.0, (c[0] + c[1] + c[2]) / 3 / 255 * 1.45)   # Vorlage ist dunkel, sonst saeuft der Farbton ab
                px[x, y] = (int(r * m), int(g * m), int(b * m), c[3])
    for y in range(7):                           # Platte, damit das Zeichen auf jedem Farbton lesbar bleibt
        for x in range(7):
            if (x, y) in ((0, 0), (6, 0), (0, 6), (6, 6)):
                continue
            px[x + 5, y + 5] = PLATTE
    rows, P = ZEICHEN[zeichen]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if P.get(ch):
                px[x + 6, y + 6] = P[ch] + (255,)
    for n in range(stufe):                       # Stufenpunkte unten rechts, von rechts nach links
        x = 15 - n * 2
        if x < 6:
            break
        px[x, 13] = PLATTE
        px[x, 14] = (255, 255, 255, 255)
        px[x, 15] = (255, 255, 255, 255)
    return im

# Kurzname des Buches in angebot.csv -> (Farbton, Zeichen, Stufe fuer die Punkte)
BUCH_SYMBOLE = {
    "SHARPNESS_4": (SCHWERT, "funke", 4),          "SHARPNESS_5": (SCHWERT, "funke", 5),
    "FIRE_ASPECT_1": (SCHWERT, "flamme", 1),       "FIRE_ASPECT_2": (SCHWERT, "flamme", 2),
    "LOOTING_2": (SCHWERT, "muenze", 2),           "LOOTING_3": (SCHWERT, "muenze", 3),
    "KNOCKBACK_1": (SCHWERT, "stoss", 1),          "KNOCKBACK_2": (SCHWERT, "stoss", 2),
    "SWEEPING_EDGE_2": (SCHWERT, "bogenhieb", 2),  "SWEEPING_EDGE_3": (SCHWERT, "bogenhieb", 3),
    "EFFICIENCY_4": (SPITZHACKE, "tempo", 4),      "EFFICIENCY_5": (SPITZHACKE, "tempo", 5),
    "FORTUNE_2": (SPITZHACKE, "edelstein", 2),     "FORTUNE_3": (SPITZHACKE, "edelstein", 3),
    "SILK_TOUCH_1": (SPITZHACKE, "seide", 1),
    "UNBREAKING_2": (SPITZHACKE, "amboss", 2),     "UNBREAKING_3": (SPITZHACKE, "amboss", 3),
    "MENDING_1": (SPITZHACKE, "plus", 1),
    "PROTECTION_3": (RUESTUNG, "schild", 3),       "PROTECTION_4": (RUESTUNG, "schild", 4),
    "FEATHER_FALLING_3": (RUESTUNG, "feder", 3),   "FEATHER_FALLING_4": (RUESTUNG, "feder", 4),
    "POWER_4": (BOGEN, "stern", 4),                "POWER_5": (BOGEN, "stern", 5),
    "PUNCH_1": (BOGEN, "doppelstoss", 1),          "PUNCH_2": (BOGEN, "doppelstoss", 2),
    "FLAME_1": (BOGEN, "flamme", 1),
    "INFINITY_1": (BOGEN, "unendlich", 1),
}

def alle():
    return {k: symbol(*v) for k, v in BUCH_SYMBOLE.items()}
