# OneK8s design - notes for Claude sessions

The shared working notes for all OneK8s repos (what is deployed, how to operate it, gotchas) are in
`onek8s/aks-terraform/CLAUDE.md`. Read that first.

## This repository

The requirements and the design, published with GitHub Pages, in two folders with two owners (since v3.9, page
`requirements/0.1-how-we-work.md`):

- `requirements/0.<page>-*.md`, part 0 Requirements - **owned by humans**: 0.1 How we work, 0.2 Requirements (R1 to
  R26 with the acceptance criteria that prove each), 0.3 Acceptance criteria (the acceptance tests in dev, formerly in
  7.1). AI may propose a change; every change needs a human's approval (`olljanat`). Never change a requirement or a
  criterion to fit the design: propose it in its own pull request for a human.
- `design/<part>.<page>-*.md`, parts 1 to 8 (1 Start here, 2 Inside a cluster, 3 The fleet, 4 Encryption, 5 Egress
  control, 6 Operations, 8 Appendix; part 7 has no page since the decision log left) - **owned by AI**, like the
  infrastructure as code in the implementation repositories; a human's change gets the AI's review (`olljanat-ai`) against the requirements and
  acceptance criteria. `1.2-how-the-design-meets-the-requirements.md` maps each requirement to the design (and holds
  the vocabulary). The design states what is chosen: it keeps no decision log, capability or verification matrix,
  human sign-offs or open questions.
- `archive/` (since v4.0, the user) - what no requirement names, kept as Markdown outside the site and the PDFs: the
  whole pages 7.1 (implementation project), 7.2 (the old decision log: D-numbers, capability matrix V, sign-offs H),
  7.3 (open questions Q), 7.4 (outlook, options kept open, watch list) and 7.5 (other clouds, exit;
  its data services moved to 1.3), and `<page>-<slug>-sections.md` with the sections moved out of a page (GPUs of 2.3,
  the D/V/H/Q rows no requirement names, ...). Numbering gaps stay (no renumbering). No published page links into it.

**The design holds only what serves a requirement** (the user, v4.0): every design page names the requirements of 0.2
it serves on the line under its first heading (`**Requirements:** [R5](../requirements/0.2-requirements.md#r5), ...`; every link to a requirement names its row;
8.1 says `none`). Content no requirement names goes to `archive/`, not `design/`; propose the requirement to a human
instead.

`.github/CODEOWNERS` and the required `Approvals` check (`scripts/approvals.py`) enforce who approves what: it lists
the approval each changed path needs, the author counts as their own side's approval, and an approval is kept across
later pushes that do not touch that owner's files. Old `docs/` URLs, and those of the pages v4.0 archived,
are redirected by `404.html`.

Diagrams are `diagrams/*.mmd`, rendered to `images/<name>.svg` and `<name>.dark.svg` by `scripts/render.sh` (`CONTRIBUTING.md`). The reading order is `_data/nav.yml` (the sidebar; the
front page has no Contents) - a new page goes into it, with `pdf: design` for every page in `design/` and `pdf:
requirements` for every page in `requirements/` and no other (`check.sh` checks the folder, and that file name, first
heading and nav share the page number). The header has two buttons, Requirements PDF and Design PDF; the sidebar
separates part 0 (owned by humans) from parts 1 to 8 (owned by AI). `scripts/check.sh` runs in CI (diagram freshness, links and anchors, navigation, release notes, each design
page's requirements line, no link into `archive/`).

- **Decisions are no longer logged** (the user, v4.0): the design states what is chosen, with a short reason only
  where it explains how a requirement is met. A changed choice changes the page that states it. The old decision
  log (`archive/7.2-decisions.md`, with `archive/7.2-decisions-sections.md`), its D/V/H numbers and the open
  questions (`archive/7.3-open-questions.md`) are kept in `archive/` for history only; no published page cites a
  D, V, H or Q number. The implementation repositories and older commits still cite D-numbers: they resolve there.
- **The environments are built from the design** (the user's rule), never the other way round: the pages describe
  the design, not the state of a lab or of the code. No "built today" against "target", no repository, file,
  workflow or variable names of the implementation, no lab cluster names or addresses (example names only, as
  `aks-prd-int-stateless-az1`); what the implementation still lacks is tracked with the implementation, not here.
  A finding in an environment that changes the design is a design pull request first. The landing zone is out of
  scope: refer to Microsoft's documentation instead of explaining it here.
- **Versions** (the user): the design is **v4.0 since 2026-10-20**. Every pull request that changes the design adds
  the next minor version (v4.1, v4.2, ...; a major version only when a human says so) at the top of
  `design/8.1-release-notes.md` - `## v4.N - <date>`, one short sentence per change ending in the pull request link
  (`[#NN](https://github.com/onek8s/onek8s.github.io/pull/NN)`) - and sets the same `version:` in `_config.yml`;
  create the pull request first if its number is not known yet. `check.sh` fails when the two disagree or an entry
  has no pull request link. Every version is tagged `v<version>` in every repository by aks-terraform's `Design tags`
  workflow (`design-tags.yml`, hourly and by hand): merge a round's code pull requests before the design's.
- **Two PDFs** (since v4.0): the requirements (`/onek8s-requirements.pdf`, part 0, `--only requirements --subtitle
  Requirements`) and the design (`/onek8s-design.pdf`, `--only design`: every page of `design/`, the summary 1.0
  first, the release notes last; the former 100-page cap is gone). Membership is the `pdf:` key of each page in
  `_data/nav.yml` (`requirements`, `design`), which `scripts/pdf.py --only <name>` selects, built from `_site` in nav
  order with headless Chrome (Pages workflow; `Check` attaches them as `onek8s-design-pdf`). The build fails on a link
  without a target, so keep links relative (`x.md#heading`) and fix every link to a renamed heading. Pictures in a PDF
  must stay readable at page width: at most about 1 200 px wide (`CONTRIBUTING.md`).
- **History**: v1 - the options v2.0 removed, the two-cell lab and the section renumberings of 2026-10-17 that older
  commits and issues cite - is in the `v1.15` tag; v2.0 still carried the lab's state and the implementation's names,
  removed in v2.1; v2.2 removed ACNS and its page 5.1 (5.2 and 5.3 became 5.1 and 5.2), kept in the `v2.1` tag;
  v3.0 cut the design PDF under 100 pages: other clouds and exit on 7.5 (outside the PDF), the company firewall's
  delegation options in 7.1, Kubernetes and AKS mechanics replaced by links to the documentation; v3.9 split the
  repository into `requirements/` (humans) and `design/` (AI, formerly `docs/`), with 1.2's requirement texts in 0.2
  and 7.1's acceptance tests in 0.3 (anchors such as `#cis-benchmark` now point into 0.3); v4.0 moved what no
  requirement names to `archive/`, the decision log (7.2) and open questions (7.3) with it, and dropped the summary
  and reference PDFs - the `v3.8` tag holds the design before
  v4.0, with the release notes of v2.0 to v3.8 (8.1 lists only v4).

## The design in v4.0

(The D-numbers below are those of the archived decision log, `archive/7.2-decisions.md`; the design itself cites none.)
One cell network: Azure CNI Pod Subnet with dynamic IP allocation and Cilium (D74) - nodes and internal load
balancers in `/24` slots of `address_space` (slot 0 the system pool, a slot per zone index), pods in
`pod_address_space`, a `/16` of 100.64.0.0/10 with a `/20` per slot. The hub Firewall (one per exposure, D53) sees the
pods' own addresses and decides egress per application rule file in every cell; ACNS (FQDN filtering, Hubble, eBPF
host routing) is not used (D61, D80). Zone-to-zone traffic goes through the hub Firewall (D73). Zone
nodes are classic node pools with the cluster autoscaler - `<zone>`, `<zone>spot`, `<zone>arm`, `<zone>armspot`, from
zero, the priority expander putting spot first; node auto provisioning only
when it supports the pod subnet. No AKS Automatic (D79). Private API servers over Private Link (D58;
VNet integration is refused on encrypted networks), no public endpoints (D60), KMS data encryption (D22), Traefik with HTTP/2 and TLS 1.3
only at the edge and h2c upstream (D69-D71), Flux's webhook only in a cell with a public entry point (D78),
Git refs with one branch per cell (D77); no Microsoft Defender - the company's third-party security tool (D81); in the build tenant every
Azure Policy assignment denies once it reports no non-compliant resource (D82); purge protection by policy in prd only (D83). The stateful cluster and backup (6.3) are built with the first
approved stateful exception. GPUs (D42), other clouds and exit (7.5), the outlook (7.4) and the implementation
project's plan (7.1: build tenant, phases, the firewall VM of D57) are in `archive/`, outside the design.
