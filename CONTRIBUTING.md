# Editing the pictures and the site

How this repository is edited and built. The requirements and acceptance criteria are in `requirements/` (part 0),
the design in `design/` (parts 1 to 8); both are published at [onek8s.github.io](https://onek8s.github.io/).

## Who approves what

Humans own `requirements/` and AI owns `design/` ([How we work](README.md#how-we-work-requirements-driven-collaboration)):

- A change to `requirements/` - a requirement or an acceptance criterion - needs a human's approval (`olljanat`).
  AI may propose one.
- A change to `design/`, and to the infrastructure as code in the implementation repositories, needs the AI's review
  (`olljanat-ai`): it checks that the change does not conflict with the requirements or the acceptance criteria.
  Humans may contribute.

`.github/CODEOWNERS` names the owners, and the required check **Approvals** lists the approval each changed path of a
pull request needs. The author counts as their own side's approval, and an approval is kept across later pushes that
do not touch that owner's files. A change to the requirements comes first; the design follows it in its own pull
request, and a finding in an environment that changes the design is a design pull request first.

## The pictures

Sources are Mermaid files in [`diagrams/`](diagrams); rendered SVGs live in [`images/`](images), two per
source: `<name>.svg` for light mode and `<name>.dark.svg` for dark mode. The documents link the light one; the site
shows the dark one when the page is dark (and the light one in print). After editing a source, regenerate both with:

```sh
scripts/render.sh                          # every picture
scripts/render.sh diagrams/2.2-control-plane.mmd   # or only the ones you changed
```

The dark rendering uses Mermaid's dark theme (`scripts/mermaid-dark.json`) and turns the colours of the `classDef`,
`style` and `linkStyle` lines dark (`scripts/dark-mmd.py`: the same hue, a dark fill, a light stroke and text), so
write the colours for a white background as before - one source serves both. Labels are SVG text in Arial's metrics
(`fontFamily` and `htmlLabels: false` in both settings files: Liberation Sans or Arimo where the renderer has no Arial),
because Mermaid sizes every box for the font of the machine that renders it: HTML labels in another font were cut off
in a reader's browser. A picture whose lines miss their boxes (edges to or from a subgraph) can use the ELK layout,
`config: layout: elk` in front matter on the first lines of its source, as 1.1 and 2.3 do.

`scripts/render.sh` also writes `images/<name>.drawio` for every flowchart (`scripts/drawio.py`): the light rendering
as native Draw.io shapes - boxes, subgraphs as containers, edges with their route, colours and text - for readers who
want to edit a picture. A page links it under its picture: `[Download the picture for Draw.io](../images/<name>.drawio){: download="<name>.drawio"}`.
The Mermaid source stays the master; a change made in Draw.io comes back as a change to the `.mmd`. The light rendering uses the spacing of
`scripts/mermaid.json`; keep a picture at most about 1 200 px wide (and 1 500 px tall), because the PDF scales it to
the page and the 16 px labels turn unreadable beyond that - stack subgraphs (`a ~~~ b`), keep edge labels to a few
words and prefer `flowchart TB` with two or three columns to a wide `LR` row.

A pull request fails the `Check` workflow when a `.mmd` is newer in Git than either `.svg`, when a relative link in
the documents is broken, or when the navigation and the files in `requirements/` and `design/` disagree (below); run `scripts/check.sh`
locally to see the same result.

## The site

The site is plain [GitHub Pages with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll):
the Markdown in `requirements/`, `design/`, `examples/lab/` and `README.md` is published as is, without front matter, and one
layout wraps every page; this file, `CLAUDE.md`, `archive/`, `reviews/`, `diagrams/` and `scripts/` are excluded.

**The design holds only what serves a requirement.** Every page in `design/` names the requirements of
[0.2](requirements/0.2-requirements.md) it serves on the line under its first heading -
`**Requirements:** [R4](../requirements/0.2-requirements.md#r4), [R29](../requirements/0.2-requirements.md#r29).` - and
the release notes say `**Requirements:** none - ...`. What no requirement names does not go into `design/`: it is
kept in `archive/` (since v4.0), outside the site and the PDFs, and no published page links to it; it comes back
only when a human adds the requirement that names it. The design states what is chosen, with a short reason only where
it explains how a requirement is met: it keeps no decision log, decision numbers, sign-offs or open questions (the old
decision log and open questions, pages 7.2 and 7.3, are in `archive/` for history). `scripts/check.sh` fails on a page without the line, an
R-number that 0.2 does not have, or a link into `archive/`.

| File | Holds |
|---|---|
| `_config.yml` | The title, the design's `version` (shown in the header and on the PDF's cover), the repository the "Edit this page" links point at, and what is not published (`archive/`, `CLAUDE.md`, `diagrams/`, `scripts/`, ...) |
| `_data/nav.yml` | The reading order of the pages in parts, and per page the PDF it is printed in (`pdf: requirements` or `design`; only the front page has none; it comes first and the sidebar shows it above both groups). The layout builds the sidebar (part 0 under "Requirements - owned by humans", parts 1 to 8 under "Design - owned by AI"; the [lab examples](#the-lab-examples) below them are not in this list), the part shown above each title and the previous / next links from it, and `scripts/check.sh` fails when the list and the files in `requirements/` and `design/` disagree, or when a page in `requirements/` is not `pdf: requirements` (or one outside it is) or a page in `design/` not `pdf: design` |
| `_layouts/default.html` | The page: header (with the version and the two PDF buttons), sidebar, the "On this page" list built from the h2 / h3 headings at build time, the page, previous / next; on the lab examples also Mermaid from jsDelivr |
| `assets/css/site.css` | The styles, light and dark (the reader's choice is remembered; the system setting is the default), print |
| `assets/js/site.js` | Progressive enhancements only: the theme toggle, the dark rendering of each picture in dark mode, pictures as figures with their caption and a full-screen view on click |
| `assets/js/mermaid.js` | The lab examples only: draws their Mermaid blocks in the browser, light or dark like the page, with the settings of `scripts/mermaid.json` and `scripts/mermaid-dark.json`, and opens one full screen on click (at least at the size Mermaid drew it, scrolling when wider than the window) |

To add a page: create the Markdown in `design/` with its requirements line (or, for a requirement page, in
`requirements/`, part 0), add it to `_data/nav.yml` (with `pdf: design` for every page in `design/`, `pdf: requirements`
for every page in `requirements/`), and run
`scripts/check.sh`. A page is numbered `<part>.<page>` in reading order (`2.3` is the third page of part 2, *Inside a
cluster*) and the pictures carry the number of the page that shows them, so a new page in the middle of a part
renumbers the pages after it - the files, the headings, the pictures and every "section N.M" in the text, here and in
the implementation repositories, which cite sections by number too.

## The lab examples

`examples/lab/` holds the **lab examples**: an index (`index.md`, `# Lab examples`) and a page per isolation zone
(`<zone>.md`, e.g. `# int-fi - Finland`) with a section and a Mermaid picture per application. They are generated
by the documentation agent (aks-ai-agents, `aks-agent docs lab`) from the lab's Git repositories and regenerated by
hand with aks-terraform's `Lab examples` workflow, which opens a pull request for the user to merge. **Never edit
them by hand**: the next run overwrites them. Zones come and go with the lab, so nothing outside `examples/lab/`
names them: the layout lists every page it finds there in the sidebar under "Lab examples - generated by the
documentation agent" (the index first, then the zones by file name, each titled by its first heading; no front
matter), and draws their ```` ```mermaid ```` blocks in the browser (the design's pictures stay pre-rendered SVGs).

The lab examples are not the design: no page of `README.md`, `requirements/` or `design/` links into `examples/`, and
they are in neither PDF (`_data/nav.yml` does not list them, so `scripts/pdf.py` never selects them).
`scripts/check.sh` checks their links and anchors, that the design does not link to them and that nav.yml gives
none a `pdf:`. The agent's own updates add no version to the release notes: only a change to the design does.

## The PDF and the release notes

Every publish also builds **two PDFs**: the requirements (`/onek8s-requirements.pdf`, part 0) and the design
(`/onek8s-design.pdf`, every page of `design/`, the summary 1.0 first and the release notes last, both linked as buttons at
the top of every page). Which PDF a page is in is its `pdf:` key in `_data/nav.yml` - only the front page is online
only - and `scripts/pdf.py --only <name>` selects by it.
`scripts/pdf.py` takes the built pages in the order of `_data/nav.yml`
(`--only` selects parts, part ranges or pages), puts a cover with the version and the commit and a contents list in
front, and prints them with headless Chrome, each page on a new sheet, with an outline from the headings. Links between
pages and to their headings stay links inside the PDF (each id is prefixed with its page, so the same heading on two
pages is two targets); links to pages outside a PDF's selection, and to files that are not pages, go to the site, or to
GitHub for what the site does not publish. The build fails when a link inside a PDF has no target. The `Check` workflow
builds the same PDFs on every pull request and attaches them to the run as `onek8s-design-pdf`; the requirements PDF
is `--only requirements --subtitle Requirements`.

The design is v4.0 since 2026-10-20 (the user's decision; the versions before it are in the Git tags, `v3.8` the last
of v3, `v1.15` the last of v1). A pull request that changes the design adds the next minor version (v4.1, v4.2, ...;
a major version only when a human says so) to [8.1 Release notes](design/8.1-release-notes.md) - one short sentence
per change with the link to the pull request - and sets the same `version` in `_config.yml`; `scripts/check.sh` fails
when the two disagree or an entry has no pull request link. Every version is tagged `v<version>` in every repository
at its default branch's head by aks-terraform's `Design tags` workflow (`design-tags.yml`, hourly and by hand), so
merge the code pull requests of a round before the design's.

## Building the site locally

```sh
printf 'source "https://rubygems.org"\ngem "github-pages", group: :jekyll_plugins\n' > Gemfile
bundle install
bundle exec jekyll serve   # http://127.0.0.1:4000/
```

The `github-pages` gem pins the same Jekyll and plugins GitHub Pages builds with (the Markdown without front
matter, `README.md` as the index, relative links rewritten to the published pages). `Gemfile` and `Gemfile.lock`
are not committed. The PDF from the built site:

```sh
bundle exec jekyll build
scripts/pdf.py _site _site/onek8s-design.pdf --only design   # CHROME=<path> when Chrome / Chromium is not on PATH
```
