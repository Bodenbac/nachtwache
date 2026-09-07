# Nachtwache (Minecraft-Datapack, Java 1.21.11)

One Block, Nachtwellen, der Sammler. Konzept siehe „Inselkette Konzept" im Vault (v3.2). Dieses Paket enthält das fertige Datapack (`out/nachtwache.zip`), das Ressourcenpaket für die Spieler (`out/nachtwache-rp.zip`), den Generator (`build.py`, ruft `rp_build.py` mit auf; `icons.py` und `zwerg.py` liefern Grafiken und 3D-Modell) und die Tabellen, aus denen das Datapack gebaut wird (`tabellen/`).

## Installation auf dem Forge-Server

1. Neue Welt anlegen. In `server.properties` diese Zeilen setzen (Welt darf noch nicht existieren, sonst vorher den Weltordner umbenennen):

```
level-name=nachtwache
level-type=minecraft\:flat
generator-settings={"layers":[],"biome":"minecraft:the_void"}
difficulty=hard
gamemode=survival
spawn-protection=0
pause-when-empty-seconds=-1
```

2. Server einmal starten, bis „Done" im Log steht, dann stoppen.
3. `out/nachtwache.zip` nach `nachtwache/datapacks/` kopieren (als Zip oder entpackt, beides geht).
4. Server starten. Beim ersten Laden baut das Datapack Startinsel, Stand, Gegnerinsel und setzt die Spielregeln. Im Chat erscheint „Die Welt ist gebaut".
5. Spieler beitreten. `/trigger nw.hilfe` zeigt die Kurzhilfe im Spiel.

Wer den Server als Op hat, kann die Admin-Funktionen nutzen (unten). Für das Spielen selbst sind keine Rechte nötig.

## Was im Spiel wie funktioniert

Der Quell in der Mitte hat sieben Stufen mit eigener Farbe: Grau (Tuff), Grün, Blau, Lila (Amethyst), Gelb, Orange, Schwarz. Die Stufe steigt nach 500, dann 1000, 1500, 2000, 3000 und 4000 weiteren Abbauten, die Seitenleiste zeigt Stufe, Balken und Zähler. Jede Stufe bringt mehr Splitter je Abbau (1 bis 8) und bessere Drops. Mit der Hand dauert ein Abbau mehrere Sekunden, mit Spitzhacke gut eine. Der Ertrag landet direkt im Inventar. Setzlinge und Weizensamen sind selten (je 1 Prozent), Essen ist knapp und beim Sammler teuer. Am Tresen des Sammlers stehen eine Truhe (KAUFEN) und ein Fass (VERKAUFEN). In der Truhe liegen die Angebote der aktuellen Phase mit Preis in der Beschreibung: Klick auf ein Symbol kauft ein Stück, Shift-Klick den Stapel (64, bei Werkzeug 1), reicht das Konto nicht, passiert nichts. Über 53 Angebote gibt es eine zweite Seite (Pfeil unten rechts). Ins Fass gelegte Ware (Shift-Klick aus dem Inventar) wird sofort zum Preis aus preise.csv verkauft, alles andere (Werkzeug, Rüstung) bleibt liegen und kann wieder mitgenommen werden. Geld ist rein virtuell (Konto in der Seitenleiste), es gibt keine Münzgegenstände. Sets kommen als gefüllte Truhe. Der Trichter rechts vom Stand ist die Lieferrampe (80 Prozent, jede Sekunde abgerechnet). Eine Bossleiste zeigt am Tag, wie lange es noch bis zur Nacht dauert. Die Uhr läuft nur, solange jemand auf dem Server ist. Eisen, Kohle, Diamant (1000) und Verzauberungsbücher (5000 bis 10000) gibt es von Anfang an. Zwei eigene Gegenstände: die Collector Lantern (Seelenlaterne, 300) verlangsamt Gegner im Umkreis von 8 Blöcken, brennt drei Nächte und ist das Einzige, was auf der Straße stehen bleibt (bekommt tagsüber einen eigenen Stumpf). Der Bounty Contract (150, nur am Tag, einer zur Zeit) gilt für die kommende Nacht: doppeltes Kopfgeld, Welle 50 Prozent größer, solange er läuft steht ein Stern neben der Uhr und der Wellenleiste. Der Zwerg (10000) wird direkt neben den Quell gestellt (eine der acht Nachbarpositionen, freier Block) und schlägt alle 15 Sekunden zu: Coins aufs Konto, Drops in seinen Rucksack (Rechtsklick, 26 Felder), Stufenzähler und Mob-Chance wie beim Spieler. Im Rucksack liegt rechts unten das Upgrade-Symbol: herausnehmen kauft eine Sekunde mehr Tempo (250 Coins mal Stufe, zwölf Stufen bis 3 s). Abbauen (Hand oder Werkzeug) holt ihn samt Stufe ins Inventar, der Rucksackinhalt fällt heraus. Technik: Marker plus zwei item_displays (Körper, Axt-Arm aus `zwerg.py`), der Rucksack ist ein Fass mit `facing=down`, das das Ressourcenpaket unsichtbar macht.

Bei Sonnenuntergang (eigene Uhr, Tag 8 Minuten) erscheint die Straße und die Welle spawnt auf der Gegnerinsel. Die Nacht endet erst, wenn alle Gegner tot sind: Sind sie es, wird es sofort hell, sonst bleibt die Uhr ab 23000 stehen (nach etwa 12 Minuten), bis nichts mehr lebt. Betten funktionieren nur, wenn kein Gegner mehr lebt. Gegner, die vier Sekunden nicht vorankommen, graben den Block vor sich weg (Erde nach 2 s, Stein nach 5 s, Eisenblock nach 10 s, Obsidian nie). Wer in den Nebel fällt oder dem nächsten Spieler 20 Sekunden lang nicht näher kommt (Turm, Plattform, eingemauert), taucht direkt neben ihm wieder auf, auf seiner Ebene. Straße und Gegnerinsel lassen sich weder abbauen noch bebauen (werden laufend zurückgesetzt). Wellen: Nacht 1 bis 3 nur Zombies, ab 4 kleine Zombies und Husks, ab 7 Skelette und Spinnen, ab 11 Endermen (werden jede Sekunde auf den nächsten Spieler wütend gemacht), ab 15 Hexen und Witherskelette, ab 20 Brutes und Plünderer, ab 25 Ravager. Keine Creeper. Alle fünf Nächte ein Boss, Nacht 30 der Sammler selbst (Warden, ein Drittel Leben). Danach Statistik und auf Wunsch Endlosmodus.

## Ressourcenpaket (Client-Seite)

`out/nachtwache-rp.zip` (9 KB) gehört auf die Spieler-PCs, nicht auf den Server. Es bringt: die Münze als echtes Symbol (das Zeichen ● der Standardschrift wird durch eine Münzgrafik ersetzt, ohne Paket bleibt es ein Punkt), die sieben Quell-Stufen im Amethyst-Stil in ihrer Farbe (Tuff grau, Grün, Blau, Amethyst, Gelb, Orange, Schwarz), eigene Symbole für Watch Bell und Kits sowie Truhen- und Fassfenster in Dämmerungstönen (gilt für alle Truhen, nicht nur den Laden). Format 75 (1.21.11).

Einbauen, zwei Wege:

1. Von Hand: Zip nach `%appdata%\.minecraft\resourcepacks\` legen, im Spiel unter Optionen, Ressourcenpakete aktivieren. Auf jedem Spieler-PC einmal.
2. Automatisch: Zip irgendwo per HTTP erreichbar ablegen (direkter Download-Link) und in `server.properties` eintragen, dann lädt der Client es beim Beitreten selbst:

```
resource-pack=https://.../nachtwache-rp.zip
resource-pack-sha1=<Inhalt von out/nachtwache-rp.sha1>
require-resource-pack=true
resource-pack-prompt={"text":"Nightwatch needs its resource pack (coins, tiers, Collector)."}
```

Ohne Paket zeigen Watch Bell und Kits im Laden die lila-schwarze Fehlgrafik (die Gegenstände funktionieren trotzdem). Wer das nicht will, setzt in `build.py` `RESSOURCENPAKET = False` und baut neu. Bei jeder Änderung am Ressourcenpaket ändert sich die SHA1, dann den Wert in `server.properties` nachziehen (sonst lädt der Client die alte Fassung aus dem Cache).

Vorlagen in `vorlagen/` sind drei Originalgrafiken aus dem 1.21.11-Client (Amethystblock, Glocke, Truhenfenster), die `rp_build.py` umfärbt. Sie liegen nicht im Git (Mojang-Grafiken), `python3 vorlagen_holen.py` lädt sie einmalig aus dem offiziellen Client.

Auf GitHub liegt das Projekt unter `github.com/Bodenbac/nachtwache`, der Download-Link für die server.properties ist `https://github.com/Bodenbac/nachtwache/raw/main/out/nachtwache-rp.zip`.

## Anpassen

Alle Zahlen stehen in `tabellen/*.csv` (Ankaufspreise, Angebot, Quell-Pools, Wellen, Sprüche) oder oben in `build.py` im Abschnitt EINSTELLUNGEN (Phasengrenzen, Splitter pro Abbau, Uhr, Wellenformel, Bosse, Grabzeiten, Materialklassen). Danach:

```
python3 build.py
```

Das schreibt `out/nachtwache/`, `out/nachtwache.zip` und `out/nachtwache-rp.zip` neu (Pillow nötig: `pip install pillow`). Zip in den Datapack-Ordner kopieren, im Spiel `/reload`. Laufende Werte (Konto, Nacht, Phase) bleiben erhalten.

## Admin-Funktionen (nur als Op)

```
/function nachtwache:admin/zeit_nacht      es wird gleich Nacht
/function nachtwache:admin/zeit_tag        es wird gleich Tag
/function nachtwache:admin/welle_toeten    alle Gegner weg
/function nachtwache:admin/splitter {n:100}   Splitter gutschreiben
/function nachtwache:admin/phase {p:3}     Quellphase setzen
/function nachtwache:admin/neustart        alles auf null, Inseln neu gesetzt (eigene Bauten bleiben)
/trigger reset                             kompletter Neuanfang: fragt nach, dann innerhalb 60 s
/trigger yes                               ... bestätigen (geht nur mit Tag nw.admin, luisgamer2349 hat ihn automatisch, weitere per /tag <name> add nw.admin): Spielbereich (x -48..47, z -48..127, y 0..160) leer, Inventare, Enderkisten, XP, Coins, Nacht, Stufe auf null, Inseln neu. Nether und End bleiben.
```

## Getestet (06.09.2026, Vanilla-Server 1.21.11 mit Testbot)

Weltbau beim ersten Laden, Quell-Abbau mit Gutschrift und Magnet, Kaufen-Truhe (Klick und Shift-Klick), Verkaufsfass (nur Ware, Werkzeug bleibt liegen), Lieferrampe mit Restmenge, Nachtstart mit Straße und Welle (Nacht 1 = 6 Zombies), Gegner laufen über die Straße zum Spieler, Kopfgeld beim Tod eines Gegners, Tagesanbruch mit Straßenabbau und Glühen, Bettregel in beide Richtungen, Durchbruch durch eine Steinwand, alle sechs Bosse, Finale mit Sieg und Statistik, Todesabzug.

## Bekannte Grenzen

Die Kaufen-Truhe ist eine echte Truhe, die das Datapack jeden Tick überwacht: Ein genommenes Symbol wird verrechnet und sofort ersetzt. Wer ein Symbol in der Hand behält, verliert es beim nächsten Tick (es ist kein echter Gegenstand). Angebote der nächsten Phase erscheinen erst beim Phasenwechsel.

Der Warden im Finale behält seinen Fernangriff (lässt sich mit Bordmitteln nicht abschalten), dafür hat er nur ein Drittel Leben. Die Straße ist drei Blöcke breit statt einem, sonst fallen die Gegner zu oft herunter. Ist das Inventar beim Abbau am Quell voll, fällt der Ertrag vor die Füße statt zu warten. Gegner, die einen Spieler auf einem Turm nicht erreichen, graben den Turm an, kommen aber nicht hoch. Der Client sollte ebenfalls 1.21.11 sein, das Datapack ist bis Pack-Format 110 freigegeben, spätere Versionen können Befehle umbenennen.
