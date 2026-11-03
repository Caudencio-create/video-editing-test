"""Gemeinsame Hilfen für alle Werkzeuge: ffmpeg finden, Videos vermessen, Texte vergleichbar machen.

Läuft unter Windows und Linux. ffmpeg wird so gesucht:
1. Umgebungsvariable FFMPEG (voller Pfad zur ffmpeg.exe), ffprobe daneben
2. ffmpeg im Suchpfad (PATH)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHRIFTEN = REPO / "vorlagen" / "schriften"
ARBEIT = REPO / "arbeitsordner"          # Zwischenstände, nie im Repository
AUSGABE = REPO / "ausgabe"               # fertige Ads, nie im Repository

# Füllwörter, die im Schnitt entfernt und in Untertiteln weggelassen werden
FUELLWOERTER = {"äh", "ähm", "ähh", "äähm", "ehm", "öhm", "hm", "hmm", "mhm", "mmh", "ah", "eh"}


def _programm(name: str) -> str:
    umgebung = os.environ.get("FFMPEG")
    if umgebung:
        pfad = Path(umgebung)
        if name == "ffprobe":
            pfad = pfad.with_name(pfad.name.replace("ffmpeg", "ffprobe"))
        if pfad.is_file():
            return str(pfad)
    gefunden = shutil.which(name)
    if not gefunden:
        sys.exit(f"{name} nicht gefunden. Installieren (Windows: winget install Gyan.FFmpeg) "
                 f"oder Umgebungsvariable FFMPEG auf die ffmpeg.exe setzen.")
    return gefunden


def ffmpeg() -> str:
    return _programm("ffmpeg")


def ffprobe() -> str:
    return _programm("ffprobe")


def lauf(befehl: list[str], pruefen: bool = True) -> subprocess.CompletedProcess:
    ergebnis = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if pruefen and ergebnis.returncode != 0:
        letzte = "\n".join(ergebnis.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"Befehl fehlgeschlagen ({Path(befehl[0]).name}):\n{letzte}")
    return ergebnis


def vermessen(pfad: Path) -> dict:
    """Breite, Höhe, Bildrate, Dauer und Drehung eines Videos."""
    roh = lauf([ffprobe(), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(pfad)]).stdout
    daten = json.loads(roh)
    video = next((s for s in daten["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError(f"Keine Videospur: {pfad}")
    zaehler, nenner = (video.get("avg_frame_rate") or "25/1").split("/")
    fps = float(zaehler) / float(nenner) if float(nenner) else 25.0
    drehung = 0
    for seitendaten in video.get("side_data_list", []) or []:
        if "rotation" in seitendaten:
            drehung = int(seitendaten["rotation"])
    if "rotate" in video.get("tags", {}):
        drehung = int(video["tags"]["rotate"])
    breite, hoehe = int(video["width"]), int(video["height"])
    if abs(drehung) in (90, 270):
        breite, hoehe = hoehe, breite
    return {
        "breite": breite,
        "hoehe": hoehe,
        "fps": round(fps, 3),
        "dauer": float(daten["format"].get("duration", 0)),
        "hat_ton": any(s["codec_type"] == "audio" for s in daten["streams"]),
    }


def normalisieren(wort: str) -> str:
    """Wort für den Vergleich: klein, ohne Satzzeichen, Umlaute bleiben."""
    wort = unicodedata.normalize("NFC", wort.lower())
    wort = wort.replace("ß", "ss")
    return re.sub(r"[^\wäöü]", "", wort)


def woerter_aus_text(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def zeit(sekunden: float) -> str:
    minuten, rest = divmod(max(0.0, sekunden), 60)
    return f"{int(minuten)}:{rest:05.2f}"


def transkript_pfad(video: Path, transkriptordner: Path) -> Path:
    return transkriptordner / f"{video.stem}.json"
