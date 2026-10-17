# Editing the pictures and the site

## The pictures

Sources are Mermaid files in [`diagrams/`](../diagrams); rendered SVGs live in [`images/`](../images).
After editing a source, regenerate with:

```sh
scripts/render.sh
```

A pull request fails the `Check` workflow when a `.mmd` is newer in Git than its `.svg`, when a relative link in
the documents is broken, or when the navigation and the files in `docs/` disagree (below); run `scripts/check.sh`
locally to see the same result.

## The site

The site is plain [GitHub Pages with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll):
the Markdown in `docs/` and `README.md` is published as is, without front matter, and one layout wraps every page.

| File | Holds |
|---|---|
| `_config.yml` | The title, the repository the "Edit this page" links point at, and what is not published (`CLAUDE.md`, `diagrams/`, `scripts/`) |
| `_data/nav.yml` | The reading order of the pages in parts. The layout builds the sidebar, the part shown above each title and the previous / next links from it; the Contents of `README.md` repeat it with a one-line description per page, and `scripts/check.sh` fails when the two lists or the files in `docs/` disagree |
| `_layouts/default.html` | The page: header, sidebar, the "On this page" list built from the h2 / h3 headings at build time, the page, previous / next |
| `assets/css/site.css` | The styles, light and dark (the reader's choice is remembered; the system setting is the default), print |
| `assets/js/site.js` | Progressive enhancements only: the theme toggle, pictures as figures with their caption and a full-screen view on click |

To add a page: create the Markdown in `docs/`, add it to `_data/nav.yml` and to the Contents of `README.md`, and run
`scripts/check.sh`. The section numbers are stable identifiers (the decision log and the implementation repositories
cite "section 14"), so a new section takes the next free number and the navigation places it by topic.

## Building the site locally

```sh
printf 'source "https://rubygems.org"\ngem "github-pages", group: :jekyll_plugins\n' > Gemfile
bundle install
bundle exec jekyll serve   # http://127.0.0.1:4000/
```

The `github-pages` gem pins the same Jekyll and plugins GitHub Pages builds with (the Markdown without front
matter, `README.md` as the index, relative links rewritten to the published pages). `Gemfile` and `Gemfile.lock`
are not committed.
