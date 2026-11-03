"""Technik-Test ohne echtes Material: erzeugt drei künstliche „Interview“-Clips samt Wort-Transkript
und ein passendes Rezept. Damit lässt sich die ganze Strecke (Zitat finden, Feinschnitt, Reframe,
Lautstärke, Untertitel, Hook, Namen, Endcard, Export) prüfen, ohne ein einziges Kundenvideo.

Die Clips zeigen ein Testbild mit der Aufschrift „TESTMATERIAL“ und haben Pieptöne statt Sprache –
sie sind ausdrücklich keine Ad, sondern nur ein Funktionstest.

Aufruf:
    python werkzeug/testmaterial.py
    python werkzeug/ad_bauen.py arbeitsordner/test/TEST_rezept.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ARBEIT, ffmpeg, lauf  # noqa: E402

ORDNER = ARBEIT / "test"

# (Dateiname, gesprochener Text mit Füllwörtern, Lautstärke, Personenposition x)
CLIPS = [
    ("Testperson A.mp4",
     "Also ähm ich hatte vorher überhaupt keinen fachlichen Hintergrund. Und ähm trotzdem habe ich "
     "jeden Schritt gut verstanden, weil alles ruhig und klar erklärt wurde. Das war für mich wichtig.",
     0.08, 0.35),
    ("Testperson B.mp4",
     "Ich war mir am Anfang unsicher, ob ich das neben dem Beruf schaffe. ähm Aber die Einteilung "
     "hat wirklich gut gepasst, auch mit Familie.",
     0.45, 0.62),
    ("Testperson C.mp4",
     "Heute weiß ich, dass es die richtige Entscheidung war. Ich würde es jederzeit wieder machen.",
     0.2, 0.5),
]


def zeitplan(text: str) -> list[dict]:
    """Künstliche Wortzeiten: 0,32 s je Wort, Füllwörter länger, nach Satzende eine lange Pause."""
    woerter, t = [], 0.6
    for wort in text.split():
        if wort.lower().strip(".,") in {"ähm", "äh"}:
            t += 0.25
            woerter.append({"w": wort, "von": round(t, 3), "bis": round(t + 0.55, 3), "p": 0.9})
            t += 0.55 + 0.3
            continue
        dauer = 0.18 + 0.03 * len(wort)
        woerter.append({"w": wort, "von": round(t, 3), "bis": round(t + dauer, 3), "p": 0.95})
        t += dauer + 0.07
        if wort.endswith("."):
            t += 1.1          # lange Pause, soll gekürzt werden
    return woerter


def main() -> None:
    ORDNER.mkdir(parents=True, exist_ok=True)
    (ORDNER / "transkripte").mkdir(exist_ok=True)
    rezept_clips = []
    for nr, (datei, text, lautstaerke, person_x) in enumerate(CLIPS, 1):
        woerter = zeitplan(text)
        dauer = woerter[-1]["bis"] + 1.5
        # Ton: Piepen genau dort, wo „gesprochen“ wird
        bedingung = "+".join(f"between(t,{w['von']},{w['bis']})" for w in woerter)
        ton = f"aevalsrc='{lautstaerke}*sin(2*PI*(180+40*{nr})*t)*gt({bedingung},0)':s=48000:d={dauer:.2f}"
        x = int(1920 * person_x)
        bild = (f"testsrc2=s=1920x1080:r=25:d={dauer:.2f},"
                f"drawbox=x={x - 170}:y=220:w=340:h=420:color=0xE8C9A8@1:t=fill,"
                f"drawbox=x={x - 260}:y=640:w=520:h=440:color=0x073D3D@1:t=fill,"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='TESTMATERIAL {nr} – kein echtes Video':fontsize=56:fontcolor=white:"
                f"box=1:boxcolor=black@0.6:boxborderw=12:x=(w-tw)/2:y=60,"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                f"text='%{{pts\\:hms}}':fontsize=44:fontcolor=white:box=1:boxcolor=black@0.6:x=40:y=h-90")
        ziel = ORDNER / datei
        lauf([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", bild, "-f", "lavfi", "-i", ton,
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-shortest", str(ziel)])
        transkript = {"datei": datei, "dauer": dauer, "modell": "kuenstlich",
                      "segmente": [{"von": woerter[0]["von"], "bis": woerter[-1]["bis"], "text": text,
                                    "woerter": woerter}]}
        (ORDNER / "transkripte" / f"{ziel.stem}.json").write_text(json.dumps(transkript, ensure_ascii=False,
                                                                              indent=1), encoding="utf-8")
        print(f"erzeugt: {ziel.name} ({dauer:.1f} s)")
        rezept_clips.append({"datei": datei, "name": f"Testperson {chr(64 + nr)}",
                             "zusatz": "Teilnehmerin der Ausbildung", "fokus": [person_x, 0.4]})

    rezept_clips[0]["zitat"] = ("ich hatte vorher überhaupt keinen fachlichen Hintergrund. Und trotzdem habe "
                                "ich jeden Schritt gut verstanden, weil alles ruhig und klar erklärt wurde.")
    rezept_clips[1]["zitat"] = "Aber die Einteilung hat wirklich gut gepasst, auch mit Familie."
    rezept_clips[2]["zitat"] = "Heute weiß ich, dass es die richtige Entscheidung war."
    rezept_clips[2].pop("fokus")      # dritter Clip: automatische Gesichtssuche (findet hier keins -> Mitte)
    rezept = {
        "id": "TEST", "name": "Technik-Test", "titel": "Funktionstest der Schnitt-Strecke",
        "funnel": "evergreen", "formate": ["9x16", "4x5"],
        "quellordner": str(ORDNER), "transkriptordner": str(ORDNER / "transkripte"),
        "hook": {"text": "Ohne fachlichen Hintergrund?", "dauer": 2.8},
        "clips": rezept_clips,
        "endcard": {"titel": "Ayurveda\nFach-Coach Ausbildung", "untertitel": "mit Dr. Ulrich Bauhofer",
                    "knopf": "Kostenloses Beratungsgespräch", "hinweis": "Jetzt unten auf „Mehr dazu“ tippen",
                    "dauer": 3.5},
    }
    (ORDNER / "TEST_rezept.json").write_text(json.dumps(rezept, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rezept: {ORDNER / 'TEST_rezept.json'}")


if __name__ == "__main__":
    main()
