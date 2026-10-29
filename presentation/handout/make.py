#!/usr/bin/env python3
"""Printed A4 handout for the Sag's Heilbronn table, German and English.

    python3 presentation/handout/make.py   # writes handout-de.html/.pdf, handout-en.html/.pdf

Two pages per language (front + back, print double-sided). HTML is self-contained
(inline CSS, inline leaf + QR SVG); google-chrome renders it to PDF. Fonts: IBM Plex
Mono (the deck's font) and Inter (the app's) via Google Fonts, with DejaVu Sans Mono /
system sans as offline fallbacks. Texts live in TEXT below; the layout is shared.
"""
import pathlib, re, shutil, subprocess, html as H

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
URL = "https://greencity.parsalotfi.com/"
URL_SHORT = "greencity.parsalotfi.com"
GITHUB = "github.com/HelloX3030/green-city"

# --- shared assets -----------------------------------------------------------
qr_master = (ROOT / "resources/qr/greencity-qr.svg").read_text()
QR = re.sub(r'width="100mm" height="100mm"', 'class="qr"', qr_master, count=1)   # black on white, quiet zone included

LEAF = ('<svg class="leaf" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="24" height="24" rx="5.5" fill="#3a7d5c"/>'
        '<g transform="translate(3.6 3.6) scale(.7)" fill="none" stroke="#fff" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/>'
        '<path d="M2 21c0-3 1.9-5.5 5-6.5"/></g></svg>')

CLUSTER = ('<svg class="illus" viewBox="0 0 60 44" xmlns="http://www.w3.org/2000/svg">'
           '<circle cx="24" cy="22" r="17" fill="#3a7d5c" fill-opacity=".12" stroke="#3a7d5c" stroke-width=".6" stroke-dasharray="1.6 1.4"/>'
           '<g fill="#3a7d5c"><circle cx="16" cy="18" r="1.8"/><circle cx="30" cy="14" r="1.8"/><circle cx="28" cy="30" r="1.8"/><circle cx="19" cy="29" r="1.8"/><circle cx="33" cy="23" r="1.8"/></g>'
           '<line x1="24" y1="22" x2="41" y2="22" stroke="#6e6e73" stroke-width=".5"/><line x1="24" y1="20.5" x2="24" y2="23.5" stroke="#6e6e73" stroke-width=".5"/><line x1="41" y1="20.5" x2="41" y2="23.5" stroke="#6e6e73" stroke-width=".5"/>'
           '<text x="44" y="23.3">100 m</text>'
           '<circle cx="24" cy="22" r="5.2" fill="#3a7d5c"/><text x="24" y="23.7" text-anchor="middle" style="fill:#fff;font-size:4.6px;font-weight:700">3</text>'
           '</svg>')

# small step glyphs (stroke icons, inherit colour)
ICON = {
    "pin": '<svg viewBox="0 0 24 24"><path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12Z"/><circle cx="12" cy="10" r="2.6"/></svg>',
    "cluster": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5" stroke-dasharray="2 2"/><circle cx="12" cy="12" r="4"/><circle cx="7" cy="8" r="1.3"/><circle cx="17" cy="9" r="1.3"/><circle cx="15" cy="17" r="1.3"/></svg>',
    "check": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5"/><path d="m7.5 12.2 3 3 6-6.4"/></svg>',
}

# --- texts -------------------------------------------------------------------
TEXT = {
 "de": dict(
  lang="de", title="Sag's Heilbronn – Handout (DE)",
  kicker="{ DATEN FÜR DAS HEILBRONN VON MORGEN. }",
  hack="Green City Hackathon Heilbronn · 27.–29. Oktober 2026",
  oneliner="Du meldest, wo Heilbronn zu laut, zu heiß ist oder die Luft schlecht. "
           "Wir prüfen es mit Sensordaten. Wo Daten fehlen, kommt ein Sensor hin.",
  who=[("WER:", "The Green Flags"), ("FÜR WEN:", "Die Menschen in Heilbronn"), ("WAS:", "Melden · Bündeln · Prüfen")],
  numbers_h="Die Geschichte in drei Zahlen",
  numbers=[
    ("40.200", "Menschen in Heilbronn sind Straßen&shy;verkehrs&shy;lärm über 55&nbsp;dB(A) Lden ausgesetzt.",
     "Lärmaktionsplan Stufe IV, 2024"),
    ("Ungeprüft", "So stehen Lärmbeschwerden über Raser- und „Poser“-Nächte im Mängelmelder der Stadt, "
     "abgelegt unter „Straße und Verkehr“. Niemand kann sie prüfen.", "Mängelmelder Heilbronn"),
    ("2029&nbsp;→&nbsp;2026", "Die nächste vergleichbare Auswertung des Lärmaktionsplans kommt 2029 – berechnet, "
     "nicht gemessen. Wir werten jetzt aus, 2026, mit Messungen.", "Lärmaktionsplan Stufe IV"),
  ],
  qr_h="Scannen, melden, fertig.",
  qr_sub="Drei Tipps, Standort per GPS. Läuft jetzt – probier es gleich hier am Stand.",
  front_foot_r="Rückseite: So funktioniert’s →",
  how_h="So funktioniert’s",
  steps=[
    ("01 · MELDEN", "Melden", "pin",
     "Drei Tipps, Standort per GPS. Was stört dich hier?",
     ["Zu laut", "Zu heiß", "Schlechte Luft", "Kein Schatten", "Müll*", "Kaputte Straße*", "Anderes"],
     "* Ausblick: Derselbe Kreislauf funktioniert für alles, was eine Stadt messen kann."),
    ("02 · BÜNDELN", "Bündeln", "cluster",
     "Meldungen im Umkreis von 100&nbsp;m werden eine Stelle. Die Zahl auf der Karte ist die Anzahl der Meldungen.",
     None, None),
    ("03 · PRÜFEN", "Prüfen", "check",
     "Jede Stelle wird mit dem nächsten Sensor verglichen, Schatten mit dem Baumkataster der Stadt.",
     None, None),
  ],
  status=[("Bestätigt", "#3a7d5c"), ("Nicht bestätigt", "#c38b2f"), ("Sensor fehlt", "#5f6b7a")],
  rank="Wo der Sensor fehlt, zählen die Meldungen: <b>„Platz 1 von 8 Stellen ohne Sensor“</b> – dort kommt der nächste Sensor hin.",
  today_h="Was es heute schon gibt",
  today=[
    "<b>Die App</b>, live auf einem Raspberry Pi in Heilbronn.",
    "<b>Daten</b> von openSenseMap (senseBox:home-Stationen und senseBox:bike-Fahrten) und der Umweltbundesamt-Station DEBW015.",
    "<b>Lärmkarte 2022</b> und <b>Baumkataster</b> der Stadt als Kartenebenen.",
    "<b>Unser eigener Sensor „NoiseNode“</b>: senseBox MCU-S2 + Schallpegelmesser, 3D-gedrucktes Gehäuse, "
    "ca. 100–150&nbsp;€ Bauteile. Seit 28.&nbsp;Oktober 2026 live auf openSenseMap: LAeq, Lmax und laute Ereignisse "
    "pro Minute. Es wird kein Audio aufgezeichnet.",
    f"<b>Open Source auf GitHub:</b> {GITHUB}",
  ],
  ask_h="Was wir brauchen",
  ask="Die nächsten <b>10 NoiseNodes</b> für die Straßen des Lärmaktionsplans – gemessen vor und nach dem geplanten "
      "lärmarmen Asphalt (2,5&nbsp;Mio.&nbsp;€ im Plan).",
  ask_2="Dann hat die Stadt <b>2027 eine gemessene Antwort</b> statt einer Neuberechnung 2029.",
  closing=("Eine grünere Stadt sammelt nicht nur mehr Daten.", "Sie hört ihren Menschen zu und handelt danach."),
  team_l="Team", team="The Green Flags: Ethan, Alexia, Lukas, Fred, Seyedparsa",
  event_l="Hackathon", event="Green City Hackathon Heilbronn, 27.–29. Oktober 2026",
  data_l="Daten", data="openSenseMap, Umweltbundesamt, Stadt Heilbronn",
  code_l="Code", code=f"Open Source auf GitHub · {GITHUB}",
 ),
 "en": dict(
  lang="en", title="Sag's Heilbronn – handout (EN)",
  kicker="{ DATA FOR THE HEILBRONN OF TOMORROW. }",
  hack="Green City Hackathon Heilbronn · 27–29 October 2026",
  oneliner="Citizens report where Heilbronn is too loud, too hot or the air is bad. "
           "We check it against sensor data. Where no data exists, a sensor goes there.",
  who=[("WHO:", "The Green Flags"), ("FOR WHO:", "Heilbronn citizens"), ("WHAT:", "Report · Cluster · Check")],
  numbers_h="The story in three numbers",
  numbers=[
    ("40,200", "Heilbronn residents are exposed to road traffic noise above 55&nbsp;dB(A) Lden.",
     "Lärmaktionsplan Stufe IV, 2024"),
    ("Ungeprüft", "“Unchecked”: the status of noise complaints about racing and “Poser” nights in the city’s "
     "Mängelmelder (defect reporting tool), filed under “Straße und Verkehr”. Nobody can check them.", "Mängelmelder Heilbronn"),
    ("2029&nbsp;→&nbsp;2026", "The next comparable noise action plan evaluation is due in 2029 – by calculation, "
     "not measurement. We start evaluating now, in 2026, by measuring.", "Lärmaktionsplan Stufe IV"),
  ],
  qr_h="Scan, report, done.",
  qr_sub="Three taps, location from GPS. It is live now – try it right here at the table.",
  front_foot_r="Back: how it works →",
  how_h="How it works",
  steps=[
    ("01 · MELDEN", "Report", "pin",
     "Three taps, location from GPS. What bothers you here?",
     ["Too loud", "Too hot", "Bad air", "No shade", "Litter*", "Broken road*", "Other"],
     "* Outlook: the same loop works for anything a city can measure."),
    ("02 · BÜNDELN", "Cluster", "cluster",
     "Reports within 100&nbsp;m form one spot. The number on the map is the number of reports.",
     None, None),
    ("03 · PRÜFEN", "Check", "check",
     "Each spot is compared with the nearest sensor; shade against the city’s tree register.",
     None, None),
  ],
  status=[("Bestätigt", "#3a7d5c"), ("Nicht bestätigt", "#c38b2f"), ("Sensor fehlt", "#5f6b7a")],
  rank="Where the sensor is missing, reports decide: <b>“Platz 1 von 8 Stellen ohne Sensor”</b> "
       "(no.&nbsp;1 of 8 spots without a sensor) – that is where the next sensor goes.",
  today_h="What exists today",
  today=[
    "<b>The app</b>, live on a Raspberry Pi in Heilbronn.",
    "<b>Data</b> from openSenseMap (senseBox:home stations and senseBox:bike rides) and the Umweltbundesamt station DEBW015.",
    "The city’s <b>noise map 2022</b> and <b>tree register</b> as map layers.",
    "<b>Our own sensor “NoiseNode”</b>: senseBox MCU-S2 + sound level meter, 3D-printed case, "
    "about 100–150&nbsp;€ in parts. Live on openSenseMap since 28&nbsp;October 2026, measuring LAeq, Lmax and "
    "loud events per minute. No audio is recorded.",
    f"<b>Open source on GitHub:</b> {GITHUB}",
  ],
  ask_h="The ask",
  ask="The next <b>10 NoiseNodes</b> for the streets of the Lärmaktionsplan – measured before and after the planned "
      "low-noise asphalt (2.5&nbsp;million&nbsp;€ in the plan).",
  ask_2="So the city has <b>a measured answer in 2027</b> instead of a recalculation in 2029.",
  closing=("A greener city isn’t just one that collects more data.", "It’s one that listens to its people and acts on what it learns."),
  team_l="Team", team="The Green Flags: Ethan, Alexia, Lukas, Fred, Seyedparsa",
  event_l="Hackathon", event="Green City Hackathon Heilbronn, 27–29 October 2026",
  data_l="Data", data="openSenseMap, Umweltbundesamt, Stadt Heilbronn",
  code_l="Code", code=f"Open source on GitHub · {GITHUB}",
 ),
}

# --- style -------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 0; }
:root {
  --navy: #070a2b; --lime: #d7fc00; --paper: #fff; --grey: #ededeb;
  --ink: #1d1d1f; --sec: #6e6e73; --green: #3a7d5c; --line: #d9d9d6;
  --mono: 'IBM Plex Mono', 'DejaVu Sans Mono', 'Liberation Mono', monospace;
  --sans: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
html, body { margin: 0; padding: 0; }
body { font-family: var(--sans); color: var(--ink); font-size: 10pt; line-height: 1.4; background: var(--paper); }
.page { width: 210mm; height: 297mm; overflow: hidden; position: relative; break-after: page; page-break-after: always; background: var(--paper); }
.page:last-child { break-after: auto; page-break-after: auto; }
.mono { font-family: var(--mono); }
b { font-weight: 600; }

/* ---------- front ---------- */
.hero { background: var(--navy); color: #fff; padding: 13mm 15mm 12mm; height: 112mm; position: relative; }
.hero .top { display: flex; justify-content: space-between; align-items: baseline; font-family: var(--mono); font-size: 8.4pt; letter-spacing: .04em; }
.hero .top .kicker { color: var(--lime); }
.hero .top .hack { color: rgba(255,255,255,.72); }
.hero .brand { display: flex; align-items: center; gap: 6mm; margin-top: 13mm; }
.hero .brand .leaf { width: 17mm; height: 17mm; flex: none; }
.hero h1 { font-family: var(--mono); font-weight: 700; font-size: 38pt; line-height: 1; margin: 0; letter-spacing: -.01em; }
.hero h1 small { display: block; font-size: 9.5pt; font-weight: 400; letter-spacing: .14em; color: var(--lime); margin-bottom: 2.6mm; }
.hero .oneliner { font-size: 14.5pt; line-height: 1.35; margin: 8mm 0 0; max-width: 178mm; font-weight: 400; }
.hero .who { font-family: var(--mono); font-size: 10.5pt; margin-top: 8mm; line-height: 1.75; }
.hero .who .gt { color: var(--lime); margin-right: 3mm; }
.hero .who .k { color: rgba(255,255,255,.72); margin-right: 2.5mm; }
.hero .who .v { color: #fff; font-weight: 700; }

.body { padding: 10mm 15mm 0; }
.sect { font-family: var(--mono); font-size: 8.4pt; letter-spacing: .12em; text-transform: uppercase; color: var(--green); margin: 0 0 4mm; font-weight: 600; }
.nums { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm; }
.num { background: var(--grey); border-radius: 22px; padding: 7mm 6mm 6mm; min-height: 76mm; display: flex; flex-direction: column; }
.num .big { font-family: var(--mono); font-weight: 700; font-size: 25pt; line-height: 1.05; color: var(--navy); letter-spacing: -.02em; margin-bottom: 3.5mm; white-space: nowrap; }
.num .txt { font-size: 10pt; line-height: 1.42; flex: 1; }
.num .src { font-family: var(--mono); font-size: 7pt; color: var(--sec); margin-top: 3mm; }

.scan { margin-top: 8mm; display: grid; grid-template-columns: 50mm 1fr; gap: 8mm; align-items: center; border: 0.5mm solid var(--green); border-radius: 22px; padding: 6mm 8mm 6mm 6mm; }
.scan .qr { width: 44mm; height: 44mm; display: block; margin: 0 auto; }
.scan h2 { font-family: var(--mono); font-weight: 700; font-size: 22pt; margin: 0 0 3mm; line-height: 1.1; color: var(--navy); }
.scan .url { font-family: var(--mono); font-size: 15pt; font-weight: 600; color: var(--green); margin: 0 0 3mm; }
.scan .sub { font-size: 10pt; color: var(--ink); margin: 0; }

.foot { position: absolute; left: 15mm; right: 15mm; bottom: 9mm; display: flex; justify-content: space-between; font-family: var(--mono); font-size: 7.6pt; color: var(--sec); border-top: 0.3mm solid var(--line); padding-top: 3mm; }
.foot .leaf { width: 4mm; height: 4mm; vertical-align: -1mm; margin-right: 2mm; }

/* ---------- back ---------- */
.back { padding: 13mm 15mm 0; }
.back .head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7mm; }
.back .head h2 { font-family: var(--mono); font-weight: 700; font-size: 20pt; margin: 0; color: var(--navy); display: flex; align-items: center; gap: 4mm; }
.back .head .leaf { width: 9mm; height: 9mm; }
.back .head .tag { font-family: var(--mono); font-size: 8.4pt; color: var(--sec); letter-spacing: .04em; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm; }
.step { background: var(--grey); border-radius: 22px; padding: 6mm 6mm 6mm; min-height: 86mm; display: flex; flex-direction: column; }
.step .k { font-family: var(--mono); font-size: 7.6pt; letter-spacing: .12em; color: var(--green); font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
.step .k svg { width: 6.5mm; height: 6.5mm; fill: none; stroke: var(--green); stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.step h3 { font-size: 15.5pt; font-weight: 600; margin: 3mm 0 2.5mm; letter-spacing: -.01em; }
.step p { margin: 0 0 3mm; font-size: 10pt; line-height: 1.42; }
.chips { display: flex; flex-wrap: wrap; gap: 1.6mm; margin: 1mm 0 3mm; }
.chip { font-size: 8.4pt; font-weight: 500; background: #fff; border-radius: 3mm; padding: 1mm 2.6mm; color: var(--ink); line-height: 1.3; }
.note { font-size: 7.6pt; color: var(--sec); line-height: 1.35; margin-top: auto; }
.status { display: flex; flex-direction: column; gap: 1.8mm; margin: 1mm 0 3mm; }
.pill { display: inline-flex; align-items: center; gap: 2.2mm; font-size: 9pt; font-weight: 600; }
.pill i { width: 3.6mm; height: 3.6mm; border-radius: 50%; display: inline-block; flex: none; }
.illus { margin: 3mm auto 0; width: 48mm; display: block; }
.illus text { font-family: var(--mono); font-size: 3.6px; fill: var(--sec); }
.rank { font-size: 9.4pt; line-height: 1.4; margin-top: auto; padding-top: 2.5mm; border-top: 0.3mm solid #d4d4d0; }

.two { display: grid; grid-template-columns: 1.3fr 1fr; gap: 5mm; margin-top: 6mm; }
.today { padding: 1mm 1mm 0; }
.today ul { margin: 0; padding: 0; list-style: none; }
.today li { position: relative; padding-left: 5.5mm; margin-bottom: 2.8mm; font-size: 10pt; line-height: 1.42; }
.today li::before { content: ">"; position: absolute; left: 0; top: 0; font-family: var(--mono); font-weight: 700; color: var(--green); }
.ask { background: var(--navy); color: #fff; border-radius: 22px; padding: 7mm 7mm 6mm; }
.ask .sect { color: var(--lime); }
.ask p { margin: 0 0 3mm; font-size: 10.4pt; line-height: 1.42; }
.ask p:last-child { margin-bottom: 0; }
.ask b { color: var(--lime); font-weight: 600; }

.closing { margin-top: 11mm; text-align: center; font-family: var(--mono); font-weight: 700; font-size: 12.5pt; line-height: 1.5; color: var(--navy); }
.closing .b { color: var(--green); font-weight: 400; margin: 0 2mm; }

.backfoot { position: absolute; left: 15mm; right: 15mm; bottom: 9mm; border-top: 0.3mm solid var(--line); padding-top: 3.5mm; display: grid; grid-template-columns: 1fr; gap: 1.2mm; font-size: 8.4pt; color: var(--sec); }
.backfoot .l { display: inline-block; width: 18mm; }
.backfoot .l { font-family: var(--mono); font-size: 7.2pt; letter-spacing: .1em; text-transform: uppercase; color: var(--green); margin-right: 2mm; }
.backfoot .v { color: var(--ink); }
"""

# --- page builders -----------------------------------------------------------
def front(t):
    who = "".join(f'<div><span class="gt">&gt;</span><span class="k">{k}</span><span class="v">{v}</span></div>' for k, v in t["who"])
    nums = "".join(f'<div class="num"><div class="big">{n}</div><div class="txt">{txt}</div><div class="src">{src}</div></div>'
                   for n, txt, src in t["numbers"])
    return f'''
<section class="page">
  <div class="hero">
    <div class="top"><span class="kicker">{H.escape(t["kicker"])}</span><span class="hack">{t["hack"]}</span></div>
    <div class="brand">{LEAF}<h1><small>{"GREEN CITY HACKATHON · PROJEKT" if t["lang"]=="de" else "GREEN CITY HACKATHON · PROJECT"}</small>Sag's Heilbronn</h1></div>
    <p class="oneliner">{t["oneliner"]}</p>
    <div class="who">{who}</div>
  </div>
  <div class="body">
    <div class="sect">{t["numbers_h"]}</div>
    <div class="nums">{nums}</div>
    <div class="scan">
      {QR}
      <div><h2>{t["qr_h"]}</h2><p class="url">{URL_SHORT}</p><p class="sub">{t["qr_sub"]}</p></div>
    </div>
  </div>
  <div class="foot"><span>{LEAF}Sag's Heilbronn · The Green Flags · Green City Hackathon Heilbronn 2026</span><span>{t["front_foot_r"]}</span></div>
</section>'''

def back(t):
    steps = []
    for i, (k, h, icon, p, chips, note) in enumerate(t["steps"]):
        extra = ""
        if chips:
            extra += '<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + '</div>'
        if i == 1:
            extra += CLUSTER
        if i == 2:
            extra += '<div class="status">' + "".join(f'<span class="pill"><i style="background:{c}"></i>{s}</span>' for s, c in t["status"]) + '</div>'
            extra += f'<div class="rank">{t["rank"]}</div>'
        if note:
            extra += f'<div class="note">{note}</div>'
        steps.append(f'<div class="step"><div class="k"><span>{k}</span>{ICON[icon]}</div><h3>{h}</h3><p>{p}</p>{extra}</div>')
    today = "".join(f"<li>{x}</li>" for x in t["today"])
    c1, c2 = t["closing"]
    return f'''
<section class="page">
  <div class="back">
    <div class="head"><h2>{LEAF}{t["how_h"]}</h2><span class="tag">Sag's Heilbronn · {URL_SHORT}</span></div>
    <div class="steps">{"".join(steps)}</div>
    <div class="two">
      <div class="today"><div class="sect">{t["today_h"]}</div><ul>{today}</ul></div>
      <div class="ask"><div class="sect">{t["ask_h"]}</div><p>{t["ask"]}</p><p>{t["ask_2"]}</p></div>
    </div>
    <div class="closing"><span class="b">{{</span>{c1}<br>{c2}<span class="b">}}</span></div>
  </div>
  <div class="backfoot">
    <div><span class="l">{t["team_l"]}</span><span class="v">{t["team"]}</span></div>
    <div><span class="l">{t["event_l"]}</span><span class="v">{t["event"]}</span></div>
    <div><span class="l">{t["data_l"]}</span><span class="v">{t["data"]}</span></div>
    <div><span class="l">{t["code_l"]}</span><span class="v">{t["code"]}</span></div>
  </div>
</section>'''

def document(t):
    return f'''<!doctype html>
<html lang="{t["lang"]}"><head><meta charset="utf-8"><title>{t["title"]}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=block" rel="stylesheet">
<style>{CSS}</style></head><body>{front(t)}{back(t)}</body></html>'''

# --- write + render ----------------------------------------------------------
chrome = shutil.which("google-chrome") or shutil.which("chromium")
for lang, t in TEXT.items():
    html_path = HERE / f"handout-{lang}.html"
    html_path.write_text(document(t), encoding="utf-8")
    if chrome:
        pdf = HERE / f"handout-{lang}.pdf"
        subprocess.run([chrome, "--headless=new", "--no-pdf-header-footer", "--disable-gpu",
                        "--virtual-time-budget=15000",            # lets the Google Fonts arrive before printing
                        f"--print-to-pdf={pdf}", str(html_path)], check=True, capture_output=True)
        print(f"wrote {pdf.name}")
    print(f"wrote {html_path.name}")
if not chrome:
    print("google-chrome not found: HTML written, no PDF")
