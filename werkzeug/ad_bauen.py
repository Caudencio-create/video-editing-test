"""Schritt 3 – aus einem Rezept eine fertige Video-Ad rendern (9:16 für Reels/Stories, 4:5 für den Feed).

Ein Rezept (rezepte/*.json) beschreibt die Ad: Hook-Text, die Clips (Datei + Wortlaut des Zitats
oder feste Zeiten), Namenseinblendungen und Endcard. Dieses Werkzeug erledigt den Rest:
  1. fehlende Transkripte erzeugen (lokal, siehe transkribieren.py),
  2. jedes Zitat im Video finden, Füllwörter und lange Pausen herausschneiden,
  3. Bildausschnitt auf das Gesicht setzen (automatisch, falls OpenCV installiert ist),
  4. bei Feinschnitten abwechselnd leicht heranzoomen, damit der Sprung nicht auffällt,
  5. Lautstärke je Person angleichen, Gesamtmischung auf -14 LUFS (Social-Media-Standard),
  6. Untertitel, Hook und Namen in den Sicherheitszonen von Meta einbrennen,
  7. Endcard über dem eingefrorenen, weichgezeichneten letzten Bild,
  8. Export H.264/AAC nach Meta-Vorgaben, dazu Vorschaubild und Schnittliste.

Aufruf:
    python werkzeug/ad_bauen.py rezepte/<rezept>.json [--formate 9x16 4x5] [--nur-planen]
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemeinsam import ARBEIT, AUSGABE, SCHRIFTEN, ffmpeg, lauf, transkript_pfad, vermessen, zeit  # noqa: E402
from regelwerk_pruefen import pruefen, texte_aus_rezept  # noqa: E402
from zitat_finden import finde_zitat  # noqa: E402

# Bildformate und Sicherheitszonen. Werte als Anteil der Bildhöhe.
# 9:16: Meta-Oberfläche verdeckt oben ca. 14 %, unten ca. 35 % (Profil, Text, Knopf).
# 4:5: Feed, unten ca. 8 % für Fortschrittsbalken/Ton-Symbol frei halten.
FORMATE = {
    "9x16": {"breite": 1080, "hoehe": 1920, "ut_unten": 0.37, "oben": 0.155, "ut_groesse": 0.035,
             "hook_groesse": 0.046, "name_groesse": 0.028, "karte_mitte": 0.42},
    "4x5": {"breite": 1080, "hoehe": 1350, "ut_unten": 0.085, "oben": 0.055, "ut_groesse": 0.043,
            "hook_groesse": 0.056, "name_groesse": 0.034, "karte_mitte": 0.50},
    "1x1": {"breite": 1080, "hoehe": 1080, "ut_unten": 0.08, "oben": 0.06, "ut_groesse": 0.050,
            "hook_groesse": 0.064, "name_groesse": 0.040, "karte_mitte": 0.50},
}
ZOOM_SPRUNG = 1.08          # Heranzoomen bei jedem zweiten Feinschnitt (mehr macht 1080p-Quellen weich)
ENDCARD_STANDARD = 3.5      # Sekunden
ZIEL_LUFS_CLIP = -16.0      # je Person vor der Gesamtmischung
STIL_STANDARD = {"schrift": "Figtree", "primaer": "#073d3d", "akzent": "#c9734d", "hell": "#fbf9f5",
                 "text_dunkel": "#22302f"}


# ---------------------------------------------------------------- Hilfen

def ass_farbe(hexwert: str, transparenz: int = 0) -> str:
    """#RRGGBB -> ASS &HAABBGGRR (Transparenz 0 = deckend, 255 = unsichtbar)."""
    r, g, b = hexwert[1:3], hexwert[3:5], hexwert[5:7]
    return f"&H{transparenz:02X}{b}{g}{r}".upper()


def ass_zeit(sekunden: float) -> str:
    sekunden = max(0.0, sekunden)
    h, rest = divmod(sekunden, 3600)
    m, s = divmod(rest, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_text(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def gesicht_finden(video: Path, zeitpunkte: list[float], technik: dict) -> tuple[float, float] | None:
    """Mittelpunkt des größten Gesichts (Anteil von Breite/Höhe), Median über mehrere Bilder."""
    try:
        import cv2  # optional
    except ImportError:
        return None
    erkenner = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs, ys = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for nr, t in enumerate(zeitpunkte):
            bild = Path(tmp) / f"b{nr}.png"
            lauf([ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                  "-vf", "scale=960:-2", str(bild)], pruefen=False)
            if not bild.is_file():
                continue
            grau = cv2.cvtColor(cv2.imread(str(bild)), cv2.COLOR_BGR2GRAY)
            hoehe, breite = grau.shape
            gesichter = erkenner.detectMultiScale(grau, scaleFactor=1.1, minNeighbors=6,
                                                  minSize=(int(breite * 0.05), int(breite * 0.05)))
            if len(gesichter):
                x, y, w, h = max(gesichter, key=lambda g: g[2] * g[3])
                xs.append((x + w / 2) / breite)
                ys.append((y + h / 2) / hoehe)
    if not xs:
        return None
    return statistics.median(xs), statistics.median(ys)


def lautheit_messen(video: Path, von: float, bis: float) -> float | None:
    ergebnis = lauf([ffmpeg(), "-hide_banner", "-nostats", "-ss", f"{von:.3f}", "-t", f"{bis - von:.3f}",
                     "-i", str(video), "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                    pruefen=False)
    text = ergebnis.stderr
    try:
        daten = json.loads(text[text.rindex("{"):text.rindex("}") + 1])
        wert = float(daten["input_i"])
        return wert if math.isfinite(wert) and wert > -70 else None
    except (ValueError, KeyError):
        return None


def ausschnitt(technik: dict, ziel_b: int, ziel_h: int, fokus: tuple[float, float], zoom: float) -> str:
    """crop-Filter für das Zielformat, zentriert auf den Fokus (Gesicht)."""
    quell_b, quell_h = technik["breite"], technik["hoehe"]
    ziel_seiten = ziel_b / ziel_h
    if quell_b / quell_h > ziel_seiten:
        h = quell_h
        b = h * ziel_seiten
    else:
        b = quell_b
        h = b / ziel_seiten
    b, h = b / zoom, h / zoom
    b, h = int(b) // 2 * 2, int(h) // 2 * 2
    fx, fy = fokus
    x = min(max(fx * quell_b - b / 2, 0), quell_b - b)
    # Gesicht im oberen Drittel halten: Fokus liegt 38 % unter der Oberkante des Ausschnitts
    y = min(max(fy * quell_h - h * 0.38, 0), quell_h - h)
    return f"crop={b}:{h}:{int(x)}:{int(y)}"


# ---------------------------------------------------------------- Planung

def planen(rezept: dict, rezept_pfad: Path) -> dict:
    quellordner = Path(rezept.get("quellordner", "."))
    if not quellordner.is_absolute():
        quellordner = (rezept_pfad.parent / quellordner).resolve()
    transkriptordner = Path(rezept.get("transkriptordner", ARBEIT / "transkripte"))
    if not transkriptordner.is_absolute():
        transkriptordner = (rezept_pfad.parent.parent / transkriptordner).resolve()

    clips = []
    for nr, eintrag in enumerate(rezept["clips"], 1):
        video = quellordner / eintrag["datei"]
        if not video.is_file():
            sys.exit(f"Clip {nr}: Datei nicht gefunden: {video}")
        technik = vermessen(video)
        if eintrag.get("teile"):
            teile = eintrag["teile"]
            woerter = eintrag.get("woerter", [])
            info = {"uebereinstimmung": None, "gefunden": "(feste Zeiten aus dem Rezept)", "geschnitten": ""}
        else:
            tpfad = transkript_pfad(video, transkriptordner)
            if not tpfad.is_file():
                print(f"Clip {nr}: Transkript fehlt, wird erstellt …")
                lauf([sys.executable, str(Path(__file__).with_name("transkribieren.py")), str(video),
                      "--ausgabe", str(transkriptordner)])
            transkript = json.loads(tpfad.read_text(encoding="utf-8"))
            info = finde_zitat(transkript, eintrag["zitat"])
            teile, woerter = info["teile"], info["woerter"]
        fokus = eintrag.get("fokus")
        if fokus is None:
            mitte = [a + (b - a) * f for a, b in teile[:1] for f in (0.2, 0.5, 0.8)]
            mitte += [a + (b - a) / 2 for a, b in teile[1:]]
            fokus = gesicht_finden(video, mitte, technik) or (0.5, 0.42)
        clips.append({"nr": nr, "video": video, "technik": technik, "teile": teile, "woerter": woerter,
                      "fokus": list(fokus), "name": eintrag.get("name", ""), "zusatz": eintrag.get("zusatz", ""),
                      "info": info})

    # Zeitachse aufbauen
    t = 0.0
    segmente = []
    for clip in clips:
        clip["start"] = t
        for nr, (a, b) in enumerate(clip["teile"]):
            zoom = ZOOM_SPRUNG if (nr % 2 == 1) else 1.0
            segmente.append({"clip": clip, "von": a, "bis": b, "start": t, "zoom": zoom})
            t += b - a
        clip["ende"] = t
        # Wort-Zeiten auf die Zeitachse legen
        clip["woerter_zeitachse"] = []
        for w in clip["woerter"]:
            for seg in (s for s in segmente if s["clip"] is clip):
                if seg["von"] - 0.15 <= w["von"] < seg["bis"]:
                    von = seg["start"] + max(0.0, w["von"] - seg["von"])
                    bis = seg["start"] + min(seg["bis"], w["bis"]) - seg["von"]
                    clip["woerter_zeitachse"].append({"w": w["w"], "von": von, "bis": max(bis, von + 0.05)})
                    break
    return {"clips": clips, "segmente": segmente, "dauer_clips": t}


# ---------------------------------------------------------------- Untertitel / Einblendungen

def untertitel_bloecke(woerter: list[dict], textbreite, max_px: float,
                       clip_ende: float) -> list[tuple[float, float, str]]:
    """Untertitel in ruhige Blöcke teilen: erst an Satzzeichen, dann so, dass jeder Block in höchstens
    zwei Zeilen passt. Gemessen wird in Pixeln mit der echten Schrift, nicht in Zeichen."""
    def text(gruppe):
        return " ".join(w["w"] for w in gruppe)

    def zeilen(gruppe) -> list[str]:
        """Beste Aufteilung auf eine oder zwei Zeilen (ausgewogen), None wenn es nicht passt."""
        if textbreite(text(gruppe)) <= max_px:
            return [text(gruppe)]
        beste = None
        for k in range(1, len(gruppe)):
            links, rechts = text(gruppe[:k]), text(gruppe[k:])
            breiter = max(textbreite(links), textbreite(rechts))
            if breiter <= max_px and (beste is None or breiter < beste[0]):
                beste = (breiter, [links, rechts])
        return beste[1] if beste else None

    # 1. Phrasen an Satzzeichen
    phrasen, aktuell = [], []
    for w in woerter:
        aktuell.append(w)
        if w["w"][-1:] in ".!?;:,–" and len(text(aktuell)) >= 12:
            phrasen.append(aktuell)
            aktuell = []
    if aktuell:
        if phrasen and len(text(aktuell)) < 10:      # kurzer Rest an die vorige Phrase hängen
            phrasen[-1] += aktuell
        else:
            phrasen.append(aktuell)

    # 2. jede Phrase in möglichst wenige, gleich lange Blöcke teilen, die je in zwei Zeilen passen
    bloecke = []
    for phrase in phrasen:
        for anzahl in range(1, len(phrase) + 1):
            ziel = len(text(phrase)) / anzahl
            teile, block = [], []
            for w in phrase:
                if block and len(text(block + [w])) > ziel * 1.15 and len(teile) < anzahl - 1:
                    teile.append(block)
                    block = []
                block.append(w)
            teile.append(block)
            if all(zeilen(t) for t in teile):
                bloecke += teile
                break
        else:
            bloecke += [[w] for w in phrase]

    ergebnis = []
    for i, block in enumerate(bloecke):
        von = block[0]["von"]
        bis = block[-1]["bis"] + 0.15
        if i + 1 < len(bloecke):
            naechster = bloecke[i + 1][0]["von"]
            if naechster - bis < 0.6:
                bis = naechster
        bis = min(max(bis, von + 0.7), clip_ende)
        ergebnis.append((von, bis, "\n".join(zeilen(block) or [text(block)])))
    return ergebnis


def ass_datei(plan: dict, rezept: dict, fmt: dict, stil: dict) -> str:
    B, H = fmt["breite"], fmt["hoehe"]
    rand = int(B * 0.07)
    ut = int(H * fmt["ut_groesse"])
    hook = int(H * fmt["hook_groesse"])
    name = int(H * fmt["name_groesse"])
    schrift = stil["schrift"]
    weiss, dunkel = ass_farbe("#FFFFFF"), ass_farbe(stil["primaer"])
    kopf = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {B}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Untertitel,{schrift} ExtraBold,{ut},{weiss},{weiss},{ass_farbe(stil['primaer'], 0x30)},&H00000000,0,0,0,0,100,100,0,0,3,{int(ut * 0.22)},0,2,{rand},{rand},{int(H * fmt['ut_unten'])},1
Style: Hook,{schrift} ExtraBold,{hook},{dunkel},{dunkel},{ass_farbe(stil['hell'])},&H00000000,0,0,0,0,100,100,0,0,3,{int(hook * 0.28)},0,8,{rand},{rand},{int(H * fmt['oben'])},1
Style: Name,{schrift} ExtraBold,{name},{weiss},{weiss},{ass_farbe(stil['akzent'])},&H00000000,0,0,0,0,100,100,0,0,3,{int(name * 0.30)},0,7,{rand},{rand},{int(H * fmt['oben'])},1
Style: Zusatz,{schrift} Medium,{int(name * 0.78)},{weiss},{weiss},{ass_farbe(stil['primaer'], 0x20)},&H00000000,0,0,0,0,100,100,0,0,3,{int(name * 0.26)},0,7,{rand},{rand},{int(H * fmt['oben'] + name * 1.75)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    zeilen = []
    hook_ende = 0.0
    if rezept.get("hook", {}).get("text"):
        hook_ende = min(rezept["hook"].get("dauer", 3.0), plan["clips"][0]["ende"])
        zeilen.append(f"Dialogue: 2,{ass_zeit(0)},{ass_zeit(hook_ende)},Hook,,0,0,0,,"
                      f"{{\\fad(120,200)}}{ass_text(rezept['hook']['text'])}")
    from PIL import ImageFont
    ut_schrift = ImageFont.truetype(str(SCHRIFTEN / "Figtree-ExtraBold.ttf"), ut)
    max_px = B - 2 * rand - 2 * int(ut * 0.22)

    def textbreite(t: str) -> float:
        return ut_schrift.getlength(t)

    for clip in plan["clips"]:
        for von, bis, text in untertitel_bloecke(clip["woerter_zeitachse"], textbreite, max_px, clip["ende"]):
            zeilen.append(f"Dialogue: 1,{ass_zeit(von)},{ass_zeit(bis)},Untertitel,,0,0,0,,"
                          + ass_text(text).replace("\n", "\\N"))
        if clip["name"]:
            start = max(clip["start"] + 0.3, hook_ende + 0.15)
            ende = min(clip["ende"] - 0.25, start + 3.2)
            if ende - start >= 1.2:
                zeilen.append(f"Dialogue: 3,{ass_zeit(start)},{ass_zeit(ende)},Name,,0,0,0,,"
                              f"{{\\fad(180,180)}}{ass_text(clip['name'])}")
                if clip["zusatz"]:
                    zeilen.append(f"Dialogue: 3,{ass_zeit(start + 0.12)},{ass_zeit(ende)},Zusatz,,0,0,0,,"
                                  f"{{\\fad(180,180)}}{ass_text(clip['zusatz'])}")
    return kopf + "\n".join(zeilen) + "\n"


def endcard_bild(ziel: Path, fmt: dict, stil: dict, endcard: dict) -> None:
    """Endcard als transparentes PNG in voller Bildgröße (Karte in der Sicherheitszone)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    B, H = fmt["breite"], fmt["hoehe"]
    bild = Image.new("RGBA", (B, H), (0, 0, 0, 0))

    def schrift(stark: str, groesse: int):
        return ImageFont.truetype(str(SCHRIFTEN / f"Figtree-{stark}.ttf"), groesse)

    def farbe(hexwert: str, alpha: int = 255):
        return tuple(int(hexwert[i:i + 2], 16) for i in (1, 3, 5)) + (alpha,)

    karte_b = int(B * 0.84)
    innen = int(karte_b * 0.08)
    einheit = H * (0.0105 if B / H < 0.7 else 0.0135)
    zeilen = []   # (text, schrift, farbe, abstand_danach)
    titel = schrift("ExtraBold", int(einheit * 4.2))
    for teil in endcard.get("titel", "").split("\n"):
        zeilen.append((teil, titel, stil["primaer"], int(einheit * 0.6)))
    if zeilen:
        zeilen[-1] = zeilen[-1][:3] + (int(einheit * 1.8),)
    if endcard.get("untertitel"):
        zeilen.append((endcard["untertitel"], schrift("Medium", int(einheit * 2.4)), stil["text_dunkel"],
                       int(einheit * 3.0)))
    knopf_schrift = schrift("ExtraBold", int(einheit * 2.5))
    knopf_text = endcard.get("knopf", "")

    def textbreite(text, f):
        l, _, r, _ = f.getbbox(text)
        return r - l

    # Schrift verkleinern, bis alles in die Karte passt
    max_breite = karte_b - 2 * innen
    for i, (text, f, c, abstand) in enumerate(zeilen):
        while textbreite(text, f) > max_breite and f.size > 20:
            f = ImageFont.truetype(f.path, f.size - 2)
        zeilen[i] = (text, f, c, abstand)
    while knopf_text and textbreite(knopf_text, knopf_schrift) > max_breite - 2 * einheit * 2.4:
        knopf_schrift = ImageFont.truetype(knopf_schrift.path, knopf_schrift.size - 2)

    zeilenhoehe = [f.getbbox("ÄgJ")[3] - f.getbbox("ÄgJ")[1] for _, f, _, _ in zeilen]
    knopf_h = int(knopf_schrift.size * 2.3) if knopf_text else 0
    hinweis = endcard.get("hinweis", "")
    hinweis_schrift = schrift("Medium", int(einheit * 1.9))
    hinweis_h = int(hinweis_schrift.size * 1.9) if hinweis else 0
    karte_h = innen * 2 + sum(zeilenhoehe) + sum(z[3] for z in zeilen) + knopf_h + hinweis_h
    oben = int(H * fmt["karte_mitte"] - karte_h / 2)
    links = (B - karte_b) // 2

    schatten = Image.new("RGBA", (B, H), (0, 0, 0, 0))
    ImageDraw.Draw(schatten).rounded_rectangle([links, oben + 14, links + karte_b, oben + karte_h + 14],
                                               radius=int(einheit * 3), fill=(0, 0, 0, 90))
    bild.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(int(einheit * 2))))
    zeichnen = ImageDraw.Draw(bild)
    zeichnen.rounded_rectangle([links, oben, links + karte_b, oben + karte_h], radius=int(einheit * 3),
                               fill=farbe(stil["hell"]))
    y = oben + innen
    for (text, f, c, abstand), zh in zip(zeilen, zeilenhoehe):
        x = (B - textbreite(text, f)) // 2 - f.getbbox(text)[0]
        zeichnen.text((x, y - f.getbbox("ÄgJ")[1]), text, font=f, fill=farbe(c))
        y += zh + abstand
    if knopf_text:
        kb = textbreite(knopf_text, knopf_schrift) + int(einheit * 5.0)
        kx = (B - kb) // 2
        zeichnen.rounded_rectangle([kx, y, kx + kb, y + knopf_h], radius=knopf_h // 2, fill=farbe(stil["akzent"]))
        bb = knopf_schrift.getbbox(knopf_text)
        zeichnen.text(((B - (bb[2] - bb[0])) // 2 - bb[0], y + (knopf_h - (bb[3] - bb[1])) // 2 - bb[1]),
                      knopf_text, font=knopf_schrift, fill=(255, 255, 255, 255))
        y += knopf_h
    if hinweis:
        bb = hinweis_schrift.getbbox(hinweis)
        zeichnen.text(((B - (bb[2] - bb[0])) // 2 - bb[0], y + int(hinweis_h * 0.35) - bb[1]), hinweis,
                      font=hinweis_schrift, fill=farbe(stil["text_dunkel"], 200))
    bild.save(ziel)


# ---------------------------------------------------------------- Rendern

def rendern(plan: dict, rezept: dict, format_name: str, ziel: Path, arbeitsordner: Path) -> None:
    fmt = FORMATE[format_name]
    stil = {**STIL_STANDARD, **rezept.get("stil", {})}
    B, H = fmt["breite"], fmt["hoehe"]
    fps = rezept.get("fps") or plan["clips"][0]["technik"]["fps"] or 25
    endcard = rezept.get("endcard", {})
    e_dauer = endcard.get("dauer", ENDCARD_STANDARD) if endcard else 0.0
    T = plan["dauer_clips"]

    (arbeitsordner / "untertitel.ass").write_text(ass_datei(plan, rezept, fmt, stil), encoding="utf-8")
    schriftordner = arbeitsordner / "schriften"
    shutil.copytree(SCHRIFTEN, schriftordner, dirs_exist_ok=True)

    eingaben, filter_teile, paare = [], [], []
    for k, seg in enumerate(plan["segmente"]):
        clip = seg["clip"]
        dauer = seg["bis"] - seg["von"]
        eingaben += ["-ss", f"{seg['von']:.3f}", "-t", f"{dauer:.3f}", "-i", str(clip["video"])]
        crop = ausschnitt(clip["technik"], B, H, tuple(clip["fokus"]), seg["zoom"])
        vergroesserung = H / int(crop.split("=")[1].split(":")[1])
        schaerfen = ",unsharp=5:5:0.5:5:5:0" if vergroesserung > 1.3 else ""
        filter_teile.append(f"[{k}:v]setpts=PTS-STARTPTS,{crop},scale={B}:{H}:flags=lanczos{schaerfen},setsar=1,"
                            f"fps={fps},format=yuv420p[v{k}]")
        if clip["technik"]["hat_ton"]:
            filter_teile.append(f"[{k}:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
                                f"volume={clip.get('verstaerkung', 0.0):.2f}dB,"
                                f"afade=t=in:d=0.02,afade=t=out:st={max(0.0, dauer - 0.03):.3f}:d=0.03[a{k}]")
        else:
            filter_teile.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{dauer:.3f}[a{k}]")
        paare.append(f"[v{k}][a{k}]")
    n = len(plan["segmente"])
    filter_teile.append(f"{''.join(paare)}concat=n={n}:v=1:a=1[vc][ac]")

    video_kette = "[vc]"
    if e_dauer:
        filter_teile.append(f"[vc]tpad=stop_mode=clone:stop_duration={e_dauer:.2f},"
                            f"boxblur=luma_radius=18:luma_power=2:enable='gte(t,{T:.3f})',"
                            f"eq=brightness=-0.06:saturation=0.75:enable='gte(t,{T:.3f})'[vp]")
        video_kette = "[vp]"
    filter_teile.append(f"{video_kette}subtitles=untertitel.ass:fontsdir=schriften[vs]")
    ausgang = "[vs]"
    if e_dauer:
        endcard_bild(arbeitsordner / "endcard.png", fmt, stil, endcard)
        eingaben += ["-loop", "1", "-framerate", str(fps), "-t", f"{e_dauer:.2f}", "-i", "endcard.png"]
        filter_teile.append(f"[{n}:v]format=rgba,fade=t=in:st=0:d=0.45:alpha=1,setpts=PTS-STARTPTS+{T:.3f}/TB[ec]")
        filter_teile.append(f"[vs][ec]overlay=x=0:y='if(lt(t-{T:.3f},0.45),70*(1-(t-{T:.3f})/0.45),0)':"
                            f"eval=frame:eof_action=pass[vo]")
        ausgang = "[vo]"
    filter_teile.append(f"[ac]highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
                        f"apad=pad_dur={e_dauer + 0.5:.2f}[ao]")

    gesamt = T + e_dauer
    befehl = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *eingaben,
              "-filter_complex", ";".join(filter_teile), "-map", ausgang, "-map", "[ao]",
              "-t", f"{gesamt:.3f}", "-r", str(fps),
              "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(ziel.resolve())]
    (arbeitsordner / "ffmpeg-befehl.txt").write_text(" ".join(f'"{b}"' if " " in b else b for b in befehl),
                                                     encoding="utf-8")
    import subprocess
    ergebnis = subprocess.run(befehl, cwd=arbeitsordner, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    if ergebnis.returncode != 0:
        raise RuntimeError("ffmpeg-Fehler:\n" + "\n".join(ergebnis.stderr.strip().splitlines()[-30:]))


def vorschau(video: Path, plan: dict, rezept: dict, ziel: Path) -> None:
    """Kontaktbogen: Hook, Mitte jedes Clips, Endcard – zum schnellen Prüfen."""
    from PIL import Image

    zeitpunkte = [min(1.2, plan["clips"][0]["ende"] / 2)]
    zeitpunkte += [(c["start"] + c["ende"]) / 2 for c in plan["clips"]]
    if rezept.get("endcard"):
        zeitpunkte.append(plan["dauer_clips"] + rezept["endcard"].get("dauer", ENDCARD_STANDARD) - 0.3)
    bilder = []
    with tempfile.TemporaryDirectory() as tmp:
        for nr, t in enumerate(zeitpunkte):
            datei = Path(tmp) / f"{nr}.png"
            lauf([ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                  "-vf", "scale=-2:720", str(datei)])
            bilder.append(Image.open(datei).convert("RGB"))
    abstand = 16
    breite = sum(b.width for b in bilder) + abstand * (len(bilder) + 1)
    bogen = Image.new("RGB", (breite, 720 + 2 * abstand), (30, 30, 30))
    x = abstand
    for b in bilder:
        bogen.paste(b, (x, abstand))
        x += b.width + abstand
    bogen.save(ziel)


def schnittliste(plan: dict, rezept: dict, ziel: Path) -> None:
    zeilen = [f"# Schnittliste {rezept['id']} – {rezept.get('titel', rezept['name'])}", "",
              f"Gesamtlänge: {plan['dauer_clips'] + rezept.get('endcard', {}).get('dauer', 0):.1f} s "
              f"(Clips {plan['dauer_clips']:.1f} s + Endcard)", "",
              "| # | Zeitachse | Quelle | Ausschnitt im Original | Treffer | Bildfokus |",
              "|---|---|---|---|---|---|"]
    for c in plan["clips"]:
        teile = ", ".join(f"{zeit(a)}–{zeit(b)}" for a, b in c["teile"])
        treffer = f"{c['info']['uebereinstimmung']:.0%}" if c["info"].get("uebereinstimmung") else "–"
        zeilen.append(f"| {c['nr']} | {zeit(c['start'])}–{zeit(c['ende'])} | {c['video'].name} | {teile} | "
                      f"{treffer} | x {c['fokus'][0]:.2f}, y {c['fokus'][1]:.2f} |")
    zeilen.append("")
    for c in plan["clips"]:
        zeilen.append(f"**Clip {c['nr']} – {c['name'] or c['video'].stem}**  ")
        zeilen.append(f"Untertitel: {' '.join(w['w'] for w in c['woerter'])}  ")
        zeilen.append(f"Im Video erkannt: {c['info']['gefunden']}  ")
        if c["info"].get("geschnitten"):
            zeilen.append(f"Herausgeschnitten: {c['info']['geschnitten']}  ")
        zeilen.append("")
    ziel.write_text("\n".join(zeilen), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rezept")
    parser.add_argument("--formate", nargs="+", default=None, help="z. B. 9x16 4x5 (Standard: aus dem Rezept)")
    parser.add_argument("--ausgabe", default=str(AUSGABE))
    parser.add_argument("--nur-planen", action="store_true", help="nur Zitate suchen und Schnittliste schreiben")
    parser.add_argument("--trotz-regelwerk", action="store_true", help="trotz Regelwerk-Treffern rendern")
    parser.add_argument("--quellordner", help="Ordner mit dem Videomaterial (überschreibt das Rezept)")
    parser.add_argument("--nur-hook", type=int, help="nur diese Hook-Variante rendern (1, 2, …)")
    args = parser.parse_args()

    rezept_pfad = Path(args.rezept).resolve()
    rezept = json.loads(rezept_pfad.read_text(encoding="utf-8"))
    if args.quellordner:
        rezept["quellordner"] = args.quellordner
    treffer = pruefen(texte_aus_rezept(rezept), rezept.get("funnel", "evergreen"))
    if treffer:
        print("Regelwerk-Treffer:\n - " + "\n - ".join(treffer))
        if not args.trotz_regelwerk:
            sys.exit("Abbruch. Texte anpassen oder bewusst mit --trotz-regelwerk rendern.")

    plan = planen(rezept, rezept_pfad)
    for c in plan["clips"]:
        if c["technik"]["hat_ton"]:
            wert = lautheit_messen(c["video"], c["teile"][0][0], c["teile"][-1][1])
            c["verstaerkung"] = max(-12.0, min(12.0, ZIEL_LUFS_CLIP - wert)) if wert is not None else 0.0
        print(f"Clip {c['nr']}: {c['video'].name} {zeit(c['teile'][0][0])}–{zeit(c['teile'][-1][1])}, "
              f"{len(c['teile'])} Teil(e), Fokus x={c['fokus'][0]:.2f}"
              + (f", Treffer {c['info']['uebereinstimmung']:.0%}" if c['info'].get('uebereinstimmung') else ""))

    ausgabe = Path(args.ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)
    basis = f"{rezept['id']}_{rezept['name']}"
    schnittliste(plan, rezept, ausgabe / f"{basis}_Schnittliste.md")
    if args.nur_planen:
        print(f"Schnittliste: {ausgabe / (basis + '_Schnittliste.md')}")
        return

    # Hook-Varianten: gleiche Ad, anderer Einstieg (günstigster Kreativtest, zählt bei Meta als Variation)
    hooks = rezept.get("hook", {}).get("varianten") or [rezept.get("hook", {}).get("text", "")]
    for nr, hook_text in enumerate(hooks, 1):
        if args.nur_hook and nr != args.nur_hook:
            continue
        fassung = {**rezept, "hook": {**rezept.get("hook", {}), "text": hook_text}}
        kennung = f"{basis}_H{nr}" if len(hooks) > 1 else basis
        for format_name in args.formate or rezept.get("formate", ["9x16", "4x5"]):
            ziel = ausgabe / f"{kennung}_{format_name}.mp4"
            arbeitsordner = ARBEIT / "render" / f"{kennung}_{format_name}"
            arbeitsordner.mkdir(parents=True, exist_ok=True)
            print(f"Rendere {ziel.name} (Hook: {hook_text}) …", flush=True)
            rendern(plan, fassung, format_name, ziel, arbeitsordner)
            vorschau(ziel, plan, fassung, ziel.with_name(ziel.stem + "_Vorschau.png"))
            technik = vermessen(ziel)
            print(f"   fertig: {technik['breite']}x{technik['hoehe']}, {technik['dauer']:.1f} s, "
                  f"{ziel.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
