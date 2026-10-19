#!/usr/bin/env bash
# CI checks for the design repository:
#  1. every diagram source (diagrams/*.mmd) has a light and a dark rendering (images/<name>.svg, images/<name>.dark.svg)
#     that are at least as new in Git history;
#  2. every relative Markdown link and image reference resolves to a file;
#  3. the navigation (_data/nav.yml), the Contents of README.md and the files in docs/ agree, every page's
#     <part>.<page> number is the same in its file name, its first heading and the navigation, and README.md marks
#     (PDF) exactly the pages whose `pdf:` is `design`;
#  4. the newest version in docs/8.1-release-notes.md is the version in _config.yml, and every entry links a pull request.
# Usage: scripts/check.sh   (run from anywhere; needs git and python3)
set -euo pipefail
cd "$(dirname "$0")/.."
status=0

echo "Diagrams: every .mmd rendered for light and dark, and not newer than either .svg"
for src in diagrams/*.mmd; do
 for out in "images/$(basename "${src%.mmd}").svg" "images/$(basename "${src%.mmd}").dark.svg"; do
  if [[ ! -f "$out" ]]; then
    echo "  MISSING  $out (render with scripts/render.sh)"; status=1; continue
  fi
  # Uncommitted or staged changes to the source count as "newer".
  if ! git diff --quiet HEAD -- "$src" 2>/dev/null; then
    echo "  STALE    $src changed in the working tree; run scripts/render.sh"; status=1; continue
  fi
  src_time=$(git log -1 --format=%ct -- "$src" 2>/dev/null || echo 0)
  out_time=$(git log -1 --format=%ct -- "$out" 2>/dev/null || echo 0)
  if (( src_time > out_time )); then
    echo "  STALE    $src ($(date -u -d @"$src_time" +%F)) is newer than $out ($(date -u -d @"$out_time" +%F)); run scripts/render.sh"
    status=1
  fi
 done
done

echo "Links: every relative link and image in *.md resolves"
python3 -I - <<'PY' || status=1
import os, re, sys
link = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)\)')
bad = 0
files = ['README.md'] + sorted(os.path.join('docs', f) for f in os.listdir('docs') if f.endswith('.md'))
for path in files:
    base = os.path.dirname(path)
    text = open(path, encoding='utf-8').read()
    anchors = {h.strip().lower() for h in re.findall(r'^#+\s+(.*)$', text, re.M)}
    for target in link.findall(text):
        if target.startswith(('http://', 'https://', 'mailto:')):
            continue
        file_part, _, anchor = target.partition('#')
        resolved = path if file_part == '' else os.path.normpath(os.path.join(base, file_part))
        if file_part and not os.path.exists(resolved):
            print(f'  BROKEN   {path}: {target}'); bad += 1
            continue
        if anchor and resolved.endswith('.md') and os.path.exists(resolved):
            other = open(resolved, encoding='utf-8').read()
            heads = re.findall(r'^#+\s+(.*)$', other, re.M)
            slugs = set()
            for h in heads:
                h = re.sub(r'`', '', h)
                h = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', h)
                s = re.sub(r'[^\w\- ]', '', h.lower()).strip().replace(' ', '-')
                slugs.add(s)
            if anchor not in slugs:
                print(f'  ANCHOR   {path}: {target}'); bad += 1
sys.exit(1 if bad else 0)
PY

echo "Navigation: _data/nav.yml, the Contents of README.md and docs/*.md agree"
python3 -I - <<'PY' || status=1
import os, re, sys
bad = 0
def fail(msg):
    global bad
    print(f'  NAV      {msg}'); bad += 1
# _data/nav.yml is simple enough to read without a YAML library: parts with pages of path / number / title.
nav = []
for line in open('_data/nav.yml', encoding='utf-8'):
    m = re.match(r'\s+- path: (\S+)', line)
    if m:
        nav.append({'path': m.group(1)})
        continue
    m = re.match(r'\s+number: "(\d+\.\d+)"', line)
    if m and nav:
        nav[-1]['number'] = m.group(1)
    m = re.match(r'\s+pdf: (\w+)', line)
    if m and nav:
        nav[-1]['pdf'] = m.group(1)
        if m.group(1) not in ('design', 'summary', 'reference'):
            fail(f'{nav[-1]["path"]}: pdf: {m.group(1)} is not design, summary or reference')
paths = [item['path'] for item in nav]
for path in paths:
    if not os.path.exists(path):
        fail(f'_data/nav.yml lists {path}, which does not exist')
    if paths.count(path) > 1:
        fail(f'_data/nav.yml lists {path} more than once')
docs = sorted('docs/' + f for f in os.listdir('docs') if f.endswith('.md'))
readme = open('README.md', encoding='utf-8').read()
linked = set(re.findall(r'\]\((docs/[^)#\s]+)', readme))
for doc in docs:
    if doc not in paths:
        fail(f'{doc} is not in _data/nav.yml')
    if doc not in linked:
        fail(f'{doc} is not linked from the Contents of README.md')
    marked = re.search(r'\]\(' + re.escape(doc) + r'\) \(PDF\)', readme) is not None
    in_design = next((i.get('pdf') == 'design' for i in nav if i['path'] == doc), False)
    if marked != in_design:
        fail(f'{doc}: README.md marks it {"(PDF)" if marked else "online only"}, _data/nav.yml says '
             f'{"pdf: design" if in_design else "it is not in the design PDF"}')
    number = re.match(r'docs/(\d+\.\d+)-', doc)
    item = next((i for i in nav if i['path'] == doc), None)
    if not number:
        fail(f'{doc}: the file name does not start with a <part>.<page> number')
        continue
    if item is not None and item.get('number') != number.group(1):
        fail(f'{doc}: number in _data/nav.yml is {item.get("number")}, the file name says {number.group(1)}')
    heading = open(doc, encoding='utf-8').readline().strip()
    if not heading.startswith(f'# {number.group(1)} '):
        fail(f'{doc}: the first heading does not start with "# {number.group(1)} "')
if 'README.md' not in paths:
    fail('README.md is not in _data/nav.yml')
sys.exit(1 if bad else 0)
PY

echo "Release notes: the newest version is _config.yml's, every entry links its pull request"
python3 -I - <<'PY' || status=1
import re, sys
bad = 0
version = re.search(r'^version:\s*"?([^"\n]+)"?', open('_config.yml', encoding='utf-8').read(), re.M)
notes = open('docs/8.1-release-notes.md', encoding='utf-8').read()
versions = re.findall(r'^## v(\d+\.\d+) - \d{4}-\d{2}-\d{2}$', notes, re.M)
if not version or not versions or versions[0] != version[1].strip():
    print(f'  NOTES    _config.yml version {version[1] if version else "(none)"} is not the newest release note '
          f'(v{versions[0] if versions else "?"})'); bad += 1
if len(set(versions)) != len(versions):
    print('  NOTES    a version is listed twice'); bad += 1
# An entry is a list item, up to the next item or heading.
for entry in re.findall(r'^- .*?(?=^- |^#|\Z)', notes, re.M | re.S):
    if not re.search(r'\(https://github\.com/onek8s/[^)]+/pull/\d+\)', entry):
        print(f'  NOTES    no pull request link: {entry.splitlines()[0]}'); bad += 1
sys.exit(1 if bad else 0)
PY

exit $status
