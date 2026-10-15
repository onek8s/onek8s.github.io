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
instead of the AKS cost analysis add-on (D46); namespace ownership labels (D47, R25); namespace access by Entra ID groups bound to `view`/`edit`/`admin`, with the matching Key Vault rights on the namespace's secrets (D49); soft multi-tenancy - tenants list no namespaces or secrets, platform viewers list both through a resource-group custom role, same pattern for other PaaS (D50); `edit` writes secrets without reading them (custom Key Vault Secrets Editor role), `admin` keeps Secrets Officer (D51); a hub VNet and Azure Firewall Premium per exposure with no route between them, the management VNet peered to both (D53); IPv4 only, no IPv6 planned (D54); V13 re-opened because the network isolated cluster docs list only the `NodeImage` and `None` OS channels. The Gateway API implementation is a per-cluster flag - App Routing in acc/prd, Traefik in the dev lab because istiod's requests cannot be tuned (Azure/AKS#5939), and the dev cells without the VPA add-on on one 8 GiB system node (D55); the dev cells keep ACNS for FQDN policies and eBPF host routing but turn Hubble off (D56). The dev lab (D57, 2026-10-15) is the internal exposure, Finland only (`int-fi`; Sweden disabled by `isolation_zones.<zone>.enabled = false`), one cell in AZ1 in germanywestcentral, routed through labfw in the hub in `firewall`-mode topology (no platform gateway, no Flux webhook, no Traffic Manager).
