"""Scan visible SVG text for product-truth breaches outside the Debrief."""
import re, sys, xml.etree.ElementTree as ET
from pathlib import Path
NS='{http://www.w3.org/2000/svg}'
def texts(path):
    root=ET.parse(path).getroot()
    for el in root.iter():
        if el.tag in (NS+'text',):
            t=' '.join(''.join(el.itertext()).split())
            if t: yield t
RULES=[
 ('navn', r'beer\s*game|ølspill|\bøl\b|\bbeer\b', ['01','02','03','04','05','06','08','09']),
 ('bullwhip', r'bullwhip|piskesnert', ['01','02','03','04','05','06','08']),
 ('kjønn', r'\b(hun|han|henne|ham|hennes|hans)\b', ['01','02','03','04','05','06','07','08','09','10']),
 ('fasit', r'anbefalt ordre|riktig ordre|du bør bestille|optimal', ['05','06']),
 ('ukeslutt', r'\b\d+\s*(av|/)\s*36\b|36\s*uker|gjenstår|uker igjen', ['01','04','05','06']),
 ('etterspørsel', r'4\s*(→|til|->)\s*8|hopper|etterspørsel', ['01','04','05','06']),
 ('rangering', r'rangering|topplist|high\s*score|vinner|premie', ['01','04','05','06','07']),
 ('læringspåstand', r'lærer mer|bedre læring|dokumentert effekt|forskning viser|kunder|sitat', ['01']),
 ('grade', r'karakter\s+[A-F]\b', ['01','05','06','07']),
]
hits=0
for d in sorted(Path('.').glob('[0-9][0-9]-*')):
    for svg in sorted(d.glob('*.svg')):
        p=svg.name[:2]
        for t in texts(svg):
            for name,pat,pages in RULES:
                if p in pages and re.search(pat,t,re.I):
                    print(f'{d.name[:2]}/{p} [{name}] {t[:150]}'); hits+=1
print('treff:',hits)
