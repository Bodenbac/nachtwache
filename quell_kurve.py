#!/usr/bin/env python3
"""Ertragskurve des Quells pruefen: was bringt ein Abbau je Stufe, und passt der Sprung?

Die Stufenkiste zaehlt bewusst NICHT mit (Luis 10.09.2026), sie ist ein Gluecksfall.
Zielkurve: Faktor 1,4 auf Stufe 2, danach je 0,1 mehr, der letzte Sprung auf 2,0.

    python quell_kurve.py            Kurve und Abweichung
    python quell_kurve.py 7          dazu die Posten der Stufe 7, groesste zuerst
"""
import csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ZIEL_FAKTOR = {2: 1.4, 3: 1.5, 4: 1.6, 5: 1.7, 6: 1.8, 7: 2.0}
SPLITTER = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 8}

def lies(name):
    p = HERE / "tabellen" / name
    return list(csv.DictReader(l for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")))

def phasen(s):
    if "-" in s:
        a, b = s.split("-")
        return range(int(a), int(b) + 1)
    return [int(s)]

def kurve():
    preis = {r["item"]: int(r["wert"]) for r in lies("preise_abgeleitet.csv")}
    rows = lies("quell.csv")
    aus = {}
    for st in range(1, 8):
        pool = [(r["item"], int(r["gewicht"]), int(r["min"]), int(r["max"])) for r in rows if st in phasen(r["phasen"])]
        ges = sum(g for _, g, _, _ in pool)
        posten = [(g / ges * preis.get(it, 0) * (mn + mx) / 2, it, g, preis.get(it, 0)) for it, g, mn, mx in pool]
        aus[st] = (SPLITTER[st] + sum(p[0] for p in posten), sorted(posten, reverse=True), ges)
    return aus

def main():
    k = kurve()
    ziel = {1: k[1][0]}
    for st in range(2, 8):
        ziel[st] = ziel[st - 1] * ZIEL_FAKTOR[st]
    print(f"{'Stufe':<6}{'ist':>8}{'soll':>8}{'fehlt':>8}{'Faktor':>8}{'Ziel':>7}{'Gewicht':>9}")
    for st in range(1, 8):
        ist, _, ges = k[st]
        fak = ist / k[st - 1][0] if st > 1 else None
        print(f"{st:<6}{ist:>8.1f}{ziel[st]:>8.1f}{ziel[st]-ist:>8.1f}"
              f"{(f'{fak:.2f}x' if fak else '-'):>8}{(f'{ZIEL_FAKTOR[st]:.1f}' if st > 1 else '-'):>7}{ges:>9}")
    if len(sys.argv) > 1:
        st = int(sys.argv[1])
        print(f"\nPosten der Stufe {st} (Beitrag je Abbau, groesste zuerst):")
        for beitrag, it, g, wert in k[st][1][:22]:
            print(f"  {beitrag:>6.2f}  {it:<24} Gewicht {g:>3}  Stueckwert {wert}")

if __name__ == "__main__":
    main()
