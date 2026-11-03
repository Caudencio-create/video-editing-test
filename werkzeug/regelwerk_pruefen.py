"""Prüft alle Texte einer Ad gegen das Regelwerk von Holistic House (HH_Regelwerk_Text_und_Creatives).

Geprüft wird alles, was im Bild steht: Hook, Untertitel (also auch die Zitate echter Personen),
Namenseinblendungen und Endcard. Meta liest eingebrannte Texte maschinell – ein Wort wie
„Krankheit“ im Untertitel kann die Anzeige auch dann sperren lassen, wenn es eine Teilnehmerin sagt.

Die Liste ist aus dem Regelwerk abgeleitet (Stand 03.11.2026). Neue Regeln dort, dann hier ergänzen.

Aufruf:  python werkzeug/regelwerk_pruefen.py rezepte/<rezept>.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# (Muster, Grund) – Muster als regulärer Ausdruck, Groß-/Kleinschreibung egal
REGELN: list[tuple[str, str]] = [
    (r"\bdr\.?\s*med\b", "„Dr. med.“ nicht in Meta-Ads (Regelwerk 2/3)"),
    (r"gesundheitssystem", "„Gesundheitssystem“ in Meta-Ads vermeiden (Regelwerk 2)"),
    (r"\bsystem\b", "bares „System“ unklar (Regelwerk 1/2)"),
    (r"symptom", "Meta-Triggerwort „Symptom“ (Regelwerk 2)"),
    (r"krankheit|erkrank", "Meta-Triggerwort „Krankheit/Erkrankung“ (Regelwerk 2)"),
    (r"diagnos", "Meta-Triggerwort „Diagnose“ (Regelwerk 2)"),
    (r"befund", "diagnostischer Beiklang „Befund“ (Regelwerk 2)"),
    (r"\bwirk(t|ung|sam)", "Health-Claim-Risiko „Wirkung/wirkt“ (Regelwerk 1)"),
    (r"\bheil(t|en|ung|methode|versprechen)", "Heilversprechen (Regelwerk 1)"),
    (r"gesundheit entsteht", "„Gesundheit entsteht“ (Regelwerk 1)"),
    (r"gesundheit (neu )?(denken|einordnen|fördern)", "Gesundheit als bearbeitetes Objekt (Regelwerk 2)"),
    (r"vorbeug", "„Vorbeugung“ → „Prävention“ (Briefing)"),
    (r"reparier", "„reparieren“ vermeiden (Regelwerk 7, Kohärenz-Liste)"),
    (r"gesundheitszustand|gesundheitliche verfassung", "diagnostischer Beiklang (Regelwerk 1)"),
    (r"\bpraxis\b|\bpatient", "Praxis-/Patientenbezug (Regelwerk 3/4)"),
    (r"therapie|ärztliche behandlung|\bkur\b", "„Therapie/Kur“ → „Kurs/Programm“ (Regelwerk 3)"),
    (r"\bvon dr\.", "„von Dr.“ → „mit Dr.“ (Regelwerk 3)"),
    (r"nicht (nur )?\w+(,)? sondern", "KI-Dualismus „nicht X, sondern Y“ (Regelwerk 5) – im Zitat erlaubt, prüfen"),
    (r"\b(beste|bester|bestes|einzig|führend|größte|älteste)\w*", "Superlativ (Regelwerk 5)"),
    (r"verdien|einkommen|\beuro\b|€|eigene[rn]? chef|selbstständig machen|karriere",
     "Verdienst-/Karriereversprechen (Meta „Economic Opportunity“, Regelwerk 2)"),
    (r"\blive\b|\b\d{1,2}\.\s?\d{1,2}\.|\buhr\b|webinar|online-seminar",
     "Datum/Live/Webinar im Evergreen-Direkt-Funnel unpassend"),
    (r"kaputt", "„kaputtgehen“ (Regelwerk 1)"),
]


def texte_aus_rezept(rezept: dict) -> list[tuple[str, str]]:
    texte = []
    hook = rezept.get("hook", {})
    for nr, text in enumerate(hook.get("varianten") or [hook.get("text", "")], 1):
        if text:
            texte.append((f"Hook {nr}", text))
    for nr, clip in enumerate(rezept.get("clips", []), 1):
        for feld in ("zitat", "untertitel", "name", "zusatz"):
            if clip.get(feld):
                texte.append((f"Clip {nr} {feld}", clip[feld]))
    for feld, wert in rezept.get("endcard", {}).items():
        if isinstance(wert, str) and feld not in ("schrift",):
            texte.append((f"Endcard {feld}", wert))
    return texte


def pruefen(texte: list[tuple[str, str]], funnel: str = "evergreen") -> list[str]:
    treffer = []
    for ort, text in texte:
        for muster, grund in REGELN:
            if funnel != "evergreen" and "Evergreen" in grund:
                continue
            for m in re.finditer(muster, text, flags=re.IGNORECASE):
                treffer.append(f"{ort}: „{m.group(0)}“ – {grund}\n      im Text: {text}")
    return treffer


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    rezept = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    treffer = pruefen(texte_aus_rezept(rezept), rezept.get("funnel", "evergreen"))
    if treffer:
        print(f"{len(treffer)} Treffer:")
        for t in treffer:
            print(" -", t)
        sys.exit(1)
    print("Regelwerk-Prüfung: 0 Treffer.")


if __name__ == "__main__":
    main()
