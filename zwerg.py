"""Der Zwerg: 3D-Modell (Minecraft-JSON-Modell aus Quadern) plus Textur-Atlas, gerendert als item_display.
16 Einheiten = 1 Block, der Zwerg ist genau einen Block hoch. Blickt nach Norden (-z), der Quell steht vor ihm.
Zwei Teile: Koerper (Kopf, Helm, Bart, Rumpf, Beine, linker Arm) und Axt-Arm (eigene Entity, schwingt).
Aufruf als Skript: schreibt eine Vorschau nach /tmp/zwerg.png."""
from PIL import Image, ImageDraw
import math

# Farben
HAUT = (222, 176, 138); HAUT_D = (196, 148, 112)
BART = (178, 74, 32); BART_H = (208, 104, 52)
TUNIKA = (46, 74, 128); TUNIKA_D = (34, 56, 100)
GURT = (74, 46, 22); SCHNALLE = (214, 166, 44)
HOSE = (70, 48, 30); STIEFEL = (36, 24, 14)
HELM = (150, 156, 164); HELM_D = (104, 110, 118); HELM_H = (200, 206, 214)
AUGE = (250, 250, 250); PUPILLE = (30, 30, 60)
HOLZ = (110, 72, 34); EISEN = (176, 180, 188); EISEN_D = (120, 124, 132)

def flach(farbe):
    return lambda w, h: [[farbe] * w for _ in range(h)]

def gesicht(w, h):
    # Kopf vorn (20x14 px): Helm deckt Zeile 0-4, Augen 5-6, Nase 7-9, Bart ab 11
    g = [[HAUT] * w for _ in range(h)]
    for y in range(11, h):
        for x in range(w):
            g[y][x] = BART if (x + y) % 3 else BART_H
    for ex in (4, 13):
        for dx in range(3):
            g[5][ex + dx] = AUGE; g[6][ex + dx] = AUGE
        g[5][ex + 1] = PUPILLE; g[6][ex + 1] = PUPILLE
        for x in range(ex - 1, ex + 4):
            g[4][x] = HAUT_D                      # Brauenschatten
    for y in range(7, 10):
        for x in (9, 10):
            g[y][x] = HAUT_D
    for x in range(8, 12):
        g[10][x] = BART_H                         # Schnurrbart
    return g

def bart_vorn(w, h):
    return [[BART_H if (x + y) % 3 == 0 else BART for x in range(w)] for y in range(h)]

def rumpf_vorn(w, h):
    g = [[TUNIKA] * w for _ in range(h)]
    for x in range(w):
        g[h - 3][x] = GURT; g[h - 4][x] = GURT
    for x in range(w // 2 - 1, w // 2 + 1):
        g[h - 3][x] = SCHNALLE; g[h - 4][x] = SCHNALLE
    return g

def helm_seite(w, h):
    g = [[HELM] * w for _ in range(h)]
    for x in range(w):
        g[h - 1][x] = HELM_D; g[h - 2][x] = HELM_D
        g[0][x] = HELM_H
    return g

# Quader: (name, from, to, {face: painter}), Einheiten 0..16, y nach oben, Zwerg blickt nach -z
def q(name, f, t, faces):
    return {"name": name, "from": f, "to": t, "faces": faces}

def alle(farbe, **sonder):
    d = {k: flach(farbe) for k in ("north", "south", "east", "west", "up", "down")}
    d.update(sonder); return d

KOERPER = [
    q("bein_r", [4, 0, 6], [7, 3, 10], alle(HOSE, down=flach(STIEFEL), north=flach(STIEFEL))),
    q("bein_l", [9, 0, 6], [12, 3, 10], alle(HOSE, down=flach(STIEFEL), north=flach(STIEFEL))),
    q("rumpf", [3, 3, 5], [13, 9, 11], alle(TUNIKA, north=rumpf_vorn, up=flach(TUNIKA_D), down=flach(TUNIKA_D))),
    q("arm_l", [13, 4, 6], [16, 9, 9], alle(TUNIKA, down=flach(HAUT), up=flach(TUNIKA_D))),
    q("kopf", [3, 9, 4], [13, 16, 11], alle(HAUT, north=gesicht, up=flach(HAUT_D))),
    q("bart", [4, 5, 3], [12, 10.5, 4], alle(BART, north=bart_vorn)),
    q("helm", [2.5, 14, 3.5], [13.5, 16.5, 11.5], alle(HELM, north=helm_seite, south=helm_seite, east=helm_seite, west=helm_seite, up=flach(HELM_H))),
    q("helmrand", [2, 13.5, 3], [14, 14.2, 12], alle(HELM_D)),
]
# Axt-Arm: Schulter-Drehpunkt bei (1.5, 9, 7.5). Axt liegt auf der Schulter, Blatt oben.
ARM = [
    q("arm_r", [0, 4, 6], [3, 9, 9], alle(TUNIKA, down=flach(HAUT), up=flach(TUNIKA_D))),
    q("hand", [0, 3, 6], [3, 4.5, 9], alle(HAUT)),
    q("stiel", [1, 2, 2], [2, 15, 3], alle(HOLZ)),
    q("blatt", [-2.5, 10, 1.5], [1, 15, 3.5], alle(EISEN, north=flach(EISEN_D), south=flach(EISEN_D), up=flach(EISEN_D))),
    q("blatt2", [2, 10, 1.5], [5, 15, 3.5], alle(EISEN, north=flach(EISEN_D), south=flach(EISEN_D), up=flach(EISEN_D))),
]
SCHULTER = (1.5, 9.0, 7.5)

# ---------------------------------------------------------------------------
# Textur-Atlas und Modell-JSON
# ---------------------------------------------------------------------------
PX = 2       # Texturpixel je Einheit

def face_size(e, face):
    f, t = e["from"], e["to"]
    w = {"north": t[0] - f[0], "south": t[0] - f[0], "east": t[2] - f[2], "west": t[2] - f[2], "up": t[0] - f[0], "down": t[0] - f[0]}[face]
    h = {"north": t[1] - f[1], "south": t[1] - f[1], "east": t[1] - f[1], "west": t[1] - f[1], "up": t[2] - f[2], "down": t[2] - f[2]}[face]
    return w, h

def atlas_und_modell(elemente, texname, size=128):
    """Malt jede Flaeche in einen Atlas und gibt (Bild, Modell-Dict) zurueck."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = im.load()
    cx, cy, zeilenhoehe = 0, 0, 0
    model_elems = []
    for e in elemente:
        faces = {}
        for face, painter in e["faces"].items():
            w, h = face_size(e, face)
            pw, ph = max(1, int(round(w * PX))), max(1, int(round(h * PX)))
            if cx + pw > size:
                cx, cy, zeilenhoehe = 0, cy + zeilenhoehe + 1, 0
            grid = painter(pw, ph)
            for y in range(ph):
                for x in range(pw):
                    px[cx + x, cy + y] = tuple(grid[y][x]) + (255,)
            s = 16 / size
            faces[face] = {"uv": [cx * s, cy * s, (cx + pw) * s, (cy + ph) * s], "texture": "#t"}
            cx += pw + 1; zeilenhoehe = max(zeilenhoehe, ph)
        model_elems.append({"from": e["from"], "to": e["to"], "faces": faces})
    model = {"textures": {"t": texname, "particle": texname}, "elements": model_elems,
             "display": {"fixed": {"scale": [1, 1, 1]}}}
    return im, model

# ---------------------------------------------------------------------------
# Vorschau-Renderer (Isometrie, Flaechen mit Textur-Zellen, Painter-Algorithmus)
# ---------------------------------------------------------------------------
def render(elemente_liste, yaw=-35, pitch=22, scale=14, arm_winkel=0.0):
    """elemente_liste: Liste von (Elemente, Drehung um SCHULTER in Grad um x-Achse)."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    def proj(x, y, z):
        # Welt: x rechts, y hoch, z nach Sueden (Betrachter steht im Nordwesten und schaut auf Gesicht und linke Seite)
        x -= 8; z -= 8
        xr = x * cy - z * sy; zr = x * sy + z * cy
        yr = y * cp - zr * sp; zd = y * sp + zr * cp
        return xr, yr, zd
    def rot_arm(p, ang):
        if not ang: return p
        px_, py, pz = p; ax, ay, az = SCHULTER
        a = math.radians(ang); c, s = math.cos(a), math.sin(a)
        y, z = py - ay, pz - az
        return (px_, ay + y * c - z * s, az + y * s + z * c)
    quads = []
    for elemente, ang in elemente_liste:
        for e in elemente:
            f, t = e["from"], e["to"]
            for face, painter in e["faces"].items():
                w, h = face_size(e, face)
                pw, ph = max(1, int(round(w * PX))), max(1, int(round(h * PX)))
                grid = painter(pw, ph)
                # Flaechen-Ecken (Ursprung oben links im Texturraum) und Richtung u, v in Welt
                if face == "north":   o, du, dv = (t[0], t[1], f[2]), (-w, 0, 0), (0, -h, 0)
                elif face == "south": o, du, dv = (f[0], t[1], t[2]), (w, 0, 0), (0, -h, 0)
                elif face == "west":  o, du, dv = (f[0], t[1], f[2]), (0, 0, w), (0, -h, 0)
                elif face == "east":  o, du, dv = (t[0], t[1], t[2]), (0, 0, -w), (0, -h, 0)
                elif face == "up":    o, du, dv = (f[0], t[1], f[2]), (w, 0, 0), (0, 0, h)
                else:                 o, du, dv = (f[0], f[1], t[2]), (w, 0, 0), (0, 0, -h)
                shade = {"up": 1.0, "north": 0.86, "south": 0.86, "west": 0.7, "east": 0.7, "down": 0.5}[face]
                for gy in range(ph):
                    for gx in range(pw):
                        pts = []
                        for (a, b) in ((gx, gy), (gx + 1, gy), (gx + 1, gy + 1), (gx, gy + 1)):
                            uu, vv = a / pw, b / ph
                            p = (o[0] + du[0] * uu + dv[0] * vv, o[1] + du[1] * uu + dv[1] * vv, o[2] + du[2] * uu + dv[2] * vv)
                            pts.append(proj(*rot_arm(p, ang)))
                        depth = sum(p[2] for p in pts) / 4
                        col = tuple(int(c * shade) for c in grid[gy][gx])
                        quads.append((depth, [(p[0], p[1]) for p in pts], col))
    quads.sort(key=lambda qd: -qd[0])   # weit weg zuerst
    W, H = 22 * scale, 24 * scale
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _, pts, col in quads:
        poly = [(W / 2 + x * scale, H * 0.78 - y * scale) for x, y in pts]
        d.polygon(poly, fill=col + (255,))
    return im

if __name__ == "__main__":
    a = render([(KOERPER, 0), (ARM, 0)])
    b = render([(KOERPER, 0), (ARM, -70)])
    c = render([(KOERPER, 0), (ARM, 0)], yaw=35)
    out = Image.new("RGBA", (a.width * 3 + 40, a.height + 20), (52, 46, 60, 255))
    # Boden-Block als Bezug (1 Block = 16 Einheiten)
    for i, im in enumerate((a, b, c)):
        out.alpha_composite(im, (10 + i * (a.width + 10), 10))
    out.save("/tmp/zwerg.png")
    atlas, model = atlas_und_modell(KOERPER, "nachtwache:entity/dwarf")
    atlas.save("/tmp/zwerg_atlas.png")
    print("ok", len(model["elements"]))

# ---------------------------------------------------------------------------
# Bogi: derselbe Zwergenkoerper in Gruen mit Lederkappe, in der Hand ein Bogen
# ---------------------------------------------------------------------------
TUNIKA_B = (46, 96, 56); TUNIKA_BD = (32, 70, 40)
KAPPE = (96, 66, 36); KAPPE_D = (68, 46, 24); KAPPE_H = (128, 92, 52)
SEHNE = (238, 238, 230)

def rumpf_vorn_b(w, h):
    g = [[TUNIKA_B] * w for _ in range(h)]
    for x in range(w):
        g[h - 3][x] = GURT; g[h - 4][x] = GURT
    for x in range(w // 2 - 1, w // 2 + 1):
        g[h - 3][x] = SCHNALLE; g[h - 4][x] = SCHNALLE
    return g

def kappe_seite(w, h):
    g = [[KAPPE] * w for _ in range(h)]
    for x in range(w):
        g[h - 1][x] = KAPPE_D; g[h - 2][x] = KAPPE_D
        g[0][x] = KAPPE_H
    return g

KOERPER_BOGI = [
    q("bein_r", [4, 0, 6], [7, 3, 10], alle(HOSE, down=flach(STIEFEL), north=flach(STIEFEL))),
    q("bein_l", [9, 0, 6], [12, 3, 10], alle(HOSE, down=flach(STIEFEL), north=flach(STIEFEL))),
    q("rumpf", [3, 3, 5], [13, 9, 11], alle(TUNIKA_B, north=rumpf_vorn_b, up=flach(TUNIKA_BD), down=flach(TUNIKA_BD))),
    q("arm_l", [13, 4, 6], [16, 9, 9], alle(TUNIKA_B, down=flach(HAUT), up=flach(TUNIKA_BD))),
    q("kopf", [3, 9, 4], [13, 16, 11], alle(HAUT, north=gesicht, up=flach(HAUT_D))),
    q("bart", [4, 5, 3], [12, 10.5, 4], alle(BART, north=bart_vorn)),
    q("kappe", [2.5, 14, 3.5], [13.5, 16.5, 11.5], alle(KAPPE, north=kappe_seite, south=kappe_seite, east=kappe_seite, west=kappe_seite, up=flach(KAPPE_H))),
    q("kappenrand", [2, 13.5, 3], [14, 14.2, 12], alle(KAPPE_D)),
]
# Arm mit Bogen: der Bogen steht senkrecht vor dem Zwerg, die Sehne zeigt zu ihm
ARM_BOGEN = [
    q("arm_r", [0, 4, 6], [3, 9, 9], alle(TUNIKA_B, down=flach(HAUT), up=flach(TUNIKA_BD))),
    q("hand", [0, 6.5, 4.5], [3, 8, 6.5], alle(HAUT)),
    q("griff", [0, 6, 4.5], [2, 10, 5.5], alle(HOLZ)),
    q("wurf_o", [0, 10, 4.2], [2, 13, 5.2], alle(HOLZ)),
    q("wurf_u", [0, 3, 4.2], [2, 6, 5.2], alle(HOLZ)),
    q("spitze_o", [0, 13, 3.4], [2, 14.5, 4.4], alle(HOLZ)),
    q("spitze_u", [0, 1.5, 3.4], [2, 3, 4.4], alle(HOLZ)),
    q("sehne", [0.8, 1.8, 5.9], [1.2, 14.2, 6.2], alle(SEHNE)),
]
