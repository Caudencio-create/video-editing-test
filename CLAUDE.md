# Hier anfangen

Dieses Repository schneidet Meta-Video-Ads aus vorhandenem Rohmaterial. Auftraggeber ist
Luciano Saraiva (Hive-Agentur, Performance Marketing). Erster Kunde: Brandlift / Holistic House,
Produkt „Ayurveda Fach-Coach Ausbildung“ mit Dr. Ulrich Bauhofer.

**Zuerst lesen:** `README.md` (Überblick), dann `docs/ANLEITUNG-LOKAL.md` (Ablauf auf dem Rechner
mit dem Material), dann `docs/ERGEBNIS-TESTLAUF-2026-11-03.md` (was schon geklärt ist).

## Stehende Regeln

1. **Alles auf Deutsch**: Antworten, Commits, Pull Requests, Kommentare, Dokumentation.
   Ausnahme: Bezeichner im Code und Werte, die fremde Systeme ausgeben.
2. **Luciano ist kein Entwickler.** Er entscheidet Inhalte (welche Ad, welcher Hook), nie Technik.
   Varianten zeigen statt beschreiben (Vorschaubilder, HTML-Übersicht). Fragen gebündelt, mit Auswahl.
3. **Kundenmaterial nie ins Repository**, nie in öffentliche Links, nie zu fremden Diensten ohne
   Lucianos Zustimmung. Transkription läuft lokal (faster-whisper). `arbeitsordner/` und `ausgabe/`
   sind in `.gitignore`.
4. **Regelwerk von Holistic House ist Pflicht** für jeden Text im Bild und im Anzeigentext
   (`werkzeug/regelwerk_pruefen.py`, läuft beim Rendern automatisch). Original:
   Google Doc „HH_Regelwerk_Text_und_Creatives“ (Link im ClickUp-Doc „Quellen-Register Evergreen“).
   Neue Regeln dort, dann im Prüfskript ergänzen.
5. **Heilmittelwerbegesetz**: keine Zitate über Heilung, Krankheiten oder Beschwerden (auch wenn
   eine Teilnehmerin es selbst sagt). Keine Systemkritik. Keine Verdienst- oder Karriereversprechen.
6. **Zitate wörtlich.** Nur Füllwörter und Fehlstarts dürfen weg. „…“ markiert einen Sprung
   innerhalb derselben Person. Den Zusammenhang nie verfälschen.
7. **Personen korrekt bezeichnen**: Frankfurt 07/2026 = „Teilnehmerin“, nicht „Absolventin“
   (die Ausbildung lief zum Drehzeitpunkt noch).
8. **Evergreen-Direkt-Funnel**: kein Datum, kein „live“, kein Webinar. Ziel ist das kostenlose
   Beratungsgespräch, Meta-Knopf „Mehr dazu“.
9. **Messen statt behaupten.** „Fertig“ heißt: gerendert, Vorschaubild angesehen, Schnittliste
   gelesen, Lautheit −14 LUFS. Was nicht geprüft werden konnte, ehrlich so sagen.
10. **Immer den Link mitgeben.** Alles, was Luciano ansehen oder prüfen soll (Video, Ordner, Datei,
    Liste), bekommt genau an dieser Stelle einen klickbaren Link, bei Drive-Dateien den Drive-Link
    (über den Drive-Konnektor nach dem Dateinamen suchen; frisch abgelegte Dateien tauchen dort erst
    nach ein paar Minuten auf). Keine Ordnerpfade zum Selbstsuchen. Kurz und ohne Fachbegriffe
    erklären, so dass jemand folgen kann, der nicht dabei war.

## Grenze der Cloud-Sitzung (Stand 03.11.2026)

Das Videomaterial (126 GB) liegt in Lucianos Google Drive und lokal auf seinem Rechner. Aus einer
Cloud-Sitzung (claude.ai/code) kommt man nicht heran: Der Drive-Konnektor liefert höchstens 10 MB
je Datei, und die Download-Adressen von Google sind im Netzwerk der Cloud-Umgebung gesperrt.
Rendern mit echtem Material geht deshalb nur auf seinem Rechner (Claude Desktop oder Remote Control).
Konzept, Zitat-Auswahl (aus den Transkript-Dokumenten im Drive), Rezepte und Code gehen überall.

## Namen und Ablage

- Dateien: ID vorne, z. B. `E12_3Stimmen-Hintergrund_H1_9x16.mp4` (IDs aus
  `01_RANKING_Video-Ads_Live-und-Evergreen.md` im Drive-Ordner „Video-Assets Ausbildung“).
- Ablage fertiger Ads: Drive › Brandlift › Projekte › „Evergreen Webinar (Ayurveda)“ bzw.
  „Live Webinar (Ayurveda)“ › „Video Batch <Nr>“.
- Meta-Anzeigenname Evergreen: `3010_HH_AYV-Direkt_<ID>_<Kurzname>_V<Nr>`.
