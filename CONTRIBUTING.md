# Editing the pictures and the site

How this repository is edited and built; the design itself is in `docs/` and published at
[onek8s.github.io](https://onek8s.github.io/).

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
write the colours for a white background as before - one source serves both. The light rendering uses the spacing of
`scripts/mermaid.json`; keep a picture at most about 1 200 px wide (and 1 500 px tall), because the PDF scales it to
the page and the 16 px labels turn unreadable beyond that - stack subgraphs (`a ~~~ b`), keep edge labels to a few
words and prefer `flowchart TB` with two or three columns to a wide `LR` row.

A pull request fails the `Check` workflow when a `.mmd` is newer in Git than either `.svg`, when a relative link in
the documents is broken, or when the navigation and the files in `docs/` disagree (below); run `scripts/check.sh`
locally to see the same result.

## The site

The site is plain [GitHub Pages with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll):
the Markdown in `docs/` and `README.md` is published as is, without front matter, and one layout wraps every page;
this file, `CLAUDE.md`, `reviews/`, `diagrams/` and `scripts/` are excluded.

| File | Holds |
|---|---|
| `_config.yml` | The title, the design's `version` (shown in the header and on the PDF's cover), the repository the "Edit this page" links point at, and what is not published (`CLAUDE.md`, `diagrams/`, `scripts/`) |
| `_data/nav.yml` | The reading order of the pages in parts, and per page the PDF it is printed in (`pdf: design`, `summary` or `reference`; none = online only). The layout builds the sidebar (with the PDF tags and their legend), the part shown above each title and the previous / next links from it; the Contents of `README.md` repeat it with a one-line description per page and *(PDF)* on the design PDF's pages, and `scripts/check.sh` fails when the lists, the markers or the files in `docs/` disagree |
| `_layouts/default.html` | The page: header (with the version and the PDF link), sidebar, the "On this page" list built from the h2 / h3 headings at build time, the page, previous / next |
| `assets/css/site.css` | The styles, light and dark (the reader's choice is remembered; the system setting is the default), print |
| `assets/js/site.js` | Progressive enhancements only: the theme toggle, the dark rendering of each picture in dark mode, pictures as figures with their caption and a full-screen view on click |

To add a page: create the Markdown in `docs/`, add it to `_data/nav.yml` (with `pdf: design` if it belongs in the
design PDF) and to the Contents of `README.md` (with *(PDF)* in that case), and run `scripts/check.sh`. A page is numbered `<part>.<page>` in reading order (`2.3` is the third page of part 2, *Inside a
cluster*) and the pictures carry the number of the page that shows them, so a new page in the middle of a part
renumbers the pages after it - the files, the headings, the pictures and every "section N.M" in the text, here and in
the implementation repositories, which cite sections by number too.

## The PDF and the release notes

Every publish also builds **three PDFs**: the summary (`/onek8s-design-summary.pdf`, page 1.0 alone), the design
(`/onek8s-design.pdf`, sections 1.1 to 5.2, linked as *PDF* at the top of every page) and the reference
(`/onek8s-design-reference.pdf`, part 8). Which PDF a page is in is its `pdf:` key in `_data/nav.yml` - the sidebar
and the Contents of `README.md` mark the design PDF's pages; the intro and parts 6 and 7 have no key and stay online
only for now - and `scripts/pdf.py --only <name>` selects by it. `scripts/pdf.py` takes the built pages in the order of `_data/nav.yml`
(`--only` selects parts, part ranges or pages), puts a cover with the version and the commit and a contents list in
front, and prints them with headless Chrome, each page on a new sheet, with an outline from the headings. Links between
pages and to their headings stay links inside the PDF (each id is prefixed with its page, so the same heading on two
pages is two targets); links to pages outside a PDF's selection, and to files that are not pages, go to the site, or to
GitHub for what the site does not publish. The build fails when a link inside a PDF has no target. The `Check` workflow
builds the same PDFs on every pull request and attaches them to the run as `onek8s-design-pdf`.

The design is v2.0 since 2026-10-19 (the user's decision; v1.0 to v1.15 are in the `v1.15` tag). A pull request that
changes the design adds the next minor version (v2.1, v2.2, ...; a major version only when a human says so) to
[8.1 Release notes](docs/8.1-release-notes.md) - one short sentence per change with the link to the pull request - and sets
the same `version` in `_config.yml`; `scripts/check.sh` fails when the two disagree or an entry has no pull request
link. Every version is tagged `v<version>` in every repository at its default branch's head by aks-terraform's
`Design tags` workflow (`design-tags.yml`, hourly and by hand), so merge the code pull requests of a round before the
design's.

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
