#!/usr/bin/env python3
"""Build a PDF of the design, or of a selection of its pages, from the built site.

Takes the pages of the built Jekyll site (_site) in the reading order of _data/nav.yml, joins their content into one
HTML document - a cover with the version, a contents list, then every page on a new sheet - and prints it with
headless Chrome. With --only the PDF holds a selection: the name of a PDF as the pages' `pdf:` key in nav.yml gives it
(`design`, `summary`, `reference`), parts (`1-6`, `7`), pages (`1.0`) or `intro` (README.md), separated by commas;
links to pages outside the selection go to the published site. Links between pages and to their headings become links inside the PDF: every id is prefixed with its
page's key (s2-1--<id>, intro--<id> for README.md), so the same heading on two pages stays two targets. Links to files
that are not pages go to the published site, or to GitHub when the site does not publish them (diagrams/, scripts/).
The build fails when an internal link has no target.

Usage: scripts/pdf.py <site dir> <output .pdf> [--only <selection>] [--subtitle <text>]
(run from the repository root; needs python3 and Chrome / Chromium, found on PATH or given as CHROME=<path>)
"""
import datetime
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urljoin, urlsplit

SITE_URL = 'https://onek8s.github.io'


def config():
    text = open('_config.yml', encoding='utf-8').read()
    get = lambda key: (re.search(rf'^{key}:\s*"?([^"\n]*)"?\s*$', text, re.M) or [None, ''])[1].strip()
    return {key: get(key) for key in ('title', 'description', 'version', 'repository', 'branch')}


def nav():
    """_data/nav.yml as a list of parts with their pages (path, number, title, pdf)."""
    parts = []
    for line in open('_data/nav.yml', encoding='utf-8'):
        if m := re.match(r'- number: (\d+)', line):
            parts.append({'number': m[1], 'pages': []})
        elif m := re.match(r'\s+part: (.+)', line):
            parts[-1]['part'] = m[1].strip().strip('"')
        elif m := re.match(r'\s+- path: (\S+)', line):
            parts[-1]['pages'].append({'path': m[1]})
        elif m := re.match(r'\s+number: "([\d.]+)"', line):
            parts[-1]['pages'][-1]['number'] = m[1]
        elif m := re.match(r'\s+title: (.+)', line):
            parts[-1]['pages'][-1]['title'] = m[1].strip().strip('"')
        elif m := re.match(r'\s+pdf: (\w+)', line):
            parts[-1]['pages'][-1]['pdf'] = m[1]
    return parts


def url_of(path):
    """The published URL path of a source page: README.md is the index, x.md is x.html."""
    return '/' if path == 'README.md' else '/' + path[:-3] + '.html'


def key_of(page):
    return 's' + page['number'].replace('.', '-') if 'number' in page else 'intro'


def selected(parts, only):
    """The parts and pages --only names: a PDF name (the pages' `pdf:` key), `intro`, a part number, a range of parts
    `a-b`, or a page number."""
    if not only:
        return parts
    wanted = set()
    for item in only.split(','):
        item = item.strip()
        if m := re.fullmatch(r'(\d+)-(\d+)', item):
            wanted |= {str(n) for n in range(int(m[1]), int(m[2]) + 1)}
        else:
            wanted.add(item)
    result = []
    for part in parts:
        pages = [p for p in part['pages'] if part['number'] in wanted or p.get('number') in wanted
                 or p.get('pdf') in wanted or (p['path'] == 'README.md' and 'intro' in wanted)]
        if pages:
            result.append(dict(part, pages=pages))
    return result


def main(site, out, only=None, subtitle=None):
    cfg = config()
    repo = f"https://github.com/{cfg['repository']}"
    all_parts = nav()
    parts = selected(all_parts, only)
    if not parts:
        print(f'--only {only} selects no page', file=sys.stderr)
        return 1
    all_pages = [dict(p, part=part) for part in all_parts for p in part['pages']]
    pages = [dict(p, part=part) for part in parts for p in part['pages']]
    site_pages = {url_of(p['path']): p for p in all_pages}
    by_url = {url_of(p['path']): p for p in pages}

    def rewrite_href(href, page):
        if href.startswith(('mailto:', 'http://', 'https://')) and not href.startswith(SITE_URL + '/'):  # elsewhere
            return href
        if href.startswith(SITE_URL + '/') and urlsplit(href).path not in by_url:
            return href
        if href.startswith('#'):
            return f'#{key_of(page)}--{href[1:]}' if href[1:] else f'#{key_of(page)}'
        target = urlsplit(urljoin(SITE_URL + url_of(page['path']), html.unescape(href)))
        if target.path in by_url:
            key = key_of(by_url[target.path])
            return f'#{key}--{target.fragment}' if target.fragment else f'#{key}'
        if target.path in site_pages:  # a page of the design outside this PDF's selection
            return SITE_URL + target.path + (f'#{target.fragment}' if target.fragment else '')
        local = target.path.lstrip('/')
        if local and os.path.isfile(os.path.join(site, local)):
            return SITE_URL + target.path
        return f"{repo}/tree/{cfg['branch']}/{local}"

    def rewrite_src(src, page):
        target = urlsplit(urljoin(SITE_URL + url_of(page['path']), html.unescape(src)))
        if target.netloc != urlsplit(SITE_URL).netloc:
            return src
        return 'file://' + os.path.abspath(os.path.join(site, target.path.lstrip('/')))

    body = []
    for page in pages:
        built = 'index.html' if page['path'] == 'README.md' else url_of(page['path']).lstrip('/')
        source = open(os.path.join(site, built), encoding='utf-8').read()
        main_html = re.search(r'<main>(.*?)</main>', source, re.S)[1]
        # The site's "On this page" box: the PDF has its own outline.
        main_html = re.sub(r'<nav class="toc-inline".*?</nav>', '', main_html, flags=re.S)
        key = key_of(page)
        main_html = re.sub(r'\bid="([^"]*)"', lambda m: f'id="{key}--{m[1]}"', main_html)
        main_html = re.sub(r'\bhref="([^"]*)"', lambda m: f'href="{html.escape(rewrite_href(m[1], page))}"', main_html)
        main_html = re.sub(r'\bsrc="([^"]*)"', lambda m: f'src="{html.escape(rewrite_src(m[1], page))}"', main_html)
        if page['path'] == 'README.md':
            main_html = f'<p class="eyebrow">{html.escape(page["part"]["number"])}. {html.escape(page["part"]["part"])}</p>' + main_html
        body.append(f'<section class="page" id="{key}">{main_html}</section>')

    # The links must all land: every href="#x" needs an id="x".
    joined = '\n'.join(body)
    ids = set(re.findall(r'\bid="([^"]*)"', joined)) | {key_of(p) for p in pages}
    missing = sorted({h for h in re.findall(r'\bhref="#([^"]*)"', joined) if h not in ids})
    for h in missing:
        print(f'  BROKEN   #{h} has no target in the PDF', file=sys.stderr)
    if missing:
        return 1

    sha = os.environ.get('GITHUB_SHA') or subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                                                         text=True).stdout.strip()
    today = datetime.date.today().isoformat()
    notes = next(p for p in all_pages if p['path'].endswith('-release-notes.md'))
    notes_href = f'#{key_of(notes)}' if notes in pages else SITE_URL + url_of(notes['path'])
    contents = ''.join(
        f'<li><span class="part-title">{part["number"]}. {html.escape(part["part"])}</span><ul>'
        + ''.join(f'<li><a href="#{key_of(p)}">{html.escape(p.get("number", ""))} {html.escape(p["title"])}</a></li>'
                  for p in part['pages'])
        + '</ul></li>' for part in parts)
    cover = f'''<section class="cover">
<p class="cover-title">{html.escape(cfg["title"])}</p>
<p class="cover-sub">{html.escape(cfg["description"])}</p>
<p class="cover-meta">{html.escape(subtitle or "Platform design")}, version {html.escape(cfg["version"])}, built {today} from commit
<a href="{repo}/commit/{sha}">{sha[:7]}</a>.<br>The current version is published at <a href="{SITE_URL}/">{SITE_URL}</a>;
the changes between versions are in <a href="{notes_href}">{notes["number"]} {html.escape(notes["title"])}</a>.</p>
</section>'''
    if len(pages) > 1:
        cover += f'<section class="contents"><h1 id="contents">Contents</h1><ul>{contents}</ul></section>'

    css = 'file://' + os.path.abspath(os.path.join(site, 'assets/css/site.css'))
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(cfg["title"])} v{html.escape(cfg["version"])}</title>
<link rel="stylesheet" href="{css}">
<style>
@page {{ size: A4; margin: 16mm 15mm 18mm;
  @bottom-left {{ content: "{cfg["title"]} v{cfg["version"]}"; font: 8pt sans-serif; color: #59636e; }}
  @bottom-right {{ content: counter(page) " / " counter(pages); font: 8pt sans-serif; color: #59636e; }} }}
@page :first {{ @bottom-left {{ content: none; }} @bottom-right {{ content: none; }} }}
body {{ font-size: 10pt; background: #fff; }}
main {{ max-width: none; }}
main a {{ color: var(--link); }}
.page, .contents {{ break-before: page; }}
.cover {{ padding-top: 35vh; }}
.cover-title {{ font-size: 36pt; font-weight: 700; margin: 0; color: var(--accent); }}
.cover-sub {{ font-size: 15pt; margin: .5em 0 2em; }}
.cover-meta {{ color: var(--muted); }}
.contents ul {{ list-style: none; padding-left: 0; margin: 0; }}
.contents li {{ margin: 0; line-height: 1.45; }}
.contents ul ul {{ padding-left: 1.5em; margin-bottom: .6em; }}
.contents .part-title {{ font-weight: 700; }}
/* A picture fits one page: tall ones (3.1, 3.2, 3.5) scale down to the page's height instead of being split,
   and a heading never ends a page without the text or picture that follows it. */
img {{ max-width: 100%; max-height: 225mm; width: auto; height: auto; display: block; margin: 0.8em auto;
  break-inside: avoid; }}
h1, h2, h3, h4 {{ break-after: avoid; break-inside: avoid; }}
figure, pre {{ break-inside: avoid; }}
table {{ font-size: 8.5pt; }}
</style></head>
<body><main>
{cover}
{joined}
</main></body></html>'''

    chrome = os.environ.get('CHROME') or next(
        (shutil.which(c) for c in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome')
         if shutil.which(c)), None)
    if not chrome:
        print('No Chrome or Chromium found; set CHROME=<path>', file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'design.html')
        open(src, 'w', encoding='utf-8').write(document)
        subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                        '--generate-pdf-document-outline', '--run-all-compositor-stages-before-draw',
                        '--virtual-time-budget=30000', f'--user-data-dir={tmp}/profile',
                        f'--print-to-pdf={os.path.abspath(out)}', 'file://' + src],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        print(f'Chrome wrote no {out}', file=sys.stderr)
        return 1
    print(f'{out}: {len(pages)} pages of the design, {os.path.getsize(out) // 1024} KiB')
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('site')
    parser.add_argument('out')
    parser.add_argument('--only', help='a PDF name (design, summary, reference), parts, part ranges, page numbers or '
                        'intro, separated by commas')
    parser.add_argument('--subtitle', help='what the cover calls this PDF (default: Platform design)')
    args = parser.parse_args()
    sys.exit(main(args.site, args.out, args.only, args.subtitle))
