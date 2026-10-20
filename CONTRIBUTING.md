# Editing the pictures and the site

How this repository is edited and built. The requirements and acceptance criteria are in `requirements/` (part 0),
the design in `design/` (parts 1 to 8); both are published at [onek8s.github.io](https://onek8s.github.io/).

## Who approves what

Humans own `requirements/` and AI owns `design/` ([0.1 How we work](requirements/0.1-how-we-work.md)):

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
write the colours for a white background as before - one source serves both. The light rendering uses the spacing of
`scripts/mermaid.json`; keep a picture at most about 1 200 px wide (and 1 500 px tall), because the PDF scales it to
the page and the 16 px labels turn unreadable beyond that - stack subgraphs (`a ~~~ b`), keep edge labels to a few
words and prefer `flowchart TB` with two or three columns to a wide `LR` row.

A pull request fails the `Check` workflow when a `.mmd` is newer in Git than either `.svg`, when a relative link in
the documents is broken, or when the navigation and the files in `requirements/` and `design/` disagree (below); run `scripts/check.sh`
locally to see the same result.

## The site

The site is plain [GitHub Pages with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll):
the Markdown in `requirements/`, `design/` and `README.md` is published as is, without front matter, and one layout wraps every page;
this file, `CLAUDE.md`, `reviews/`, `diagrams/` and `scripts/` are excluded.

| File | Holds |
|---|---|
| `_config.yml` | The title, the design's `version` (shown in the header and on the PDF's cover), the repository the "Edit this page" links point at, and what is not published (`CLAUDE.md`, `diagrams/`, `scripts/`) |
| `_data/nav.yml` | The reading order of the pages in parts, and per page the PDF it is printed in (`pdf: requirements`, `design`, `summary` or `reference`; none = online only). The layout builds the sidebar (with the PDF tags and their legend), the part shown above each title and the previous / next links from it; the Contents of `README.md` repeat it with a one-line description per page and *(PDF)* on the design PDF's pages and *(requirements PDF)* on the requirements PDF's, and `scripts/check.sh` fails when the lists, the markers or the files in `requirements/` and `design/` disagree, or when a page in `requirements/` is not `pdf: requirements` (or one outside it is) |
| `_layouts/default.html` | The page: header (with the version and the PDF link), sidebar, the "On this page" list built from the h2 / h3 headings at build time, the page, previous / next |
| `assets/css/site.css` | The styles, light and dark (the reader's choice is remembered; the system setting is the default), print |
| `assets/js/site.js` | Progressive enhancements only: the theme toggle, the dark rendering of each picture in dark mode, pictures as figures with their caption and a full-screen view on click |

To add a page: create the Markdown in `design/` (or, for a requirement page, in `requirements/`, part 0), add it to
`_data/nav.yml` (with `pdf: design` if it belongs in the design PDF, `pdf: requirements` for every page in
`requirements/`) and to the Contents of `README.md` (with *(PDF)* or *(requirements PDF)* in those cases), and run `scripts/check.sh`. A page is numbered `<part>.<page>` in reading order (`2.3` is the third page of part 2, *Inside a
cluster*) and the pictures carry the number of the page that shows them, so a new page in the middle of a part
renumbers the pages after it - the files, the headings, the pictures and every "section N.M" in the text, here and in
the implementation repositories, which cite sections by number too.

## The PDF and the release notes

Every publish also builds **four PDFs**: the requirements (`/onek8s-requirements.pdf`, part 0), the summary
(`/onek8s-design-summary.pdf`, page 1.0 alone), the design (`/onek8s-design.pdf`, sections 1.1 to 5.2, linked as
*PDF* at the top of every page) and the reference (`/onek8s-design-reference.pdf`, part 8). Which PDF a page is in is
its `pdf:` key in `_data/nav.yml` - the sidebar tags the design PDF's pages *PDF* and the other PDFs' *own PDF*, the
Contents of `README.md` mark them *(PDF)* and *(requirements PDF)*; the intro and parts 6 and 7 have no key and stay
online only for now - and `scripts/pdf.py --only <name>` selects by it. `scripts/pdf.py` takes the built pages in the order of `_data/nav.yml`
(`--only` selects parts, part ranges or pages), puts a cover with the version and the commit and a contents list in
front, and prints them with headless Chrome, each page on a new sheet, with an outline from the headings. Links between
pages and to their headings stay links inside the PDF (each id is prefixed with its page, so the same heading on two
pages is two targets); links to pages outside a PDF's selection, and to files that are not pages, go to the site, or to
GitHub for what the site does not publish. The build fails when a link inside a PDF has no target. The `Check` workflow
builds the same PDFs on every pull request and attaches them to the run as `onek8s-design-pdf`; the requirements PDF
is `--only requirements --subtitle Requirements`.

The design is v2.0 since 2026-10-19 (the user's decision; v1.0 to v1.15 are in the `v1.15` tag). A pull request that
changes the design adds the next minor version (v2.1, v2.2, ...; a major version only when a human says so) to
[8.1 Release notes](design/8.1-release-notes.md) - one short sentence per change with the link to the pull request - and sets
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
