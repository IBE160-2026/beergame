import re
from pathlib import Path
bad = 0
for d in sorted(Path('.').glob('[0-9][0-9]-*')):
    nn = d.name[:2]
    for svg in d.glob('*.svg'):
        t = svg.read_text(encoding='utf-8')
        others = {m for m in re.findall(r'(?:class|id)="[^"]*\b([de]\d\d)-', t) if m != 'e' + nn}
        wrong_class = set(re.findall(r'\.([de]\d\d)-', t)) - {'e' + nn}
        scripts = len(re.findall(r'<script|onload=|onclick=|javascript:', t, re.I))
        external = [u for u in re.findall(r'(?:href|src)="(https?:[^"]+)"', t)]
        if others or wrong_class or scripts or external:
            print(d.name, svg.name, others, wrong_class, scripts, external[:2]); bad += 1
print('krysskontaminering/skript:', bad)
