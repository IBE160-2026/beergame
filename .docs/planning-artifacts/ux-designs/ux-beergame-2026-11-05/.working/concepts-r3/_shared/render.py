"""Render every SVG in a concept folder to PNG with headless Edge or Chrome, and check XML.

Usage: python render.py <concept-dir> [--only NAME]
Writes <concept-dir>/_png/<name>.png. Fonts load through the SVG's own @import.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def browser():
    for candidate in CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return shutil.which("msedge") or shutil.which("chrome")


def size_of(root):
    view_box = root.get("viewBox")
    if view_box:
        _, _, width, height = [float(v) for v in re.split(r"[ ,]+", view_box.strip())]
        return int(width), int(height)
    return int(float(root.get("width", 1440))), int(float(root.get("height", 900)))


def main():
    concept = Path(sys.argv[1]).resolve()
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    out = concept / "_png"
    out.mkdir(exist_ok=True)
    exe = browser()
    if not exe:
        sys.exit("No Edge or Chrome found")
    failed = 0
    for svg in sorted(concept.glob("*.svg")):
        if only and only not in svg.name:
            continue
        try:
            root = ET.parse(svg).getroot()
        except ET.ParseError as err:
            print(f"XML-FEIL {svg.name}: {err}")
            failed += 1
            continue
        width, height = size_of(root)
        html = (
            "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;padding:0}"
            "svg{display:block;width:%dpx;height:%dpx}</style>%s" % (width, height, svg.read_text(encoding="utf-8"))
        )
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_text(html, encoding="utf-8")
            target = out / f"{svg.stem}.png"
            subprocess.run(
                [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}/profile",
                 f"--window-size={width},{height}", "--virtual-time-budget=4000",
                 f"--screenshot={target}", page.as_uri()],
                capture_output=True, timeout=120,
            )
        print(f"OK {svg.name} {width}x{height} -> {target}" if target.exists() else f"FEIL {svg.name}: no PNG")
        failed += 0 if target.exists() else 1
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
