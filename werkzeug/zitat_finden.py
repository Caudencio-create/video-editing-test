"""Schritt 2 – ein Zitat im Video finden und schnittfertig machen.

Man gibt den Wortlaut eines Zitats an (zum Beispiel aus einem vorhandenen Transkript-Dokument).
Ein „…“ im Zitat markiert einen bewussten Sprung zu einer späteren Stelle derselben Person.
Das Werkzeug sucht die Stelle im Wort-Transkript, liefert Start und Ende in Sekunden und plant
die Feinschnitte:
- Füllwörter („ähm“, „äh“) und Wörter, die im Zitat bewusst fehlen, werden herausgeschnitten,
- lange Pausen (> 0,6 s) werden auf 0,2 s gekürzt,
- jedes Wort des Zitats bekommt eine Zeit, damit die Untertitel exakt sitzen.

Aufruf zum Ausprobieren:
    python werkzeug/zitat_finden.py arbeitsordner/transkripte/<name>.json "Wortlaut des Zitats"
"""

from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import FUELLWOERTER, normalisieren, woerter_aus_text, zeit  # noqa: E402

VORLAUF = 0.12        # so viel Luft vor dem ersten Wort
NACHLAUF = 0.30       # so viel Luft nach dem letzten Wort
SCHNITT_LUFT = 0.05   # Luft an jedem Feinschnitt
MIN_SCHNITT = 0.18    # kürzere Lücken lohnen keinen Schnitt (sonst springt das Bild unnötig)
MAX_PAUSE = 0.60      # längere Pausen werden gekürzt
REST_PAUSE = 0.20     # auf diese Länge


def _woerter(transkript: dict) -> list[dict]:
    liste = []
    for segment in transkript["segmente"]:
        for w in segment["woerter"]:
            n = normalisieren(w["w"])
            if n:
                liste.append({**w, "n": n})
    return liste


def _bestes_fenster(zitat_n: list[str], woerter: list[dict], ab: int = 0) -> tuple[int, int, float]:
    """Sucht den Ausschnitt des Transkripts (ab Wort Nr. „ab“), der dem Zitat am ähnlichsten ist."""
    laenge = len(zitat_n)
    zitat_menge = set(zitat_n)
    bestes = (0, 0, 0.0)
    for start in range(ab, len(woerter)):
        for l in range(max(1, int(laenge * 0.8)), int(laenge * 1.7) + 2):
            ende = start + l
            if ende > len(woerter):
                break
            fenster = [w["n"] for w in woerter[start:ende]]
            if len(zitat_menge & set(fenster)) < 0.4 * len(zitat_menge):
                continue
            wert = SequenceMatcher(None, zitat_n, fenster, autojunk=False).ratio()
            if wert > bestes[2]:
                bestes = (start, ende, wert)
    return bestes


def finde_zitat(transkript: dict, zitat: str) -> dict:
    """Zitat finden. „…“ im Zitat markiert einen bewussten Sprung zu einer späteren Stelle derselben Person."""
    woerter = _woerter(transkript)
    stuecke = [st.strip() for st in zitat.replace("...", "…").split("…") if st.strip()]
    ergebnisse, ab = [], 0
    for stueck in stuecke:
        try:
            ergebnis = _finde_stueck(woerter, stueck, ab)
        except ValueError:
            ergebnis = _finde_stueck(woerter, stueck, 0)   # notfalls auch weiter vorn suchen
        ergebnisse.append(ergebnis)
        ab = ergebnis["ende_index"]
    return {
        "von": ergebnisse[0]["von"],
        "bis": ergebnisse[-1]["bis"],
        "uebereinstimmung": min(e["uebereinstimmung"] for e in ergebnisse),
        "teile": [t for e in ergebnisse for t in e["teile"]],
        "woerter": [w for e in ergebnisse for w in e["woerter"]],
        "gefunden": " … ".join(e["gefunden"] for e in ergebnisse),
        "geschnitten": " | ".join(e["geschnitten"] for e in ergebnisse if e["geschnitten"]),
    }


def _finde_stueck(woerter: list[dict], zitat: str, ab: int) -> dict:
    anzeige = woerter_aus_text(zitat)                      # Wörter, wie sie im Untertitel stehen
    zitat_n = [normalisieren(w) for w in anzeige]
    paare = [(w, n) for w, n in zip(anzeige, zitat_n) if n and n not in FUELLWOERTER]
    anzeige = [w for w, _ in paare]
    zitat_n = [n for _, n in paare]
    if not zitat_n:
        raise ValueError("Zitat ist leer.")

    start, ende, wert = _bestes_fenster(zitat_n, woerter, ab)
    if wert < 0.5:
        raise ValueError(f"Zitat nicht sicher gefunden (Übereinstimmung {wert:.0%}). Wortlaut prüfen.")
    fenster = woerter[start:ende]

    # Zuordnung Zitat-Wort -> Transkript-Wort; überzählige Transkript-Wörter merken
    zuordnung: dict[int, tuple[float, float]] = {}
    ueberzaehlig: set[int] = set()
    matcher = SequenceMatcher(None, zitat_n, [w["n"] for w in fenster], autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                zuordnung[i1 + k] = (fenster[j1 + k]["von"], fenster[j1 + k]["bis"])
        elif tag == "replace":       # anders erkannt, aber gesprochen: Zeiten anteilig verteilen
            von, bis = fenster[j1]["von"], fenster[j2 - 1]["bis"]
            schritt = (bis - von) / (i2 - i1)
            for k in range(i2 - i1):
                zuordnung[i1 + k] = (von + k * schritt, von + (k + 1) * schritt)
        elif tag == "insert":        # im Video gesagt, im Zitat nicht: Füllwort oder bewusst weggelassen
            ueberzaehlig.update(range(j1, j2))

    # Zitat-Wörter ohne Zuordnung zwischen die Nachbarn legen
    for i in range(len(zitat_n)):
        if i not in zuordnung:
            vorher = max((k for k in zuordnung if k < i), default=None)
            nachher = min((k for k in zuordnung if k > i), default=None)
            von = zuordnung[vorher][1] if vorher is not None else fenster[0]["von"]
            bis = zuordnung[nachher][0] if nachher is not None else von + 0.3
            zuordnung[i] = (von, max(von + 0.05, bis))

    behalten = [k for k in range(len(fenster)) if k not in ueberzaehlig]
    erstes, letztes = behalten[0], behalten[-1]

    # Teile bilden: Schnitt bei überzähligen Wörtern und langen Pausen
    teile: list[list[float]] = []
    anfang = max(0.0, fenster[erstes]["von"] - VORLAUF)
    vorheriges = erstes
    for k in range(erstes + 1, letztes + 1):
        if k in ueberzaehlig:
            continue
        luecke_von = fenster[vorheriges]["bis"]
        luecke_bis = fenster[k]["von"]
        geschnittene = any(j in ueberzaehlig for j in range(vorheriges + 1, k))
        if geschnittene and luecke_bis - luecke_von >= MIN_SCHNITT:
            teile.append([anfang, luecke_von + SCHNITT_LUFT])
            anfang = luecke_bis - SCHNITT_LUFT
        elif luecke_bis - luecke_von > MAX_PAUSE:
            teile.append([anfang, luecke_von + REST_PAUSE / 2])
            anfang = luecke_bis - REST_PAUSE / 2
        vorheriges = k
    schluss = fenster[letztes]["bis"] + NACHLAUF
    naechstes = start + letztes + 1
    if naechstes < len(woerter):                     # nicht in das nächste Wort hineinschneiden
        schluss = min(schluss, woerter[naechstes]["von"] - 0.03)
    teile.append([anfang, max(schluss, fenster[letztes]["bis"] + 0.05)])

    return {
        "von": round(teile[0][0], 3),
        "bis": round(teile[-1][1], 3),
        "uebereinstimmung": round(wert, 3),
        "teile": [[round(a, 3), round(b, 3)] for a, b in teile],
        "woerter": [{"w": w, "von": round(zuordnung[i][0], 3), "bis": round(zuordnung[i][1], 3)}
                    for i, w in enumerate(anzeige)],
        "gefunden": " ".join(w["w"] for w in fenster[erstes:letztes + 1]),
        "geschnitten": " ".join(fenster[k]["w"] for k in sorted(ueberzaehlig) if erstes < k < letztes),
        "ende_index": start + letztes + 1,
    }


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    transkript = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ergebnis = finde_zitat(transkript, sys.argv[2])
    dauer = sum(b - a for a, b in ergebnis["teile"])
    print(f"Gefunden ({ergebnis['uebereinstimmung']:.0%}): {zeit(ergebnis['von'])} – {zeit(ergebnis['bis'])}, "
          f"{len(ergebnis['teile'])} Teil(e), {dauer:.1f} s nach Feinschnitt")
    print(f"Im Video:     {ergebnis['gefunden']}")
    if ergebnis["geschnitten"]:
        print(f"Herausgeschnitten: {ergebnis['geschnitten']}")


if __name__ == "__main__":
    main()
