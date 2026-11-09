"""Kontroll mot brief-ens forbud. Kjøres etter bygg."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NS = "{http://www.w3.org/2000/svg}"
files = sorted(ROOT.glob("*.svg"))
print(len(files), "SVG-er")
BAN_FONTS = ["Fraunces", "Playfair", "Cormorant", "Lora", "Crimson", "Newsreader", "Syne", "Space Grotesk", "Space Mono", "IBM Plex", "Inter", "DM Sans", "DM Serif", "Outfit", "Plus Jakarta", "Instrument Sans"]
problems = 0
for f in files:
    raw = f.read_text(encoding="utf-8")
    root = ET.fromstring(raw)
    texts = ["".join(t.itertext()) for t in root.iter(NS + "text")]
    joined = "\n".join(texts)
    issues = []
    if root.find(NS + "title") is None or root.find(NS + "desc") is None:
        issues.append("mangler title/desc")
    if "<script" in raw:
        issues.append("script")
    if re.search(r"bullwhip", raw, re.I):
        issues.append("bullwhip")
    if re.search(r"Beer Game|ølspill|\bøl\b", joined, re.I) and "07-" not in f.name:
        issues.append("spillnavnet før Debrief")
    if re.search(r"\b\d+ av 36\b", joined):
        issues.append("framdrift")
    for font in BAN_FONTS:
        if re.search(r"family=" + font.replace(" ", r"\+"), raw) or f"'{font}'" in raw:
            issues.append("font " + font)
    bad_ids = [e.get("id") for e in root.iter() if e.get("id") and not e.get("id").startswith("d08-")]
    bad_cls = [e.get("class") for e in root.iter() if e.get("class") and not e.get("class").startswith("d08-")]
    if bad_ids or bad_cls:
        issues.append(f"prefiks {bad_ids[:3]} {bad_cls[:3]}")
    if re.search(r"[←-⇿☀-➿]|[\U0001F300-\U0001FAFF]", joined):
        issues.append("unicode-ikon")
    if "!" in joined:
        issues.append("utropstegn")
    if re.search(r"lorem", joined, re.I):
        issues.append("lorem")
    # Tekst utenfor lerretet
    vb = [float(x) for x in root.get("viewBox").split()]
    W, H = vb[2], vb[3]
    # Bare toppnivå: tekst uten transform-forelder
    for g in root:
        if g.tag == NS + "text":
            x, y = float(g.get("x")), float(g.get("y"))
            if x > W or y > H or x < 0 or y < 0:
                issues.append(f"utenfor lerret: {''.join(g.itertext())[:30]}")
    empties = [t for t in texts if not t.strip()]
    if empties:
        issues.append(f"{len(empties)} tomme tekster")
    print(("OK  " if not issues else "FEIL"), f.name, "; ".join(issues))
    problems += bool(issues)
print("Problemer:", problems)
# Telefonskjermer: minste skrift i 04
raw = (ROOT / "04-student-hjem.svg").read_text(encoding="utf-8")
print("minste skrift i 04:", min(float(x) for x in re.findall(r'font-size="([\d.]+)"', raw)))
raw = (ROOT / "05-spill.svg").read_text(encoding="utf-8")
print("minste skrift i 05:", min(float(x) for x in re.findall(r'font-size="([\d.]+)"', raw)))
