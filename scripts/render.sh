#!/usr/bin/env bash
# Renders diagrams/*.mmd with Mermaid CLI twice: images/<name>.svg for light mode (default theme, white background,
# the spacing of scripts/mermaid.json - the pictures must stay narrow enough to be readable at the PDF's page width)
# and images/<name>.dark.svg for dark mode (scripts/mermaid-dark.json, the classDef colours turned dark by
# scripts/dark-mmd.py). The site shows the one that matches the reader's colour scheme.
# Usage: scripts/render.sh [diagrams/<name>.mmd ...]   (default: all; set PUPPETEER_CONFIG to a puppeteer JSON
# config if Chromium needs custom flags/path)
set -euo pipefail
cd "$(dirname "$0")/.."
MMDC_VERSION="11.4.2"
args=()
[[ -n "${PUPPETEER_CONFIG:-}" ]] && args+=(-p "$PUPPETEER_CONFIG")
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
(( $# )) || set -- diagrams/*.mmd
for src in "$@"; do
  name=$(basename "${src%.mmd}")
  echo "Rendering $src -> images/$name.svg, images/$name.dark.svg"
  npx -y "@mermaid-js/mermaid-cli@${MMDC_VERSION}" "${args[@]}" -c scripts/mermaid.json -b white -i "$src" -o "images/$name.svg"
  python3 -I scripts/dark-mmd.py "$src" "$tmp/$name.mmd"
  npx -y "@mermaid-js/mermaid-cli@${MMDC_VERSION}" "${args[@]}" -c scripts/mermaid-dark.json -b '#161d26' \
    -i "$tmp/$name.mmd" -o "images/$name.dark.svg"
done
