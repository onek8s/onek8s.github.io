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
- **The design follows the implementation** (the user's rule): every page states what runs as "built today" and what
  the design intends as "target"; when something is built differently, the design changes in the same round. When an
  implementation decision changes the design, update the affected sections here too.
- **Versions** (the user): the design is **v2.0 since 2026-10-19**. Every pull request that changes the design adds
  the next minor version (v2.1, v2.2, ...; a major version only when a human says so) at the top of
  `docs/8.1-release-notes.md` - `## v2.N - <date>`, one short sentence per change ending in the pull request link
  (`[#NN](https://github.com/onek8s/onek8s.github.io/pull/NN)`) - and sets the same `version:` in `_config.yml`;
  create the pull request first if its number is not known yet. `check.sh` fails when the two disagree or an entry
  has no pull request link. Every version is tagged `v<version>` in every repository by aks-terraform's `Design tags`
  workflow (`design-tags.yml`, hourly and by hand): merge a round's code pull requests before the design's.
- **Three PDFs**: the summary (`/onek8s-design-summary.pdf`, page `1.0-summary.md` alone - every line links a
  section, it adds nothing of its own), the design (`/onek8s-design.pdf`, parts 1-6) and the reference
  (`/onek8s-design-reference.pdf`, parts 7-8), built by `scripts/pdf.py --only` from `_site` in nav order with
  headless Chrome (Pages workflow; `Check` attaches them as `onek8s-design-pdf`). The build fails on a link without a
  target, so keep links relative (`x.md#heading`) and fix every link to a renamed heading.
- **History**: v1 - the options v2.0 removed, the two-cell lab and the section renumberings of 2026-10-17 that older
  commits and issues cite - is in the `v1.15` tag.

## The design in v2.0

One cell network: Azure CNI Pod Subnet with dynamic IP allocation and Cilium (D74) - nodes and internal load
balancers in `/24` slots of `address_space` (slot 0 the system pool, a slot per zone index), pods in
`pod_address_space`, a `/16` of 100.64.0.0/10 with a `/20` per slot. The hub Firewall (one per exposure, D53) sees the
pods' own addresses and decides egress per application rule file; ACNS (Cilium FQDN policies, eBPF host routing) is
optional per cell, Hubble off in the lab (D56, D61). Zone-to-zone traffic goes through the hub Firewall (D73). Zone
nodes are classic node pools with the cluster autoscaler - `<zone>`, `<zone>spot`, `<zone>arm`, `<zone>armspot`, from
zero, the priority expander putting spot first; GPUs a `<zone>gpu` pool on request (D42, not built); node auto
provisioning only when it supports the pod subnet (7.4 watch list). No AKS Automatic (D79). Private API servers over
Private Link (D58, VNet integration open as H14), no public endpoints (D60), Traefik with HTTP/2 and TLS 1.3 only at
the edge and h2c upstream (D69-D71, V29 open), Flux's webhook only in a cell with a public entry point (D78), Git
refs with one branch per cell (D77). The dev lab (D57, D79) is one cell, `aks-dev-int-stateless-az3` in
germanywestcentral (Sweden's `int-se`, 10.100.0.0/16 + pods 100.64.0.0/16) behind labfw in the hub; Finland's
`int-fi` stays defined but no lab cell runs it; the stateful cluster (pod subnet too) is never deployed. Backup (6.3)
is left open on purpose: it is built with the stateful cluster.

Known code-side gaps noted in the design: aks-ai-agents `versions.py` steps the slow speed by 30 days and matches
`sl-az1`/`sf` names (D11 wants 3 weeks and the real cluster names); the upgrade agent edits a tfvars file that does
not exist; the egress check and `--check` of the traffic flow docs are not wired into any CI.
