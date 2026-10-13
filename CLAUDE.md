# OneK8s design - notes for Claude sessions

The shared working notes for all OneK8s repos (what is deployed, decisions, gotchas) are in
`onek8s/aks-terraform/CLAUDE.md`. Read that first.

This repo is the design, published with GitHub Pages (`docs/01-...21-*.md`, `requirements.md`,
`open-questions.md`; diagrams in `diagrams/`, rendered as described in `docs/editing-the-pictures.md`).
When an implementation decision changes the design, update the affected sections here in the same
round. Decisions already reflected: Traffic Manager instead of Front Door; public API server as a dev
lab exception; zone gateways and ESOs on the system pool so zone nodes scale to zero; spot and
architecture chosen per application with on-demand fallback; App Routing's Gateway API (`approuting-istio`)
instead of Traefik.
