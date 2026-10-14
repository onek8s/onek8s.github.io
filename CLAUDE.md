# OneK8s design - notes for Claude sessions

The shared working notes for all OneK8s repos (what is deployed, decisions, gotchas) are in
`onek8s/aks-terraform/CLAUDE.md`. Read that first.

This repo is the design, published with GitHub Pages (`docs/01-...21-*.md`, `requirements.md`,
`decisions.md` (decision log, capability matrix, human sign-offs), `open-questions.md` (only what still needs a
human); diagrams in `diagrams/`, rendered as described in `docs/editing-the-pictures.md`). A decision goes into
`decisions.md` with its options and justification; `scripts/check.sh` runs in CI (diagram freshness, links).
When an implementation decision changes the design, update the affected sections here in the same
round. Decisions already reflected: Traffic Manager instead of Front Door; public API server as a dev
lab exception; zone gateways and ESOs on the system pool so zone nodes scale to zero; spot and
architecture chosen per application with on-demand fallback; App Routing's Gateway API (`approuting-istio`)
instead of Traefik; GPU NodePools per zone on request (D42); cost per team from OpenCost in Grafana's k8s-monitoring
instead of the AKS cost analysis add-on (D46); namespace ownership labels (D47, R25); namespace access by Entra ID groups bound to `view`/`edit`/`admin`, with the matching Key Vault rights on the namespace's secrets (D49); soft multi-tenancy - tenants list no namespaces or secrets, platform viewers list both through a resource-group custom role, same pattern for other PaaS (D50).

`docs/isolation-explained.md` explains the zone isolation to security reviewers (Kubernetes glossary, the five layers,
what one cluster still shares, the cluster-per-exposure / per-country / per-zone options of D01 and the questions for
sign-off H01). `docs/isolation-active-directory.md` maps the same isolation onto Active Directory (forest, domains, Tier 0,
kill chain, lateral movement between and inside node pools); its picture 23 also exists as `diagrams/23-ad-analogy.drawio`
for draw.io and Visio, kept in step with the Mermaid source by hand. Update both pages in the same round when an
isolation control, a zone rule in section 14 or D01 changes.
