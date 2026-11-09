"""Replace gendered pronouns about the illustrative people. The PRD avoids them on purpose."""
import re
from pathlib import Path
SPECIFIC = [("kom inn hos ham:", "kom inn:"), ("og hun så bare", "og bare")]
GENERAL = [(r"\bhennes\b", "hens"), (r"\bhenne\b", "hen"), (r"\bhun\b", "hen"), (r"\bHun\b", "Hen"), (r"\bham\b", "hen"), (r"\bhan\b", "hen"), (r"\bHan\b", "Hen")]
changed = 0
for d in sorted(Path('.').glob('[0-9][0-9]-*')):
    for f in list(d.glob('*.svg')) + list(d.glob('*.md')) + list(d.glob('*.py')):
        t = o = f.read_text(encoding='utf-8')
        for a, b in SPECIFIC:
            t = t.replace(a, b)
        for a, b in GENERAL:
            t = re.sub(a, b, t)
        if t != o:
            f.write_text(t, encoding='utf-8'); changed += 1
            if f.suffix == '.py':
                compile(t, str(f), 'exec')
print('endrede filer', changed)
