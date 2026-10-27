#!/usr/bin/env python3
"""Writes images/<name>.drawio, an editable Draw.io (diagrams.net) copy of a picture, from the light rendering
images/<name>.svg that scripts/render.sh made and its source diagrams/<name>.mmd: every node, subgraph and edge
becomes a native Draw.io shape at the place Mermaid drew it, with its colours, line style, arrows and text.

Usage: scripts/drawio.py diagrams/<name>.mmd ...   (render.sh runs it after each rendering)

Flowcharts and sequence diagrams (others are skipped); the labels must be SVG text (htmlLabels false in
scripts/mermaid.json).
"""
import base64
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = '{http://www.w3.org/2000/svg}'
FONT = 'Arial'
# Mermaid's default theme, for the shapes no classDef or linkStyle colours.
NODE = {'fill': '#ECECFF', 'stroke': '#9370DB'}
CLUSTER = {'fill': '#ffffde', 'stroke': '#aaaa33'}
EDGE = '#333333'
TEXT = '#333333'
ARROWS = {'pointEnd': 'block', 'pointStart': 'block', 'crossEnd': 'cross', 'crossStart': 'cross',
          'circleEnd': 'oval', 'circleStart': 'oval'}


def classes(el):
    return (el.get('class') or '').split()


def translate(el):
    m = re.search(r'translate\(\s*([-\d.e]+)[ ,]+([-\d.e]+)\s*\)', el.get('transform') or '')
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


def style_of(el):
    """The inline style as a dict; Mermaid repeats properties, the last one wins."""
    out = {}
    for part in (el.get('style') or '').split(';'):
        if ':' in part:
            k, v = part.split(':', 1)
            out[k.strip()] = v.replace('!important', '').strip()
    return out


def text_of(el):
    """The lines of a label: one per tspan row."""
    rows = [t for t in el.iter(SVG + 'tspan') if 'row' in classes(t)]
    if not rows:
        return ' '.join(''.join(el.itertext()).split())
    return '\n'.join(' '.join(''.join(r.itertext()).split()) for r in rows)


def walk(el, ox=0.0, oy=0.0, out=None):
    """Every element with its absolute offset (the sum of its ancestors' translations)."""
    out = [] if out is None else out
    dx, dy = translate(el)
    out.append((el, ox, oy))
    for child in el:
        walk(child, ox + dx, oy + dy, out)
    return out


def subgraphs(source):
    """Subgraph id -> (title, parent subgraph) and node id -> its subgraph, from the Mermaid source."""
    graphs, parent_of, stack = {}, {}, []
    for line in source.splitlines():
        line = line.strip()
        m = re.match(r'subgraph\s+([\w-]+)\s*(?:\["(.*)"\]|\[(.*)\])?', line)
        if m:
            sid = m.group(1)
            graphs[sid] = (html.unescape(m.group(2) or m.group(3) or sid), stack[-1] if stack else None)
            stack.append(sid)
        elif line == 'end' and stack:
            stack.pop()
        elif stack and not line.startswith(('%%', 'direction', 'classDef', 'class ', 'style', 'linkStyle')):
            for nid in re.findall(r'(?:^|[\s&])([A-Za-z_][\w-]*)\s*(?=[\[\(\{>]|$|\s*&)', line):
                parent_of.setdefault(nid, stack[-1])
    return graphs, parent_of


def convert(mmd):
    name = Path(mmd).stem
    root = ET.parse(Path('images') / f'{name}.svg').getroot()
    graphs, parent_of = subgraphs(Path(mmd).read_text())
    elements = walk(root)
    boxes = {}  # id -> (x, y, w, h) absolute
    cells = []  # (id, parent, kind, attrs)

    # Subgraphs: Mermaid's cluster ids are not the source ids, so match by title.
    for el, ox, oy in elements:
        if el.tag != SVG + 'g' or 'cluster' not in classes(el):
            continue
        rect = el.find(SVG + 'rect')
        label = el.find(SVG + "g[@class='cluster-label']")
        title = text_of(label) if label is not None else ''
        sid = next((k for k, (t, _) in graphs.items() if ' '.join(t.split()) == title and k not in boxes), None)
        if sid is None or rect is None:
            continue
        dx, dy = translate(el)
        x, y = ox + dx + float(rect.get('x')), oy + dy + float(rect.get('y'))
        boxes[sid] = (x, y, float(rect.get('width')), float(rect.get('height')))
        st = {**CLUSTER, **style_of(rect)}
        cells.append((sid, graphs[sid][1], 'cluster', {'value': title, 'fill': st['fill'], 'stroke': st['stroke']}))

    # Nodes.
    for el, ox, oy in elements:
        if el.tag != SVG + 'g' or 'node' not in classes(el) or not el.get('id'):
            continue
        m = re.match(r'(?:.*-)?flowchart-(.+)-\d+$', el.get('id'))
        if not m:
            continue
        nid = m.group(1)
        dx, dy = translate(el)
        cx, cy = ox + dx, oy + dy
        shape = next((c for c in el if c.tag in (SVG + 'rect', SVG + 'circle', SVG + 'polygon', SVG + 'path')), None)
        if shape is None:
            continue
        if shape.tag == SVG + 'circle':
            r = float(shape.get('r'))
            box, kind = (cx - r, cy - r, 2 * r, 2 * r), 'ellipse'
        elif shape.tag == SVG + 'rect':
            w, h = float(shape.get('width')), float(shape.get('height'))
            box = (cx + float(shape.get('x')), cy + float(shape.get('y')), w, h)
            kind = 'rounded' if float(shape.get('rx') or 0) > 0 else 'rect'
        else:
            pts = [float(v) for v in re.findall(r'-?[\d.]+(?:e-?\d+)?', shape.get('points') or shape.get('d') or '')]
            xs, ys = pts[0::2], pts[1::2]
            sx, sy = translate(shape)
            box = (cx + sx + min(xs), cy + sy + min(ys), max(xs) - min(xs), max(ys) - min(ys))
            kind = 'rhombus'
        st = {**NODE, **style_of(shape)}
        label = el.find(SVG + "g[@class='label']")
        color = style_of(label).get('color', TEXT) if label is not None else TEXT
        boxes[nid] = box
        cells.append((nid, parent_of.get(nid), kind, {'value': text_of(label) if label is not None else '',
                                                     'fill': st['fill'], 'stroke': st['stroke'], 'color': color}))

    # Edges: L_<from>_<to>_<n>[_<m>]; the ends are nodes or subgraphs.
    labels = {}
    for el, ox, oy in elements:
        if el.tag == SVG + 'g' and 'label' in classes(el) and el.get('data-id'):
            labels[el.get('data-id')] = text_of(el)
    ids = sorted(boxes, key=len, reverse=True)
    edges = []
    for el, ox, oy in elements:
        if el.tag != SVG + 'path' or not el.get('data-id') or 'flowchart-link' not in classes(el):
            continue
        eid = el.get('data-id')
        rest = eid[2:]
        src = next((i for i in ids if rest.startswith(i + '_')), None)
        dst = next((i for i in ids if src and re.match(re.escape(i) + r'(_\d+)+$', rest[len(src) + 1:])), None)
        if not src or not dst:
            continue
        pts = json.loads(base64.b64decode(el.get('data-points') or 'W10='))
        pts = [(ox + p['x'], oy + p['y']) for p in pts]
        st = style_of(el)
        cls = classes(el)
        width = st.get('stroke-width', '3.5' if 'edge-thickness-thick' in cls else '1').replace('px', '')
        dash = st.get('stroke-dasharray')
        if not dash and 'edge-pattern-dotted' in cls[:4]:
            dash = '2 2'
        elif not dash and 'edge-pattern-dashed' in cls[:4]:
            dash = '3 3'
        ends = {}
        for attr, key in (('marker-start', 'startArrow'), ('marker-end', 'endArrow')):
            m = re.search(r'flowchart-v2-(\w+?)(?:__|\))', el.get(attr) or '')
            ends[key] = ARROWS.get(m.group(1), 'none') if m else 'none'
        edges.append((eid, src, dst, pts, {'stroke': st.get('stroke', EDGE), 'width': width, 'dash': dash,
                                           'value': labels.get(eid, ''), **ends}))

    return mxfile(name, cells, boxes, edges)


def mxfile(name, cells, boxes, edges):
    mxf, top = model(name)
    font = f'fontFamily={FONT};fontSize=16;html=0;whiteSpace=wrap;'

    def cid(i):
        return 'n-' + i

    # Parents before children, so Draw.io nests them.
    order = []
    pending = list(cells)
    while pending:
        placed = {c[0] for c in order}
        ready = [c for c in pending if not c[1] or c[1] in placed or c[1] not in boxes]
        ready = ready or pending
        order += ready
        pending = [c for c in pending if c not in ready]

    for i, parent, kind, a in order:
        x, y, w, h = boxes[i]
        if parent in boxes:
            px, py, _, _ = boxes[parent]
            x, y = x - px, y - py
        if kind == 'cluster':
            style = (f'rounded=0;container=1;collapsible=0;verticalAlign=top;fillColor={a["fill"]};'
                     f'strokeColor={a["stroke"]};fontColor={TEXT};{font}')
        else:
            shape = {'ellipse': 'shape=ellipse;perimeter=ellipsePerimeter;',
                     'rhombus': 'shape=rhombus;perimeter=rhombusPerimeter;', 'rounded': 'rounded=1;'}.get(kind, 'rounded=0;')
            style = f'{shape}fillColor={a["fill"]};strokeColor={a["stroke"]};fontColor={a["color"]};{font}'
        cell = ET.SubElement(top, 'mxCell', id=cid(i), value=a['value'], style=style, vertex='1',
                             parent=cid(parent) if parent in boxes else '1')
        ET.SubElement(cell, 'mxGeometry', x=f'{x:.1f}', y=f'{y:.1f}', width=f'{w:.1f}', height=f'{h:.1f}',
                      **{'as': 'geometry'})

    for eid, src, dst, pts, a in edges:
        style = (f'edgeStyle=none;rounded=1;html=0;strokeColor={a["stroke"]};strokeWidth={a["width"]};'
                 f'endArrow={a["endArrow"]};startArrow={a["startArrow"]};endFill=1;startFill=1;'
                 f'fontFamily={FONT};fontSize=16;fontColor={TEXT};labelBackgroundColor=#ffffff;')
        # Pin both ends where Mermaid drew them, as fractions of the shape's box.
        for (px, py), end in ((pts[0], 'exit'), (pts[-1], 'entry')) if pts else ():
            x, y, w, h = boxes[src if end == 'exit' else dst]
            fx, fy = min(max((px - x) / w, 0), 1), min(max((py - y) / h, 0), 1)
            style += f'{end}X={fx:.3f};{end}Y={fy:.3f};{end}Dx=0;{end}Dy=0;{end}Perimeter=0;'
        if a['dash']:
            style += f'dashed=1;dashPattern={" ".join(a["dash"].replace(",", " ").split())};'
        cell = ET.SubElement(top, 'mxCell', id='e-' + eid, value=a['value'], style=style, edge='1', parent='1',
                             source=cid(src), target=cid(dst))
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
        if pts:
            ET.SubElement(geo, 'mxPoint', x=f'{pts[0][0]:.1f}', y=f'{pts[0][1]:.1f}', **{'as': 'sourcePoint'})
            ET.SubElement(geo, 'mxPoint', x=f'{pts[-1][0]:.1f}', y=f'{pts[-1][1]:.1f}', **{'as': 'targetPoint'})
        if len(pts) > 2:
            arr = ET.SubElement(geo, 'Array', **{'as': 'points'})
            for x, y in pts[1:-1]:
                ET.SubElement(arr, 'mxPoint', x=f'{x:.1f}', y=f'{y:.1f}')

    ET.indent(mxf)
    return ET.tostring(mxf, encoding='unicode') + '\n'


def sequence(mmd):
    """A sequence diagram: participants, lifelines, notes, and messages with their numbers and text where Mermaid drew
    them (the text and the numbers are shapes of their own, so they stay where they were)."""
    name = Path(mmd).stem
    elements = walk(ET.parse(Path('images') / f'{name}.svg').getroot())
    mxf, top = model(name)
    font = f'fontFamily={FONT};fontSize=16;html=0;whiteSpace=wrap;fontColor={TEXT};'
    count = [0]

    def vertex(value, style, x, y, w, h):
        count[0] += 1
        cell = ET.SubElement(top, 'mxCell', id=f'v{count[0]}', value=value, style=style, vertex='1', parent='1')
        ET.SubElement(cell, 'mxGeometry', x=f'{x:.1f}', y=f'{y:.1f}', width=f'{w:.1f}', height=f'{h:.1f}',
                      **{'as': 'geometry'})

    def edge(pts, style):
        count[0] += 1
        cell = ET.SubElement(top, 'mxCell', id=f'e{count[0]}', value='', style=style, edge='1', parent='1')
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
        ET.SubElement(geo, 'mxPoint', x=f'{pts[0][0]:.1f}', y=f'{pts[0][1]:.1f}', **{'as': 'sourcePoint'})
        ET.SubElement(geo, 'mxPoint', x=f'{pts[-1][0]:.1f}', y=f'{pts[-1][1]:.1f}', **{'as': 'targetPoint'})
        if len(pts) > 2:
            arr = ET.SubElement(geo, 'Array', **{'as': 'points'})
            for x, y in pts[1:-1]:
                ET.SubElement(arr, 'mxPoint', x=f'{x:.1f}', y=f'{y:.1f}')

    def lines(texts):
        return '\n'.join(' '.join(''.join(t.itertext()).split()) for t in texts)

    # Participant names: Mermaid writes them as texts over the boxes, top and bottom.
    names = [(ox + float(t.get('x')), oy + float(t.get('y')), t) for t, ox, oy in elements
             if t.tag == SVG + 'text' and 'actor-box' in classes(t)]
    pending = []  # the lines of a message's text, written before its arrow
    for el, ox, oy in elements:
        cls = classes(el)
        if el.tag == SVG + 'rect' and 'actor' in cls:
            x, y = ox + float(el.get('x')), oy + float(el.get('y'))
            w, h = float(el.get('width')), float(el.get('height'))
            label = lines([t for tx, ty, t in names if x <= tx <= x + w and y <= ty <= y + h])
            vertex(label, f'rounded=1;arcSize=5;fillColor={el.get("fill")};strokeColor={el.get("stroke")};{font}',
                   x, y, w, h)
        elif el.tag == SVG + 'line' and 'actor-line' in cls:
            edge([(ox + float(el.get('x1')), oy + float(el.get('y1'))),
                  (ox + float(el.get('x2')), oy + float(el.get('y2')))],
                 f'endArrow=none;strokeColor={el.get("stroke") or "#999"};strokeWidth=0.5;')
        elif el.tag == SVG + 'g' and el.get('data-et') == 'note':
            rect = el.find(SVG + 'rect')
            vertex(lines(el.findall(SVG + 'text')),
                   f'rounded=0;fillColor={rect.get("fill")};strokeColor={rect.get("stroke")};{font}',
                   ox + float(rect.get('x')), oy + float(rect.get('y')), float(rect.get('width')),
                   float(rect.get('height')))
        elif el.tag == SVG + 'text' and 'messageText' in cls:
            pending.append((ox + float(el.get('x')), oy + float(el.get('y')), el))
        elif el.get('data-et') == 'message':
            if el.tag == SVG + 'line':
                pts = [(ox + float(el.get('x1')), oy + float(el.get('y1'))),
                       (ox + float(el.get('x2')), oy + float(el.get('y2')))]
            else:  # a message to itself: a loop to the right
                xy = [float(v) for v in re.findall(r'-?[\d.]+', el.get('d'))]
                (x0, y0), (x1, _), (x3, y3) = (xy[0], xy[1]), (xy[2], xy[3]), (xy[-2], xy[-1])
                pts = [(ox + x0, oy + y0), (ox + x1 - 20, oy + y0), (ox + x1 - 20, oy + y3), (ox + x3, oy + y3)]
            style = f'endArrow=block;endFill=1;strokeColor={EDGE};strokeWidth=1.5;rounded=0;'
            if 'dasharray' in (el.get('style') or ''):
                style += 'dashed=1;dashPattern=3 3;'
            edge(pts, style)
            if pending:
                text = lines([t for _, _, t in pending])
                w = max(len(line) for line in text.split('\n')) * 8.6 + 10
                vertex(text, f'text;strokeColor=none;fillColor=none;align=center;verticalAlign=top;{font}', pending[0][0] - w / 2,
                       pending[0][1] + 4, w, 18 * len(pending) + 4)
                pending = []
        elif el.tag == SVG + 'text' and 'sequenceNumber' in cls:
            x, y = ox + float(el.get('x')), oy + float(el.get('y'))
            vertex(''.join(el.itertext()), f'shape=ellipse;perimeter=ellipsePerimeter;fillColor={EDGE};strokeColor={EDGE};fontColor=#ffffff;'
                   f'fontFamily={FONT};fontSize=12;html=0;', x - 9, y - 13, 18, 18)

    ET.indent(mxf)
    return ET.tostring(mxf, encoding='unicode') + '\n'


def model(name):
    """An empty Draw.io file: its root element and the parent of every cell."""
    mxf = ET.Element('mxfile', host='onek8s scripts/drawio.py')
    diagram = ET.SubElement(mxf, 'diagram', name=name, id=name)
    graph = ET.SubElement(diagram, 'mxGraphModel', grid='1', gridSize='10', guides='1', page='0', math='0',
                          shadow='0')
    top = ET.SubElement(graph, 'root')
    ET.SubElement(top, 'mxCell', id='0')
    ET.SubElement(top, 'mxCell', id='1', parent='0')
    return mxf, top


if __name__ == '__main__':
    for src in sys.argv[1:]:
        out = Path('images') / f'{Path(src).stem}.drawio'
        kind = ET.parse(out.with_suffix('.svg')).getroot().get('aria-roledescription', '')
        if kind not in ('flowchart-v2', 'sequence'):
            print(f'Skipped {out}: a {kind}, neither a flowchart nor a sequence diagram')
            continue
        out.write_text(sequence(src) if kind == 'sequence' else convert(src))
        print(f'Wrote {out}')
