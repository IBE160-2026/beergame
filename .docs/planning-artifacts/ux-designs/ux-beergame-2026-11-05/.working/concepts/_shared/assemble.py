"""Assemble all concept folders into one gallery page.

Writes ../_dist/ (index.html plus svg/ and thumb/, fetched on demand; for publishing) and
../gallery-local.html (one file with inert <template> tags and data-URI thumbnails; opens from disk).
SVGs are inserted only when a concept is opened, so fonts and animations load on demand.
"""
import base64
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = [
    ("06-spilldynamikk", "spilldynamikk", "Spilldynamikk"),
    ("05-spill", "spill", "Spillskjermen"),
    ("07-debrief", "debrief", "Debrief"),
    ("01-landing", "landing", "Landingsside"),
    ("02-laerer-klasse", "klasse", "Faglærer: lag klasse"),
    ("03-laerer-spill", "oppsett", "Faglærer: sett opp spill"),
    ("04-student-hjem", "student", "Student"),
    ("08-laerer-oversikt", "oversikt", "Faglærer: oversikt"),
    ("09-alle-sider", "alle", "Alle sider"),
]
LABELS = ["Tese", "Spilldynamikk", "Debrief-grep", "Lærerflate-grep", "Palett", "Typografi", "Styrke", "Ærlig risiko",
          "Gjenbrukbart selv om konseptet velges bort"]


def parse_concept(text):
    title = re.search(r"^#\s+(.+)$", text, re.M).group(1).strip()
    number = re.match(r"\d+", title)
    name = re.sub(r"^\d+[\s.:-]*", "", title)
    fields = {}
    for label in LABELS:
        pattern = rf"\*\*{re.escape(label)}[^*]*?\*\*\s*(.+?)(?=\s*\*\*[A-ZÆØÅ][^*]*?:\*\*|\Z)"
        found = re.search(pattern, text, re.S)
        if found:
            fields[label] = found.group(1).strip()
    name = re.sub(r"\s*[(«].*$", "", name).strip()
    return (number.group(0) if number else ""), name, fields


def inline(text):
    out = html.escape(" ".join(text.split()), quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong></strong>", out)
    return re.sub(r"`([^`]+)`", r"<code></code>", out)


def rich(text):
    """Small Markdown subset used in concept.md: paragraphs, bullet lists, bold and code."""
    parts, bullets, para = [], [], []
    def flush():
        if para:
            parts.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if bullets:
            parts.append("<ul>" + "".join(f"<li>{inline(b)}</li>" for b in bullets) + "</ul>")
            bullets.clear()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            if para:
                flush()
            bullets.append(stripped[2:])
        elif not stripped:
            flush()
        elif bullets:
            bullets[-1] += " " + stripped
        else:
            para.append(stripped)
    flush()
    return "".join(parts)


def thumb(png):
    if not png.exists():
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "t.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-vf", "scale=620:-2", "-q:v", "6", str(out)],
                       check=True)
        return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


def size_of(svg_text):
    found = re.search(r'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', svg_text)
    return (found.group(1), found.group(2)) if found else ("16", "10")


def clean_svg(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<\?xml.*?\?>", "", text, flags=re.S)
    return text.strip()


concepts = []
for folder in sorted(p for p in ROOT.iterdir() if p.is_dir() and re.match(r"\d\d-", p.name)):
    concept_md = folder / "concept.md"
    if not concept_md.exists():
        print("MANGLER concept.md:", folder.name)
        continue
    number, name, fields = parse_concept(concept_md.read_text(encoding="utf-8"))
    number = folder.name[:2]
    pages = {}
    for stem, slug, _ in PAGES:
        svg = folder / f"{stem}.svg"
        if svg.exists():
            pages[slug] = {"svg": clean_svg(svg), "thumb": thumb(folder / "_png" / f"{stem}.png")}
        else:
            print("MANGLER", folder.name, stem)
    concepts.append({"id": number, "name": name, "fields": fields, "pages": pages})

templates, cards, sections = [], [], []
thumbs = {}
for c in concepts:
    cid = c["id"]
    thumbs[cid] = {slug: p["thumb"] for slug, p in c["pages"].items()}
    blocks = []
    for stem, slug, label in PAGES:
        if slug not in c["pages"]:
            continue
        templates.append(f'<template id="t-{cid}-{slug}">{c["pages"][slug]["svg"]}</template>')
        blocks.append(
            f'<figure class="board" id="k{cid}-{slug}" data-tpl="t-{cid}-{slug}" data-src="svg/{cid}-{slug}.svg">'
            f'<figcaption><h3>{html.escape(label)}</h3>'
            f'<button type="button" class="zoom" aria-pressed="false">Full størrelse</button></figcaption>'
            f'<div class="canvas" style="aspect-ratio:{"/".join(size_of(c["pages"][slug]["svg"]))}"></div></figure>'
        )
    f = c["fields"]
    def rows(keys):
        return "".join(f"<dt>{html.escape(k)}</dt><dd>{rich(f[k])}</dd>" for k in keys if k in f)
    lead = rows(["Spilldynamikk", "Styrke", "Ærlig risiko"])
    more = rows(["Debrief-grep", "Lærerflate-grep", "Gjenbrukbart selv om konseptet velges bort", "Palett", "Typografi"])
    jump = "".join(f'<a href="#k{cid}-{slug}">{html.escape(label)}</a>' for _, slug, label in PAGES if slug in c["pages"])
    sections.append(
        f'<section class="concept" id="konsept-{cid}" hidden>'
        f'<header class="concept-head"><div class="concept-title"><h2>{cid} {html.escape(c["name"])}</h2>'
        f'<div class="thesis">{rich(f.get("Tese", ""))}</div>'
        f'<button type="button" class="fav" data-id="{cid}" aria-pressed="false">Legg på kortlista</button></div>'
        f'<div><dl>{lead}</dl><details><summary>Debrief, lærerflate, palett og typografi</summary><dl>{more}</dl></details></div></header>'
        f'<nav class="jump" aria-label="Sider i konseptet">{jump}</nav>'
        + "".join(blocks) + "</section>"
    )
    cards.append(
        f'<a class="pick" href="#konsept-{cid}"><span class="num">{cid}</span><span class="pick-name">{html.escape(c["name"])}</span>'
        f'<span class="pick-thesis">{html.escape(f.get("Tese", ""))}</span></a>'
    )

bar = "".join(f'<a class="tab" data-c="{c["id"]}" href="#konsept-{c["id"]}" title="{html.escape(c["name"])}">{c["id"]}</a>' for c in concepts)
tabs = "".join(f'<a class="tab" href="#side-{slug}" data-slug="{slug}">{html.escape(label)}</a>' for _, slug, label in PAGES)
concept_names = {c["id"]: c["name"] for c in concepts}
meta = {"names": concept_names, "labels": {s: l for _, s, l in PAGES}}
file_thumbs = {cid: {slug: f"thumb/{cid}-{slug}.jpg" for slug in t} for cid, t in thumbs.items()}
payload_files = json.dumps({**meta, "thumbs": file_thumbs}, ensure_ascii=False).replace("</", "<\\/")
payload_inline = json.dumps({**meta, "thumbs": thumbs}, ensure_ascii=False).replace("</", "<\\/")

STYLE = """
<title>Beergame designkonsepter</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;700;800&display=swap">
<style>
/* Layout: a grey gallery wall so every concept's own colours read true. One look in both themes. */
:root { --wall:#dfe2e4; --panel:#f3f4f5; --ink:#15191d; --soft:#4a5158; --line:#b9bfc4; --mark:#15191d; --on-mark:#f3f4f5; color-scheme:light;
  --ui:'Hanken Grotesk','Segoe UI',system-ui,sans-serif; }
* { box-sizing:border-box; }
[hidden] { display:none !important; }
body { background:var(--wall); color:var(--ink); font:16px/1.5 var(--ui); margin:0; }
.wrap { max-width:1680px; margin:0 auto; padding-block:28px 80px; padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); }
h1 { font-size:clamp(28px,4vw,48px); line-height:1.05; letter-spacing:-.02em; margin:0 0 10px; font-weight:800; text-wrap:balance; }
.lede { max-width:68ch; color:var(--soft); margin:0 0 22px; }
.picks { display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:1px; background:var(--line); border:1px solid var(--line); margin-bottom:32px; }
.pick { background:var(--panel); padding:14px 16px 16px; color:inherit; text-decoration:none; display:grid; grid-template-columns:auto 1fr; column-gap:10px; align-items:baseline; min-width:0; }
.pick:hover, .pick:focus-visible { background:#fff; }
.num { font-weight:800; font-variant-numeric:tabular-nums; color:var(--soft); }
.pick-name { font-weight:800; font-size:18px; }
.pick-thesis { grid-column:1/-1; font-size:14px; color:var(--soft); margin-top:4px; }
.pick.is-fav .pick-name { text-decoration:underline; text-decoration-thickness:3px; text-underline-offset:3px; }
.tabs { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:18px; position:sticky; top:env(safe-area-inset-top,0px); background:var(--wall); padding-block:10px; z-index:5; }
.tab, .jump a { padding:7px 12px; border:1px solid var(--line); color:inherit; text-decoration:none; font-size:14px; font-weight:500; background:var(--panel); }
.tab[aria-current="page"] { background:var(--mark); color:var(--on-mark); border-color:var(--mark); }
.compare { display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,400px),1fr)); gap:18px; }
.compare a { color:inherit; text-decoration:none; background:var(--panel); display:block; min-width:0; }
.compare img { width:100%; height:auto; display:block; }
.compare .cap { padding:10px 12px; font-weight:700; }
.compare a:hover .cap, .compare a:focus-visible .cap { text-decoration:underline; }
.concept-head { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.5fr); gap:28px; background:var(--panel); padding:24px; margin-bottom:12px; }
.concept-title h2 { font-size:clamp(28px,3.4vw,44px); line-height:1.05; letter-spacing:-.02em; margin:0 0 10px; font-weight:800; text-wrap:balance; }
.thesis { font-size:19px; margin:0 0 16px; max-width:44ch; } .thesis p { margin:0; }
dl { margin:0; display:grid; grid-template-columns:max-content minmax(0,1fr); gap:6px 16px; font-size:15px; }
dt { font-weight:700; }
dd { margin:0; color:var(--soft); max-width:75ch; }
dd p { margin:0 0 6px; } dd ul { margin:0; padding-left:18px; } dd li { margin-bottom:4px; }
code { font-size:.92em; font-variant-numeric:tabular-nums; }
details { margin-top:12px; font-size:15px; } summary { cursor:pointer; font-weight:700; padding-block:4px; } details dl { margin-top:8px; }
.board, .concept { scroll-margin-top:64px; }
.jump { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:22px; }
.board { margin:0 0 30px; background:var(--panel); }
.board figcaption { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px 14px; }
.board h3 { margin:0; font-size:16px; font-weight:700; }
.canvas { overflow-x:auto; }
.canvas svg { display:block; width:100%; height:auto; }
.board.is-full .canvas svg { width:auto; max-width:none; }
button { font:inherit; font-size:14px; font-weight:500; padding:7px 12px; border:1px solid var(--ink); background:transparent; color:var(--ink); cursor:pointer; }
button:hover { background:#fff; }
button[aria-pressed="true"] { background:var(--mark); color:var(--on-mark); }
.short { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:0 0 24px; font-size:15px; }
a:focus-visible, button:focus-visible { outline:3px solid var(--ink); outline-offset:2px; }
@media (max-width:820px) { .tabs { flex-wrap:nowrap; overflow-x:auto; } .tab { flex:none; } .concept-head { grid-template-columns:minmax(0,1fr); } dl { grid-template-columns:minmax(0,1fr); } dd { margin-bottom:8px; } }
</style>
"""

BODY = f"""
<div class="wrap">
<div id="intro">
<h1>10 designkonsepter</h1>
<p class="lede">Hvert konsept har 9 skisser med samme syntetiske spill, så du sammenligner ideen og ikke tallene. Start med spilldynamikken, og åpne et konsept for å se alle sidene. Navnene er arbeidsnavn.</p>
<div class="picks">{''.join(cards)}</div>
<p class="short"><span id="shortText">Kortlista er tom. Åpne et konsept og legg det på lista.</span> <button type="button" id="copyShort" hidden>Kopier kortlista</button></p>
</div>
<nav class="tabs" id="tabs" aria-label="Sammenlign en side på tvers av konseptene">{tabs}</nav>
<nav class="tabs" id="bar" aria-label="Velg konsept" hidden><a class="tab back" href="#side-spilldynamikk">Alle konsepter</a>{bar}</nav>
<main>
<section id="compare"><div class="compare" id="compareGrid"></div></section>
{''.join(sections)}
</main>
</div>
@@TEMPLATES@@
<script type="application/json" id="gallery-data">@@PAYLOAD@@</script>
<script>
(function () {{
  var data = JSON.parse(document.getElementById('gallery-data').textContent);
  var grid = document.getElementById('compareGrid');
  var compare = document.getElementById('compare');
  var concepts = Array.prototype.slice.call(document.querySelectorAll('.concept'));
  var favKey = 'beergame-kortliste';
  function readFavs() {{ try {{ return JSON.parse(localStorage.getItem(favKey)) || []; }} catch (e) {{ return []; }} }}
  function writeFavs(list) {{ try {{ localStorage.setItem(favKey, JSON.stringify(list)); }} catch (e) {{}} }}
  var favs = readFavs();
  function renderFavs() {{
    document.querySelectorAll('.fav').forEach(function (b) {{
      var on = favs.indexOf(b.dataset.id) > -1;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.textContent = on ? 'På kortlista' : 'Legg på kortlista';
    }});
    document.querySelectorAll('.pick').forEach(function (p) {{
      p.classList.toggle('is-fav', favs.indexOf(p.getAttribute('href').slice(-2)) > -1);
    }});
    var text = favs.slice().sort().map(function (id) {{ return id + ' ' + data.names[id]; }}).join(', ');
    document.getElementById('shortText').textContent = text ? 'Kortliste: ' + text : 'Kortlista er tom. Åpne et konsept og legg det på lista.';
    document.getElementById('copyShort').hidden = !text;
  }}
  function fill(section) {{
    section.querySelectorAll('.board').forEach(function (board) {{
      var canvas = board.querySelector('.canvas');
      if (canvas.firstChild) return;
      var tpl = document.getElementById(board.dataset.tpl);
      if (tpl) {{ canvas.appendChild(tpl.content.cloneNode(true)); return; }}
      canvas.textContent = 'Laster …';
      fetch(board.dataset.src).then(function (r) {{ return r.text(); }}).then(function (t) {{ canvas.innerHTML = t; }})
        .catch(function () {{ canvas.textContent = 'Kunne ikke laste skissen. Last siden på nytt.'; }});
    }});
  }}
  function setMode(concept, id) {{
    document.getElementById('intro').hidden = concept;
    document.getElementById('tabs').hidden = concept;
    var bar = document.getElementById('bar');
    bar.hidden = !concept;
    bar.querySelectorAll('[data-c]').forEach(function (t) {{
      if (t.dataset.c === id) t.setAttribute('aria-current', 'page'); else t.removeAttribute('aria-current');
    }});
  }}
  function showCompare(slug) {{
    setMode(false);
    compare.hidden = false;
    concepts.forEach(function (s) {{ s.hidden = true; }});
    document.querySelectorAll('.tab').forEach(function (t) {{
      if (t.dataset.slug === slug) t.setAttribute('aria-current', 'page'); else t.removeAttribute('aria-current');
    }});
    grid.innerHTML = '';
    Object.keys(data.thumbs).sort().forEach(function (id) {{
      var src = data.thumbs[id][slug];
      if (!src) return;
      var a = document.createElement('a');
      a.href = '#k' + id + '-' + slug;
      var img = document.createElement('img');
      img.src = src; img.loading = 'lazy'; img.alt = data.labels[slug] + ' i konseptet ' + data.names[id];
      var cap = document.createElement('div');
      cap.className = 'cap'; cap.textContent = id + ' ' + data.names[id];
      a.appendChild(img); a.appendChild(cap); grid.appendChild(a);
    }});
  }}
  function showConcept(id, anchor) {{
    setMode(true, id);
    compare.hidden = true;
    concepts.forEach(function (s) {{ s.hidden = s.id !== 'konsept-' + id; if (!s.hidden) fill(s); }});
    var target = anchor && document.getElementById(anchor);
    if (target) target.scrollIntoView(); else window.scrollTo(0, 0);
  }}
  function route() {{
    var h = location.hash.slice(1), m;
    if ((m = h.match(/^konsept-(\\d\\d)$/))) return showConcept(m[1]);
    if ((m = h.match(/^k(\\d\\d)-([a-z]+)$/))) return showConcept(m[1], h);
    if ((m = h.match(/^side-([a-z]+)$/))) return showCompare(m[1]);
    showCompare('spilldynamikk');
  }}
  document.addEventListener('click', function (e) {{
    var zoom = e.target.closest('.zoom');
    if (zoom) {{
      var board = zoom.closest('.board');
      var on = board.classList.toggle('is-full');
      zoom.setAttribute('aria-pressed', on ? 'true' : 'false');
      var svg = board.querySelector('svg');
      if (svg && svg.viewBox && svg.viewBox.baseVal) {{ svg.style.width = on ? svg.viewBox.baseVal.width + 'px' : ''; }}
    }}
    var fav = e.target.closest('.fav');
    if (fav) {{
      var i = favs.indexOf(fav.dataset.id);
      if (i > -1) favs.splice(i, 1); else favs.push(fav.dataset.id);
      writeFavs(favs); renderFavs();
    }}
    if (e.target.id === 'copyShort' && navigator.clipboard) {{
      navigator.clipboard.writeText(document.getElementById('shortText').textContent).catch(function () {{}});
    }}
  }});
  window.addEventListener('hashchange', route);
  renderFavs();
  route();
}})();
</script>
"""

DIST = ROOT / "_dist"
shutil.rmtree(DIST, ignore_errors=True)
(DIST / "svg").mkdir(parents=True)
(DIST / "thumb").mkdir()
for c in concepts:
    for slug, page in c["pages"].items():
        (DIST / "svg" / f'{c["id"]}-{slug}.svg').write_text(page["svg"], encoding="utf-8")
        if page["thumb"]:
            (DIST / "thumb" / f'{c["id"]}-{slug}.jpg').write_bytes(base64.b64decode(page["thumb"].split(",", 1)[1]))

(DIST / "index.html").write_text(STYLE + BODY.replace("@@TEMPLATES@@", "").replace("@@PAYLOAD@@", payload_files), encoding="utf-8")
offline = BODY.replace("@@TEMPLATES@@", "".join(templates)).replace("@@PAYLOAD@@", payload_inline)
(ROOT / "gallery-local.html").write_text(
    '<!doctype html><html lang="nb"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + STYLE + "</head><body>" + offline + "</body></html>", encoding="utf-8")
print(f"{len(concepts)} konsepter; side {(DIST / 'index.html').stat().st_size / 1e3:.0f} KB; "
      f"frakoblet {(ROOT / 'gallery-local.html').stat().st_size / 1e6:.1f} MB; "
      f"{sum(1 for _ in DIST.rglob('*') if _.is_file())} filer, {sum(f.stat().st_size for f in DIST.rglob('*') if f.is_file()) / 1e6:.1f} MB")
