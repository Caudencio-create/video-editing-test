# Testlauf 03.11.2026: Können aus den 126 GB Ads entstehen?

Aufgabe von Luciano: Mit dem am 02.11. heruntergeladenen Material (Brandlift / Holistic House)
und der Quellendatei `00_VIDEO-UEBERSICHT_Kontext.md` geeignete Videos transkribieren, ein
Ad-Format wählen, zusammenschneiden, am Ende eine fertige Ad.

## Ergebnis in einem Satz

Konzept, Zitat-Auswahl, Rezept und die komplette Schnitt-Strecke sind fertig und getestet. Die
fertige Ad aus echtem Material entsteht in einem Lauf auf Lucianos Rechner, denn die Cloud-Sitzung
kommt technisch nicht an die Videodateien heran.

## Was geklappt hat

| Schritt | Ergebnis |
|---|---|
| Material und Kontext finden | Drive-Ordner „Video-Assets Ausbildung (Stand 2026-11-02)“: 443 Dateien, 361 Videos, Übersicht, Katalog (CSV), Ranking mit 30 Ad-Ideen |
| Transkripte | Für alle 17 Frankfurt- und 13 Oberursel-Testimonials lagen fertige Transkripte im Drive („AA Fach-Coach Testimonial Transkripte.docx“). Alle 41 Abschnitte gelesen und nach sechs Einwänden ausgewertet |
| Ad-Format | Einwand-Hook + 3 echte Stimmen + Endcard „Kostenloses Beratungsgespräch“ (Ranking-Position E12) |
| Zitate | Christine Reimer → Christina Brückner → Ute Völker, alle wörtlich gegen das Transkript geprüft |
| Regelwerk | eigenes Prüfskript aus dem HH-Regelwerk; Hooks, Untertitel, Namen, Endcard, Anzeigentext: **0 Treffer** |
| Schnitt-Strecke | Transkribieren mit Wort-Zeitstempeln, Zitat finden, Füllwörter schneiden, Reframe aufs Gesicht, Lautstärke angleichen, Untertitel, Hook, Namen, Endcard, Export |
| Technik-Test (künstliches Material) | 2 Formate in 33 s gerendert; −14,1 LUFS; H.264 High, yuv420p, AAC 48 kHz; Texte in den Sicherheitszonen (per Vorschaubild geprüft) |
| Zitat-Suche an echten Texten | Mit den echten Transkripttexten (künstliche Zeitstempel): 100 % / 94 % / 100 % Übereinstimmung, Sprünge und „äh“-Schnitte richtig gesetzt |

## Warum dieses Format (und nicht Voice-over)

1. **Echte Menschen schlagen KI**: Laut Datenlage von Holistic House gewinnt die echte Person.
   Voice-over über B-Roll wäre Stufe 4 (Neuproduktion), und Ulis Stimme darf ohne seine
   schriftliche Freigabe nicht geklont werden.
2. **Diversität für Meta (Andromeda)**: Im Direkt-Funnel laufen bisher nur Statics, bei den Videos
   fast nur Uli als sprechender Kopf. Drei Teilnehmerinnen sind ein neuer Bildtyp.
3. **Einwand ist der größte Hebel im Direkt-Funnel** (Ranking, Abschnitt B). „Kein medizinischer
   Hintergrund“ passt zu einer Ausbildung mit „Fach-“ im Namen, und Christine Reimer spricht den
   Einwand fast wörtlich aus.
4. **Zielgruppe**: 82,5 % Frauen, Median 57. Ute (65) und Christina (51) liegen in diesem Bereich.
5. **Frisch und unverbraucht**: Frankfurt 07/2026 ist das neueste Material und noch nie in einer Ad gelaufen.

Ablauf (ca. 38–44 s + 3,5 s Endcard):

| Zeit | Bild | Text |
|---|---|---|
| 0–3 s | Christine Reimer | Hook (3 Varianten zum Testen) |
| 0–13 s | Christine Reimer | „Da werden bestimmt nur ganz tolle Leute genommen und Heilpraktiker und Ärzte, aber doch nicht ich. Ich habe ja nicht so viel Ahnung vom Gesundheitswesen, aber ich habe es dann trotzdem gemacht.“ |
| 13–29 s | Christina Brückner | „Als ich mit der Ausbildung angefangen habe, muss ich ehrlich sagen, war ich überfordert. … Und ich merke einfach jetzt während der Ausbildung, die ist in so gut verdaubaren Portionen für mich gestückelt, dass ich das unglaublich gut ergreifen kann.“ |
| 29–37 s | Ute Völker | „Mein Name ist Ute. Ich bin 65 Jahre alt, verkaufe Küchen und Hausgeräte. … Es ist leichter, wie man denkt.“ |
| letzte 3,5 s | letztes Bild eingefroren, weich | Endcard: Ayurveda Fach-Coach Ausbildung · mit Dr. Ulrich Bauhofer · Kostenloses Beratungsgespräch |

Hook-Varianten: H1 „Ohne medizinischen Hintergrund?“ · H2 „Weder Ärztin noch Heilpraktikerin?“ ·
H3 „Braucht man dafür ein Medizinstudium?“

## Was nicht ging, und warum

| Hindernis | Ursache | Folge |
|---|---|---|
| Videodateien laden | Google-Drive-Konnektor liefert höchstens 10 MB je Datei; das kleinste Video hat 21 MB. `drive.usercontent.google.com`, `drive.google.com` und `docs.google.com` sind im Netzwerk der Cloud-Umgebung gesperrt | keine echte Ad in dieser Sitzung |
| Freigabe-Link als Umweg | bewusst nicht genutzt: hätte Testimonials echter Personen öffentlich gemacht, und die Freigabe lässt sich mit den vorhandenen Werkzeugen nicht wieder entfernen | – |
| Make.com als Umweg | Free-Tarif, höchstens 5 MB je Datei | – |
| Whisper-Modell laden | `huggingface.co` gesperrt | Transkription am echten Ton nicht getestet (auf Lucianos Rechner lief faster-whisper im August bereits) |
| Landingpage lesen | `holistic-world.de` gesperrt | Anzeigentext und Endcard vor Freigabe gegen die LP lesen |

## Nicht geprüft (ehrlich)

- Wie sauber die Schnitte an echten Wortgrenzen klingen (Whisper-Zeitstempel sind auf etwa
  0,1 s genau; die Strecke gibt Luft zu, Prüfliste in `ANLEITUNG-LOKAL.md`).
- Gesichtserkennung an echten Gesichtern (am Testbild greift die Rückfallebene: Bildmitte).
- Ob das hochskalierte 9:16 aus 1080p-Quellen scharf genug wirkt (Zuschnitt 608 px breit → 1080 px;
  dafür wird leicht nachgeschärft; die 4:5-Fassung ist deutlich schärfer).
- Freigabe der drei Teilnehmerinnen für bezahlte Werbung.

## Nächster Schritt

Auf Lucianos Rechner: `docs/ANLEITUNG-LOKAL.md`, Abschnitte 1–4. Geschätzt 15–25 Minuten
Rechenzeit (Transkription von ca. 14 min Interviewmaterial, danach 6 Videos rendern).
