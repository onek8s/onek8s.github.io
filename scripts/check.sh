#!/usr/bin/env bash
# CI checks for the design repository:
#  1. every diagram source (diagrams/*.mmd) has a rendering (images/*.svg) that is at least as new in Git history;
#  2. every relative Markdown link and image reference resolves to a file.
# Usage: scripts/check.sh   (run from anywhere; needs git and python3)
set -euo pipefail
cd "$(dirname "$0")/.."
status=0

echo "Diagrams: every .mmd rendered, and not newer than its .svg"
for src in diagrams/*.mmd; do
  out="images/$(basename "${src%.mmd}").svg"
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

exit $status
