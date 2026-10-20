#!/usr/bin/env python3
"""Check that every code owner of a pull request's changed files has approved it (the `Approvals` status check).

The repository's owners are in .github/CODEOWNERS: the requirements and the governance files are the human's, the
rest is the AI's. Branch protection's code owner review cannot enforce that, since the AI account writes most pull
requests and an author cannot approve their own, so this check does it instead and branch protection requires it.

The rules are read from the pull request's BASE commit, so a pull request cannot loosen its own rules; only when the
base has no CODEOWNERS yet (the pull request that adds it) is the working tree's file used. A changed file needs the
owners of its last matching line; a renamed file also those of its old name, so moving a file out of a protected folder
needs that folder's owner. An owner is satisfied when they are the pull request's author, or when their latest review
(APPROVED, CHANGES_REQUESTED or DISMISSED - comments change nothing) approves either the head commit or a commit after
which none of their files changed (compare API; a failed compare, e.g. after a force-push, counts as stale). A line
with several owners is satisfied by any one of them.

Usage: python3 -I scripts/approvals.py              (in CI: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER)
       python3 -I scripts/approvals.py --self-test  (the CODEOWNERS matching, offline)
GITHUB_API_URL defaults to https://api.github.com; without GITHUB_TOKEN it reads public repositories unauthenticated.
The result is printed as a table and, when GITHUB_STEP_SUMMARY is set, written there as Markdown. Exit 1 when an owner
is not satisfied.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

CODEOWNERS = '.github/CODEOWNERS'
API = os.environ.get('GITHUB_API_URL', 'https://api.github.com').rstrip('/')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
DECISIVE = ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED')  # COMMENTED reviews leave the state as it was


# --- CODEOWNERS --------------------------------------------------------------------------------------------------

def pattern_regex(pattern):
    """A CODEOWNERS pattern as a regex on a path relative to the root (the subset this repository uses).

    A leading / anchors to the root, a trailing / matches a directory and everything under it, * and ? stay within one
    path segment (** crosses them), and a pattern without any other / matches at any depth. A pattern without a
    trailing / also matches a directory of that name and everything under it, as in .gitignore."""
    directory = pattern.endswith('/')
    body = pattern.strip('/')
    anchored = pattern.startswith('/') or '/' in body
    out = ''
    i = 0
    while i < len(body):
        if body.startswith('**', i):
            out += '.*'
            i += 2
        elif body[i] == '*':
            out += '[^/]*'
            i += 1
        elif body[i] == '?':
            out += '[^/]'
            i += 1
        else:
            out += re.escape(body[i])
            i += 1
    if body == '':  # '*' alone was handled above; a bare '/' matches everything
        out = '.*'
    prefix = '^' if anchored else '^(?:.*/)?'
    suffix = '/.*$' if directory else '(?:/.*)?$'
    return re.compile(prefix + out + suffix)


def parse_codeowners(text):
    """[(pattern, regex, owners)] in file order; owners are logins without @ (lower case), teams kept as org/team."""
    rules = []
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        pattern, *owners = line.split()
        owners = tuple(o[1:].lower() for o in owners if o.startswith('@'))
        rules.append((pattern, pattern_regex(pattern), owners))
    return rules


def owners_of(rules, path):
    """The owners of the last matching line (an empty tuple: no line matches, or the line names no owner)."""
    found = ()
    for _, regex, owners in rules:
        if regex.match(path):
            found = owners
    return found


def self_test():
    rules = parse_codeowners(
        '# comment\n'
        '*               @olljanat-ai\n'
        '/requirements/  @olljanat\n'
        '/diagrams/0.*   @olljanat\n'
        '/images/0.*     @olljanat\n'
        '/.github/       @olljanat\n'
        '/CLAUDE.md      @olljanat\n'
        'notes.txt       @someone   # any depth\n'
        '/docs/?.md      @single\n')
    cases = {
        'README.md': ('olljanat-ai',),
        'design/2.3-node-pools.md': ('olljanat-ai',),
        'requirements/0.1-goals.md': ('olljanat',),
        'requirements/sub/deep.md': ('olljanat',),
        'requirements': ('olljanat-ai',),  # a file named like the directory is not under it
        'x/requirements/a.md': ('olljanat-ai',),  # anchored to the root
        'diagrams/0.1-overview.mmd': ('olljanat',),
        'diagrams/1.1-overview.mmd': ('olljanat-ai',),
        'images/0.1-overview.dark.svg': ('olljanat',),
        'images/10.1-x.svg': ('olljanat-ai',),
        '.github/CODEOWNERS': ('olljanat',),
        '.github/workflows/approvals.yml': ('olljanat',),
        'CLAUDE.md': ('olljanat',),
        'design/CLAUDE.md': ('olljanat-ai',),
        'notes.txt': ('someone',),
        'a/b/notes.txt': ('someone',),
        'docs/a.md': ('single',),
        'docs/ab.md': ('olljanat-ai',),
        'docs/x/a.md': ('olljanat-ai',),
    }
    failed = 0
    for path, want in cases.items():
        got = owners_of(rules, path)
        if got != want:
            print(f'FAIL {path}: {got} != {want}')
            failed += 1
    assert pattern_regex('*').match('a/b/c')
    assert pattern_regex('/a/**/b').match('a/x/y/b')
    print(f'self-test: {len(cases) - failed}/{len(cases)} paths owned as expected')
    return 1 if failed else 0


# --- GitHub API --------------------------------------------------------------------------------------------------

def request(path, accept='application/vnd.github+json'):
    """GET API + path; returns (status, body bytes). HTTP errors are returned, not raised."""
    req = urllib.request.Request(API + path, headers={
        'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'onek8s-approvals'})
    if TOKEN:
        req.add_header('Authorization', 'Bearer ' + TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def get_json(path):
    status, body = request(path)
    if status != 200:
        sys.exit(f'GET {path}: HTTP {status}: {body[:300].decode(errors="replace")}')
    return json.loads(body)


def get_all(path):
    """Every item of a paginated list (100 per page)."""
    items, page = [], 1
    sep = '&' if '?' in path else '?'
    while True:
        batch = get_json(f'{path}{sep}per_page=100&page={page}')
        items += batch
        if len(batch) < 100:
            return items
        page += 1


def codeowners_text(repo, base_sha):
    """CODEOWNERS as the base commit has it; the working tree's when the base has none (the bootstrap pull request)."""
    ref = urllib.parse.quote(base_sha)
    status, body = request(f'/repos/{repo}/contents/{CODEOWNERS}?ref={ref}', 'application/vnd.github.raw')
    if status == 200:
        return body.decode('utf-8'), f'base {base_sha[:7]}'
    if status != 404:
        sys.exit(f'Reading {CODEOWNERS} at the base: HTTP {status}: {body[:300].decode(errors="replace")}')
    try:
        return open(CODEOWNERS, encoding='utf-8').read(), 'working tree (the base has none)'
    except FileNotFoundError:
        sys.exit(f'No {CODEOWNERS} at the base {base_sha[:7]} nor in the working tree')


def changed_since(repo, commit, head):
    """Files changed from commit to head (old and new names), or None when the compare fails or may be truncated."""
    status, body = request(f'/repos/{repo}/compare/{commit}...{head}')
    if status != 200:
        return None
    files = json.loads(body).get('files') or []
    if len(files) >= 300:  # the compare API lists at most 300 files: assume one of the owner's is among the rest
        return None
    paths = set()
    for f in files:
        paths.add(f['filename'])
        if f.get('previous_filename'):
            paths.add(f['previous_filename'])
    return paths


# --- The check ---------------------------------------------------------------------------------------------------

def main():
    repo = os.environ.get('GITHUB_REPOSITORY')
    number = os.environ.get('PR_NUMBER')
    if not repo or not number:
        sys.exit('Set GITHUB_REPOSITORY and PR_NUMBER (and GITHUB_TOKEN in CI)')
    pr = get_json(f'/repos/{repo}/pulls/{number}')
    author = pr['user']['login'].lower()
    head, base = pr['head']['sha'], pr['base']['sha']
    text, source = codeowners_text(repo, base)
    rules = parse_codeowners(text)

    # Required owner groups -> the changed paths they own (a renamed file counts under its old name too).
    required = {}
    for f in get_all(f'/repos/{repo}/pulls/{number}/files'):
        for path in {f['filename'], f.get('previous_filename') or f['filename']}:
            owners = owners_of(rules, path)
            if owners:
                required.setdefault(owners, set()).add(path)

    # Each reviewer's latest decisive review, in the order GitHub lists them (chronological).
    latest = {}
    for review in get_all(f'/repos/{repo}/pulls/{number}/reviews'):
        if review.get('user') and review['state'] in DECISIVE:
            latest[review['user']['login'].lower()] = review

    rows, ok = [], True
    for owners, paths in sorted(required.items()):
        statuses = []
        for owner in owners:
            review = latest.get(owner)
            if owner == author:
                statuses.append((True, 'author'))
            elif review is None or review['state'] == 'DISMISSED':
                statuses.append((False, 'missing'))
            elif review['state'] == 'CHANGES_REQUESTED':
                statuses.append((False, 'changes requested'))
            elif review['commit_id'] == head:
                statuses.append((True, f'approved at {head[:7]}'))
            else:
                since = changed_since(repo, review['commit_id'], head)
                if since is not None and not (since & paths):
                    statuses.append((True, f'approved at {review["commit_id"][:7]}'))
                else:
                    statuses.append((False, 'approval stale'))
        passed = any(s for s, _ in statuses)
        ok &= passed
        names = sorted(paths)
        files = f'{len(names)}: ' + ', '.join(names[:5]) + (', ...' if len(names) > 5 else '')
        status = '; '.join(f'{o}: {s}' if len(owners) > 1 else s for o, (_, s) in zip(owners, statuses))
        rows.append((' / '.join('@' + o for o in owners), files, status, passed))

    # Report: a plain table on stdout, Markdown in the step summary.
    print(f'Pull request #{number} by @{author}, head {head[:7]}; CODEOWNERS from the {source}')
    if not rows:
        print('No changed file has an owner.')
    widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(('Owner', 'Files'))]
    print(f'{"Owner":<{widths[0]}}  {"Files":<{widths[1]}}  Status')
    for owner, files, status, passed in rows:
        print(f'{owner:<{widths[0]}}  {files:<{widths[1]}}  {"OK  " if passed else "FAIL"} {status}')
    print('All owners satisfied.' if ok else 'Waiting for the owners marked FAIL.')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as out:
            out.write(f'### Approvals\n\nPull request #{number} by @{author}, head `{head[:7]}`; '
                      f'CODEOWNERS from the {source}.\n\n| Owner | Files | Status |\n|---|---|---|\n')
            for owner, files, status, passed in rows:
                cell = files.replace('|', '\\|')
                out.write(f'| {owner} | {cell} | {"OK" if passed else "**FAIL**"} {status} |\n')
            out.write('\n' + ('All owners satisfied.' if ok else 'Waiting for the owners marked FAIL.') + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(self_test() if sys.argv[1:] == ['--self-test'] else main())
