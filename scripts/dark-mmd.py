"""Writes the dark variant of a Mermaid source: the colours in classDef, style and linkStyle lines are drawn for a
white background (light fills, dark strokes and text); this keeps each hue and moves fills dark and strokes and text
light. Usage: python3 -I scripts/dark-mmd.py <in.mmd> <out.mmd>"""
import colorsys, re, sys

def tone(hexcolor, lightness, max_saturation=1.0):
    h = hexcolor.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, _, sat = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(hue, lightness, min(sat, max_saturation))
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in (r, g, b))

ROLE = {'fill': lambda c: tone(c, 0.20, 0.45), 'stroke': lambda c: tone(c, 0.65), 'color': lambda c: '#e6edf3'}
styled = re.compile(r'^\s*(classDef|style|linkStyle)\s')
prop = re.compile(r'\b(fill|stroke|color):\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b')

src, out = sys.argv[1], sys.argv[2]
lines = []
for line in open(src, encoding='utf-8'):
    if styled.match(line):
        line = prop.sub(lambda m: f'{m.group(1)}:{ROLE[m.group(1)](m.group(2))}', line)
    lines.append(line)
open(out, 'w', encoding='utf-8').write(''.join(lines))
