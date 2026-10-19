# OneK8s design - notes for Claude sessions

The shared working notes for all OneK8s repos (what is deployed, how to operate it, gotchas) are in
`onek8s/aks-terraform/CLAUDE.md`. Read that first.

## This repository

The design, published with GitHub Pages: `docs/<part>.<page>-*.md` (1 Start here, 2 Inside a cluster, 3 The fleet,
4 Encryption, 5 Egress control, 6 Operations, 7 Delivery and decisions, 8 Appendix). `7.2-decisions.md` is the decision
log, capability matrix and human sign-offs; `7.3-open-questions.md` holds only the questions a person still has to
weigh (the sign-offs live in 7.2 alone). Diagrams are `diagrams/*.mmd`, rendered to `images/<name>.svg` and
`<name>.dark.svg` by `scripts/render.sh` (`CONTRIBUTING.md`). The reading order is `_data/nav.yml`, repeated with a
description per page in `README.md`'s Contents - a new page goes into both. `scripts/check.sh` runs in CI (diagram
freshness, links and anchors, navigation, release notes).

- **Decisions**: a decision goes into `7.2-decisions.md` with its options and justification. D-numbers are never
  renumbered or reused (D75 is retired, D59 and D76 are merged into D61 and D74).
- **The environments are built from the design** (the user's rule), never the other way round: the pages describe
  the design, not the state of a lab or of the code. No "built today" against "target", no repository, file,
  workflow or variable names of the implementation, no lab cluster names or addresses (example names only, as
  `aks-prd-int-stateless-az1`); what the implementation still lacks is tracked with the implementation, not here.
  A finding in an environment that changes the design is a design pull request first. The landing zone is out of
  scope: refer to Microsoft's documentation instead of explaining it here.
- **Versions** (the user): the design is **v3.0 since 2026-10-19**. Every pull request that changes the design adds
  the next minor version (v2.1, v2.2, ...; a major version only when a human says so) at the top of
  `docs/8.1-release-notes.md` - `## v2.N - <date>`, one short sentence per change ending in the pull request link
  (`[#NN](https://github.com/onek8s/onek8s.github.io/pull/NN)`) - and sets the same `version:` in `_config.yml`;
  create the pull request first if its number is not known yet. `check.sh` fails when the two disagree or an entry
  has no pull request link. Every version is tagged `v<version>` in every repository by aks-terraform's `Design tags`
  workflow (`design-tags.yml`, hourly and by hand): merge a round's code pull requests before the design's.
- **Three PDFs**: the summary (`/onek8s-design-summary.pdf`, page `1.0-summary.md` alone - every line links a
  section, it adds nothing of its own), the design (`/onek8s-design.pdf`, sections 1.1 to 5.2, under 100 pages) and the reference
  (`/onek8s-design-reference.pdf`, part 8; the intro, the summary, parts 6 and 7 and page 7.5 are left out of the
  design PDF until the user asks for their review - the `--only` ranges in `check.yml` and `pages.yml`), built by `scripts/pdf.py --only` from `_site` in nav order with
  headless Chrome (Pages workflow; `Check` attaches them as `onek8s-design-pdf`). The build fails on a link without a
  target, so keep links relative (`x.md#heading`) and fix every link to a renamed heading.
- **History**: v1 - the options v2.0 removed, the two-cell lab and the section renumberings of 2026-10-17 that older
  commits and issues cite - is in the `v1.15` tag; v2.0 still carried the lab's state and the implementation's names,
  removed in v2.1; v2.2 removed ACNS and its page 5.1 (5.2 and 5.3 became 5.1 and 5.2), kept in the `v2.1` tag;
  v3.0 cut the design PDF under 100 pages: other clouds and exit on 7.5 (outside the PDF), the company firewall's
  delegation options in 7.1, Kubernetes and AKS mechanics replaced by links to the documentation.

## The design in v3.0

One cell network: Azure CNI Pod Subnet with dynamic IP allocation and Cilium (D74) - nodes and internal load
balancers in `/24` slots of `address_space` (slot 0 the system pool, a slot per zone index), pods in
`pod_address_space`, a `/16` of 100.64.0.0/10 with a `/20` per slot. The hub Firewall (one per exposure, D53) sees the
pods' own addresses and decides egress per application rule file in every cell; ACNS (FQDN filtering, Hubble, eBPF
host routing) is not used, each part an option in 7.4 with a measured trigger (D61, D80). Zone-to-zone traffic goes through the hub Firewall (D73). Zone
nodes are classic node pools with the cluster autoscaler - `<zone>`, `<zone>spot`, `<zone>arm`, `<zone>armspot`, from
zero, the priority expander putting spot first; GPUs a `<zone>gpu` pool on request (D42); node auto provisioning only
when it supports the pod subnet (7.4 watch list). No AKS Automatic (D79). Private API servers over Private Link (D58,
VNet integration open as H14), no public endpoints (D60), KMS data encryption (D22), Traefik with HTTP/2 and TLS 1.3
only at the edge and h2c upstream (D69-D71, V29 open), Flux's webhook only in a cell with a public entry point (D78),
Git refs with one branch per cell (D77); other clouds, sovereignty and exit only on 7.5. The implementation project (7.1) builds and accepts the dev environment in a
separate build tenant, starting with one internal cell behind a firewall VM that enforces the designed Firewall
Policies (D57); the stateful cluster and backup (6.3) are built with the first approved stateful exception.
