"""Schritt 1 – Ton transkribieren, mit Zeitstempel für jedes einzelne Wort.

Läuft komplett lokal (faster-whisper auf der CPU). Das Videomaterial verlässt den Rechner nicht.
Wort-Zeitstempel sind nötig, damit wir ein Zitat sekundengenau finden, Füllwörter herausschneiden
und Untertitel exakt zum Gesprochenen setzen können.

Aufruf:
    python werkzeug/transkribieren.py <video oder ordner> [...] [--modell large-v3-turbo]

Ergebnis je Video in arbeitsordner/transkripte/:
    <name>.json  (Segmente + Wörter mit von/bis in Sekunden)
    <name>.txt   (lesbar, mit Zeitmarken)
Bereits vorhandene Transkripte werden übersprungen (--neu erzwingt eine neue Fassung).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ARBEIT, ffmpeg, lauf, transkript_pfad, vermessen, zeit  # noqa: E402

VIDEO_ENDUNGEN = {".mp4", ".mov", ".m4v", ".mkv", ".mxf", ".avi"}


def videos_sammeln(eingaben: list[str]) -> list[Path]:
    liste: list[Path] = []
    for eingabe in eingaben:
        pfad = Path(eingabe)
        if pfad.is_dir():
            liste += sorted(p for p in pfad.rglob("*") if p.suffix.lower() in VIDEO_ENDUNGEN)
        elif pfad.is_file():
            liste.append(pfad)
        else:
            print(f"Nicht gefunden: {pfad}")
    return liste


def audio_ziehen(video: Path, ziel: Path) -> None:
    lauf([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
          "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(ziel)])


def transkribieren(modell, video: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "ton.wav"
        audio_ziehen(video, wav)
        segmente, info = modell.transcribe(
            str(wav), language="de", beam_size=5, vad_filter=True,
            word_timestamps=True, condition_on_previous_text=False,
        )
        liste = []
        for s in segmente:
            woerter = [{"w": w.word.strip(), "von": round(w.start, 3), "bis": round(w.end, 3),
                        "p": round(w.probability, 3)} for w in (s.words or []) if w.word.strip()]
            liste.append({"von": round(s.start, 3), "bis": round(s.end, 3), "text": s.text.strip(),
                          "woerter": woerter})
    return {"sprache": info.language, "sprache_sicherheit": round(info.language_probability, 3),
            "segmente": liste}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("eingaben", nargs="+", help="Videodateien oder Ordner")
    parser.add_argument("--modell", default="large-v3-turbo",
                        help="Whisper-Modell (Standard large-v3-turbo; schneller: small)")
    parser.add_argument("--ausgabe", default=str(ARBEIT / "transkripte"))
    parser.add_argument("--neu", action="store_true", help="vorhandene Transkripte überschreiben")
    args = parser.parse_args()

    ziel = Path(args.ausgabe)
    ziel.mkdir(parents=True, exist_ok=True)
    videos = videos_sammeln(args.eingaben)
    offen = [v for v in videos if args.neu or not transkript_pfad(v, ziel).is_file()]
    print(f"{len(videos)} Videos gefunden, {len(offen)} zu transkribieren.")
    if not offen:
        return

    from faster_whisper import WhisperModel  # erst hier laden, damit --help ohne Modell geht

    print(f"Modell {args.modell} wird geladen (beim ersten Mal Download, ca. 1,6 GB)…")
    modell = WhisperModel(args.modell, device="cpu", compute_type="int8")

    for nr, video in enumerate(offen, 1):
        technik = vermessen(video)
        print(f"[{nr}/{len(offen)}] {video.name} ({zeit(technik['dauer'])})", flush=True)
        if not technik["hat_ton"]:
            print("   keine Tonspur, übersprungen")
            continue
        start = time.time()
        ergebnis = transkribieren(modell, video)
        ergebnis.update({"datei": video.name, "pfad": str(video), "dauer": technik["dauer"],
                         "breite": technik["breite"], "hoehe": technik["hoehe"], "fps": technik["fps"],
                         "modell": args.modell})
        json_pfad = transkript_pfad(video, ziel)
        json_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")
        zeilen = [f"[{zeit(s['von'])}] {s['text']}" for s in ergebnis["segmente"]]
        json_pfad.with_suffix(".txt").write_text("\n".join(zeilen) or "(kein Text)", encoding="utf-8")
        woerter = sum(len(s["woerter"]) for s in ergebnis["segmente"])
        print(f"   {woerter} Wörter in {time.time() - start:.0f} s -> {json_pfad.name}")


if __name__ == "__main__":
    main()
