"""Sjekker SVG-ene i denne mappa: produktsannheter (logikken fra ../concepts-r3/_shared/truthscan.py),
prefiks v-, ingen rester av e04-/e08-/d02-, ingen skript eller eksterne bilder, og ingen tekst under 9 px
(utenom kontaktarket 09). Kjør: uv run python sjekk.py"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"
HERE = Path(__file__).resolve().parent
RULES = [
    ("navn", r"beer\s*game|ølspill|\bøl\b|\bbeer\b", ["01", "02", "03", "04", "05", "06", "08", "09"]),
    ("bullwhip", r"bullwhip|piskesnert", ["01", "02", "03", "04", "05", "06", "08"]),
    ("kjønn", r"\b(hun|han|henne|ham|hennes|hans)\b", ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]),
    ("fasit", r"anbefalt ordre|riktig ordre|du bør bestille|optimal", ["05", "06"]),
    ("ukeslutt", r"\b\d+\s*(av|/)\s*36\b|36\s*uker|gjenstår|uker igjen", ["01", "04", "05", "06"]),
    ("etterspørsel", r"4\s*(→|til|->)\s*8|hopper|etterspørsel", ["01", "04", "05", "06"]),
    ("rangering", r"rangering|topplist|high\s*score|vinner|premie", ["01", "04", "05", "06", "07"]),
    ("læringspåstand", r"lærer mer|bedre læring|dokumentert effekt|forskning viser|kunder|sitat", ["01"]),
    ("grade", r"karakter\s+[A-F]\b", ["01", "05", "06", "07"]),
]
hits = 0
svgs = sorted(HERE.glob("[0-9][0-9]-*.svg"))
assert len(svgs) == 10, len(svgs)
for svg in svgs:
    p = svg.name[:2]
    raw = svg.read_text(encoding="utf-8")
    root = ET.fromstring(raw)
    for el in root.iter(NS + "text"):
        t = " ".join("".join(el.itertext()).split())
        for name, pat, pages in RULES:
            if t and p in pages and re.search(pat, t, re.I):
                print(f"{p} [{name}] {t[:150]}"); hits += 1
    for c in re.findall(r'class="([^"]+)"', raw):
        if not c.startswith("v-"):
            print(p, "klasse uten v-:", c); hits += 1
    for i in re.findall(r'id="([^"]+)"', raw):
        if not i.startswith(f"v-{svg.stem}-"):
            print(p, "id uten v-<side>-:", i); hits += 1
    if re.search(r"\b(e04|e08|d02)-", raw):
        print(p, "gammelt prefiks"); hits += 1
    if re.search(r"<script|onload=|onclick=|javascript:", raw, re.I) or re.search(r'(?:href|src)="https?:', raw):
        print(p, "skript eller ekstern ressurs"); hits += 1
    if p != "09":
        small = [float(s) for s in re.findall(r'font-size="([0-9.]+)"', raw) if float(s) < 9]
        if small:
            print(p, "tekst under 9 px:", sorted(set(small))); hits += 1
for py in HERE.glob("*.py"):
    if py.name != "sjekk.py" and re.search(r"\b(e04|e08|d02)-|e04lib|e08grid|e08lib", py.read_text(encoding="utf-8")):
        print(py.name, "gammelt prefiks i koden"); hits += 1
print("treff:", hits)
sys.exit(1 if hits else 0)
