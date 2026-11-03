# Anleitung für den Agenten auf Lucianos Rechner

Diese Datei ist für eine Claude-Sitzung, die **auf Lucianos Windows-Rechner** läuft (Claude Desktop
oder `claude` im Terminal). Dort liegt das Videomaterial bereits lokal, über Google Drive für
Desktop synchronisiert:

```
D:\Meine Ablage\1-UNTERNEHMEN\Externe Projekte\Brandlift\Projekte\Video-Assets Ausbildung (Stand 2026-11-02)
```

Luciano ist kein Entwickler. Du erledigst alles selbst und fragst ihn nur nach Inhalten
(welche Ad, welcher Hook gefällt), nie nach Technik.

## 1. Einmal einrichten (ca. 5 Minuten)

```powershell
cd C:\Users\User
git clone https://github.com/Caudencio-create/video-editing-test
cd video-editing-test
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
ffmpeg -version
```

Danach alle Befehle mit `.venv\Scripts\python.exe` statt `python` ausführen.

- **Kurzer Pfad**: Windows erlaubt hier höchstens 260 Zeichen pro Pfad (Langpfade sind aus). In einem
  tief verschachtelten Ordner scheitert schon `git clone`, später das Rendern
  (`arbeitsordner\render\…\schriften\…`). Deshalb direkt unter `C:\Users\User` klonen.
- **Eigene Umgebung (.venv)**: Auf diesem Rechner ist global OpenCV 5 installiert, dem die
  Gesichtserkennung fehlt (`CascadeClassifier`). Die `.venv` bringt OpenCV 4 mit, ohne andere
  Projekte zu stören. Ohne `uv`: `python -m venv .venv` und `.venv\Scripts\python.exe -m pip install -r requirements.txt`.

- Fehlt ffmpeg: `winget install Gyan.FFmpeg`, danach ein neues Terminal öffnen. Auf diesem Rechner
  lief im August schon eine Strecke mit ffmpeg und faster-whisper (Creative-Showcase,
  `03_transkript.py`). Ist ffmpeg dort unter einem festen Pfad installiert, die Umgebungsvariable
  `FFMPEG` auf die `ffmpeg.exe` setzen.
- Beim ersten Transkribieren lädt faster-whisper das Modell `large-v3-turbo` (ca. 1,6 GB) einmalig.

## 2. Funktionstest ohne Kundenmaterial (1 Minute)

```powershell
python werkzeug/testmaterial.py
python werkzeug/ad_bauen.py arbeitsordner/test/TEST_rezept.json
```

Ergebnis in `ausgabe/`: zwei Testvideos mit buntem Testbild. Läuft das, funktioniert die Technik.

## 3. Die Ad E12 bauen

```powershell
python werkzeug/ad_bauen.py rezepte/E12_3Stimmen-Hintergrund.json --nur-planen
```

Das transkribiert die drei benötigten Interviews (je 3–7 min Material, auf der CPU je ca. 2–5 min),
sucht die Zitate und schreibt `ausgabe/E12_3Stimmen-Hintergrund_Schnittliste.md`.
**Lies die Schnittliste**, bevor du renderst:

- Treffer je Clip mindestens 85 %. Darunter: Wortlaut im Rezept an das Transkript in
  `arbeitsordner/transkripte/<Name>.txt` angleichen. Das Transkript ist die Wahrheit, nicht das Rezept.
- Zeile „Im Video erkannt“ mit der Zeile „Untertitel“ vergleichen. Weicht ein Wort ab, das Rezept
  korrigieren. Untertitel müssen wiedergeben, was gesagt wird. Steht unter „Herausgeschnitten“ ein
  Wort, das kein Füllwort und kein Fehlstart ist (am 03.11.: „noch“ bei Christine Reimer), gehört
  es ins Zitat.
- Schnittkanten nicht blind übernehmen: Whisper setzt Wortgrenzen nur auf etwa 0,1 s genau und
  dehnt Wörter über Pausen. Am 03.11. mussten bei E12 elf von zwölf Kanten nachgesetzt werden
  (Silbenreste wie „-te“ von „konnte“, abgeschnittenes „kann“, Atemzug vor Utes „Mein Name“). Kanten am Pegel messen und als feste `teile` ins
  Rezept schreiben, **zusätzlich** zum `zitat` (dann kommen die Untertitel-Wörter weiter aus dem
  Transkript). Die Schnittliste zeigt den ursprünglichen Vorschlag zum Vergleich.

Dann rendern:

```powershell
python werkzeug/ad_bauen.py rezepte/E12_3Stimmen-Hintergrund.json
```

Ergebnis: 3 Hook-Varianten × 2 Formate = 6 Videos (`E12_3Stimmen-Hintergrund_H1_9x16.mp4` usw.)
plus je ein `_Vorschau.png`. Dauer auf einem normalen Rechner ca. 1–2 min pro Video.

## 4. Prüfen, bevor Luciano es sieht

Öffne jedes `_Vorschau.png` und sieh dir mindestens eine 9:16-Fassung ganz an. Prüfliste:

- [ ] Gesicht im Bild, nicht angeschnitten (sonst im Rezept beim Clip `"fokus": [x, y]` setzen,
      z. B. `[0.42, 0.35]` = Gesicht bei 42 % der Breite, 35 % der Höhe)
- [ ] Schnitte hörbar sauber: kein abgehacktes Wort, kein Atemgeräusch-Rest. Sonst im Rezept
      zusätzlich zum `zitat` feste `teile` angeben (Zeiten aus der Schnittliste, leicht verschieben)
- [ ] Ute: harter Schnitt nach „Hausgeräte.“, danach kein Wort mehr hörbar
- [ ] Untertitel = Gesprochenes, keine Tippfehler, Umlaute korrekt
- [ ] Hook und Namen gut lesbar, nichts in den unteren 35 % (9:16)
- [ ] Endcard: Text vollständig, Knopf nicht abgeschnitten
- [ ] Lautstärke der drei Frauen ähnlich

## 5. Ablegen

Fertige Videos nach Google Drive, Ordner (anlegen, falls nicht vorhanden):

```
Brandlift › Projekte › Evergreen Webinar (Ayurveda) › Video Batch 1
```

Dateinamen unverändert lassen (ID vorne, so erkennt die wiederkehrende Aufgabe den Status).
In `01_RANKING_Video-Ads_Live-und-Evergreen.md` bei E12 den Status auf „geschnitten, wartet auf
Freigabe“ setzen.

## 6. Vor dem Hochladen in Meta (Luciano bzw. Kunde)

- Freigabe der drei Teilnehmerinnen für Werbung bestätigen (die Interviews wurden für Marketing
  gedreht, eine schriftliche Einwilligung sollte bei Holistic House liegen).
- Anzeigentext aus dem Rezept (`meta_texte`) gegen die Landingpage lesen.
- Anzeigenname: `3010_HH_AYV-Direkt_E12_3Stimmen-Hintergrund_V1` (H2, H3 entsprechend `_V2`, `_V3`).
