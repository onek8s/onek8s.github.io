# Editing the pictures

Sources are Mermaid files in [`diagrams/`](../diagrams); rendered SVGs live in [`images/`](../images).
After editing a source, regenerate with:

```sh
scripts/render.sh
```

A pull request fails the `Check` workflow when a `.mmd` is newer in Git than its `.svg`, or a relative link in the
documents is broken; run `scripts/check.sh` locally to see the same result.

## Building the site locally

The site is plain [GitHub Pages with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll)
(`_config.yml`, `_layouts/default.html`). To preview it:

```sh
gem install bundler jekyll github-pages
jekyll serve   # http://127.0.0.1:4000/
```

---

[Back to contents](../README.md) · Previous: [Comparison with Wolkwacht](wolkwacht-comparison.md)
