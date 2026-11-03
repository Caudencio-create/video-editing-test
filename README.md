# Video-Ads aus Rohmaterial – Schnitt-Strecke

Aus langen Interviews und Rohaufnahmen automatisch fertige Meta-Video-Ads schneiden:
transkribieren, das richtige Zitat finden, sauber schneiden, Hochformat, Untertitel, Hook,
Namen, Endcard. Erster Einsatz: Brandlift / Holistic House, Ayurveda Fach-Coach Ausbildung.

## So funktioniert es – in einem Bild

```
 Rezept (welche Zitate, welcher Hook)          ← das ist die kreative Entscheidung
        │
        ▼
 1 Transkribieren   jedes Wort mit Zeitstempel, lokal auf dem Rechner (faster-whisper)
 2 Zitat finden     Stelle im Video suchen, „ähm“ und lange Pausen herausschneiden
 3 Bild             auf das Gesicht zuschneiden (9:16 und 4:5), bei Feinschnitten leicht zoomen
 4 Ton              Lautstärke je Person angleichen, Gesamtmischung −14 LUFS
 5 Text             Untertitel, Hook, Namen in den Sicherheitszonen von Meta einbrennen
 6 Endcard          über dem eingefrorenen, weichgezeichneten letzten Bild
 7 Prüfen           Regelwerk-Check, Vorschaubild, Schnittliste
        │
        ▼
 fertige MP4s: je Hook-Variante 9:16 (Reels/Stories) und 4:5 (Feed)
```

## Stand 03.11.2026

| | |
|---|---|
| Schnitt-Strecke | fertig, technisch getestet mit Testmaterial (siehe `docs/ERGEBNIS-TESTLAUF-2026-11-03.md`) |
| Erste Ad | Rezept `rezepte/E12_3Stimmen-Hintergrund.json`: Einwand „kein medizinischer Hintergrund“, drei Teilnehmerinnen aus Frankfurt (07/2026), drei Hook-Varianten |
| Offen | Rendern mit dem echten Material. Das geht nur auf Lucianos Rechner, weil die Videos (126 GB) dort liegen. Anleitung: `docs/ANLEITUNG-LOKAL.md` |

## Befehle

```bash
python -m pip install -r requirements.txt
python werkzeug/testmaterial.py                                  # Funktionstest ohne Kundenmaterial
python werkzeug/ad_bauen.py arbeitsordner/test/TEST_rezept.json
python werkzeug/ad_bauen.py rezepte/E12_3Stimmen-Hintergrund.json --nur-planen   # nur Zitate suchen
python werkzeug/ad_bauen.py rezepte/E12_3Stimmen-Hintergrund.json                # rendern
python werkzeug/regelwerk_pruefen.py rezepte/E12_3Stimmen-Hintergrund.json       # nur Texte prüfen
```

## Ordner

| Ordner | Inhalt |
|---|---|
| `werkzeug/` | die Werkzeuge (Python, ffmpeg) |
| `rezepte/` | eine Datei je Ad: Zitate, Hook-Varianten, Endcard, Anzeigentexte |
| `vorlagen/schriften/` | Schrift Figtree (freie Lizenz OFL); Farben und Schrift aus der Kohärenz-Übersicht vom 27.10., gegen die Landingpage noch zu prüfen |
| `docs/` | Anleitung für den Rechner mit dem Material, Testbericht |
| `arbeitsordner/`, `ausgabe/` | entstehen beim Arbeiten, **nie im Repository** (Kundenmaterial) |
