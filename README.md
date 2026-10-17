# OneK8s

**One Kubernetes platform for every cloud.** The name comes from the one ring that rules them all: one platform
that runs in any public cloud **without changes to the applications or to how they are deployed**. Applications,
their manifests and the platform's in-cluster configuration use only open standards – Kubernetes, OCI, Flux, the
Gateway API, External Secrets, OIDC workload identity – and data lives in PaaS services that every major cloud offers
with the same protocol (PostgreSQL, MySQL, Redis / Valkey, MongoDB, Kafka). Only the landing zone and the cluster
infrastructure-as-code are cloud-specific ([section 21](docs/21-open-standards-and-portability.md)).

**Azure is the first cloud implemented**; AWS and Google Cloud are the targets. This design describes the Azure
implementation: a large Azure Kubernetes Service (AKS) platform with strong isolation between
**internal / external** workloads – separate subscriptions and clusters – and between **countries** – isolation zones
with their own node pools, network and Key Vault inside a cluster – plus application multi-tenancy inside each zone.

The platform runs **two types of clusters** – zonal **stateless** clusters in the frontend network and an
**optional** zone-redundant **stateful** cluster in the Internet-less backend network – per exposure (internal,
external) in **dev, acc and prd**, i.e. fourteen clusters (twenty with the stateful clusters) kept in sync from one
Git repository – the stateless clusters with **FluxCD**, the stateful cluster with **CI/CD pipelines** – with fully
automated zero-downtime upgrades of applications and clusters. Data belongs in **Azure PaaS services**; the stateful
cluster is the *last option*, used only when no suitable PaaS service exists or a special use case requires it, and
it is **not built at all until the first such workload is approved**. All admission policies are implemented with
the AKS-native **Azure Policy add-on** (Gatekeeper managed by AKS), and day-2 operations are run by **AI agents**
that change the platform only through pull requests within human-defined guardrails.

> Status: **draft** for review. Country codes `fi` / `se` and all IP ranges are examples.

## Contents

The sections are numbered in the order they were written; the numbers are stable identifiers that the decision log
and the implementation repositories cite. Read them in the order below.

**Start here**

- [1. Overview](docs/01-overview.md) – the hub-and-spoke landing zone with a hub per exposure, and the inner layout
  every cluster shares.
- [Requirements](docs/requirements.md) – the requirements and how the design meets each; the vocabulary: exposures,
  isolation zones, cells, the Key Vaults.
- [21. Open standards and portability](docs/21-open-standards-and-portability.md) – what is the same in every cloud,
  the thin cloud-specific layer, the PaaS services every cloud offers, sovereignty and exit.

**Inside a cluster**

- [2. Network layout](docs/02-network-layout.md) – an address space and subnets per isolation zone in the cluster's
  VNet; NSGs and routes through the exposure's firewall.
- [3. Control plane](docs/03-control-plane.md) – a private API server in its own subnet, reached only from the
  management network; no local accounts, no SSH.
- [4. Node pools](docs/04-node-pools.md) – node auto provisioning per zone in the stateless clusters, fixed pools in
  the stateful one; arm64, spot and GPUs chosen by the application; pods right-sized in place.
- [5. Allowed and blocked flows](docs/05-allowed-and-blocked-flows.md) – the few flows Kubernetes needs between a
  zone and the platform, and the isolation matrix of what each principal can reach.
- [6. Workload identity first, Key Vault secrets only when needed](docs/06-workload-identity-and-secrets.md) –
  workload identity wherever Entra ID is supported; secrets only through External Secrets Operator, separated per
  application with ABAC.
- [7. Application multi-tenancy inside a zone](docs/07-application-multi-tenancy.md) – a namespace per application
  with default-deny policies, Entra ID groups per role, platform viewers, ownership and cost labels.
- [14. Policy enforcement with the Azure Policy add-on](docs/14-policy-enforcement.md) – the single policy engine:
  the day-1 rule set, mutations and validations per cluster type.

**The fleet**

- [8. Cluster types: stateless and stateful](docs/08-cluster-types-stateless-and-stateful.md) – where a workload
  runs; internal and external in separate subscriptions; cells with DNS affinity, home cells and migration; the
  address plan; adding a country online.
- [9. Environments (fourteen to twenty clusters)](docs/09-environments.md) – dev, acc and prd with two subscriptions
  each, and the cost and capacity model.
- [10. Keeping clusters in sync: Flux for stateless, pipelines for stateful](docs/10-keeping-clusters-in-sync.md) –
  one fleet repository and one signed artifact, delivered by Flux and by a pipeline.
- [11. Zero-downtime application upgrades](docs/11-zero-downtime-application-upgrades.md) – rollout guardrails
  enforced by policy; releases that move through the cells one at a time.
- [12. Zero-downtime cluster upgrades](docs/12-zero-downtime-cluster-upgrades.md) – the update policy with two
  speeds, drain-and-upgrade per cell, in-place upgrades of the stateful cluster.

**Encryption**

- [13. Encryption in transit and TLS](docs/13-encryption-in-transit-and-tls.md) – VNet encryption between nodes, an
  HTTPS-only Gateway API gateway per zone, certificates issued centrally and distributed through the platform Key
  Vault.
- [18. Encryption at rest with customer-managed keys](docs/18-encryption-at-rest-and-customer-managed-keys.md) – a
  key per control plane, per cluster's node disks and per zone's persistent volumes; rotation and revocation.

**Egress control**

- [16. Advanced networking: eBPF host routing and FQDN egress](docs/16-advanced-networking-and-fqdn-egress.md) –
  Advanced Container Networking Services with per-application Cilium FQDN egress policies.
- [22. Egress control options and the company firewall](docs/22-egress-control-options-and-the-company-firewall.md)
  – overlay or node subnet, Cilium or the hub firewall: the four combinations, the proposed default, and working
  with a firewall another team owns.
- [23. Traffic flow documentation: a picture per application and per zone](docs/23-traffic-flow-documentation.md)
  – generated from Git, every destination with its status.

**Operations**

- [15. AI-driven day 2 operations](docs/15-ai-driven-day-2-operations.md) – agents that observe with read-only
  identities and change the platform only by pull request, inside guardrails that humans own.
- [19. Observability with Grafana Cloud](docs/19-observability-with-grafana-cloud.md) – one stack per environment,
  Grafana Alloy collecting node-locally, Private Link, SLO gates and security detections.
- [20. Backup and region recovery](docs/20-backup-and-region-recovery.md) – only persistent data is backed up,
  immutably, into the paired region; clusters are rebuilt from IaC and Git.

**Delivery and decisions**

- [17. Implementation project and acceptance testing](docs/17-implementation-project-and-acceptance-testing.md) – a
  separate build tenant, the phases and the backlog, the acceptance tests, security reviews and the connection
  readiness gate.
- [Decisions](docs/decisions.md) – the decision log with options and justification, the Azure capability and
  verification matrix, and the human sign-offs still needed.
- [Open questions](docs/open-questions.md) – only what still needs a person: the sign-off list for the connection
  readiness gate.

**Appendix**

- [Comparison with Wolkwacht](docs/wolkwacht-comparison.md) – where the design agrees with, differs from, or closed
  a gap raised by a well-known AKS blog.
- [Editing the pictures and the site](docs/editing-the-pictures.md) – diagram sources and rendering, the site's
  layout and navigation, building it locally.

## Repositories

| Repository | What it holds |
|---|---|
| [onek8s.github.io](https://github.com/onek8s/onek8s.github.io) | This design ([onek8s.github.io](https://onek8s.github.io/)) |
| [azure-landing-zone](https://github.com/onek8s/azure-landing-zone) | The Azure landing zone of the build tenant: management groups, policy, hub, subscriptions, the public DNS zone |
| [aks-terraform](https://github.com/onek8s/aks-terraform) | The AKS clusters and what an environment's clusters share: network, Key Vault, container registry, Traffic Manager |
| [aks-fluxcd-platform](https://github.com/onek8s/aks-fluxcd-platform) | What Flux deploys into every cluster: the zones' Gateways (AKS App Routing), External Secrets, external-dns, policies, tenants |
| [aks-fluxcd-example](https://github.com/onek8s/aks-fluxcd-example) | An application team's repository – cloud-neutral manifests |
| [aks-hello](https://github.com/onek8s/aks-hello) | The example application, live at https://hello.ext-fi.dev.onek8s.lol on the dev lab's external cell |
| [aks-ai-agents](https://github.com/onek8s/aks-ai-agents) | AI agents for day-2 operations ([section 15](docs/15-ai-driven-day-2-operations.md)) |
