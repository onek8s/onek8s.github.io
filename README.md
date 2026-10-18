# OneK8s

**One Kubernetes platform, one application contract for every cloud – built on Azure (AKS) first.** The name comes
from the one ring that rules them all: one platform whose applications run in any public cloud **without changes to
the applications or to how they are deployed** (R26). Applications,
their manifests and the platform's in-cluster configuration use only open standards – Kubernetes, OCI, Flux, the
Gateway API, External Secrets, OIDC workload identity – and data lives in PaaS services that every major cloud offers
with the same protocol (PostgreSQL, MySQL, Redis / Valkey, MongoDB, Kafka). Only the landing zone and the cluster
infrastructure-as-code are cloud-specific ([section 1.3](docs/1.3-open-standards-and-portability.md)). The *contract* is
portable today; the platform under it is an AKS platform that leans on what Azure manages, and a second cloud is
another implementation of it, not a lift of this one.

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

The platform is **private by default**: no PaaS service, vault, registry or API server takes public network access,
and the only public endpoints are the external zones' gateways ([D60](docs/7.2-decisions.md#decision-matrix)). Egress
leaves through the exposure's **hub Azure Firewall**, which decides per isolation zone by default; per-application
egress (Cilium FQDN policies with ACNS, or pod addresses in the Firewall's rules) is a per-cell choice
([D61](docs/7.2-decisions.md#decision-matrix), [section 5.2](docs/5.2-egress-control-options-and-the-company-firewall.md)).

> Status: **draft** for review ([release notes](docs/8.3-release-notes.md)). Country codes `fi` / `se` and
> all IP ranges are examples. The whole design is also one [PDF](https://onek8s.github.io/onek8s-design.pdf), rebuilt with
> every publish.

## Contents

The sections are numbered by part and page in reading order; the decision log and the implementation repositories cite them by number.

**1. Start here**

- [1.1 Overview](docs/1.1-overview.md) – the hub-and-spoke landing zone with a hub per exposure, and the inner layout
  every cluster shares.
- [1.2 Requirements](docs/1.2-requirements.md) – the requirements and how the design meets each; the vocabulary: exposures,
  isolation zones, cells, the Key Vaults.
- [1.3 Open standards and portability](docs/1.3-open-standards-and-portability.md) – what is the same in every cloud,
  the thin cloud-specific layer, the PaaS services every cloud offers, sovereignty and exit.

**2. Inside a cluster**

- [2.1 Network layout](docs/2.1-network-layout.md) – an address space and subnets per isolation zone in the cluster's
  VNet; NSGs and routes through the exposure's firewall.
- [2.2 Control plane](docs/2.2-control-plane.md) – a private API server in its own subnet, reached only from the
  management network; no local accounts, no SSH.
- [2.3 Node pools](docs/2.3-node-pools.md) – node auto provisioning per zone in the stateless clusters (classic pools in the
  default pod-subnet cell until NAP supports it), fixed pools in the stateful one; arm64, spot and GPUs chosen by the application; pods right-sized in place.
- [2.4 Allowed and blocked flows](docs/2.4-allowed-and-blocked-flows.md) – the few flows Kubernetes needs between a
  zone and the platform, and the isolation matrix of what each principal can reach.
- [2.5 Workload identity first, Key Vault secrets only when needed](docs/2.5-workload-identity-and-secrets.md) –
  workload identity wherever Entra ID is supported; secrets only through External Secrets Operator, separated per
  application with ABAC.
- [2.6 Application multi-tenancy inside a zone](docs/2.6-application-multi-tenancy.md) – a namespace per application
  with default-deny policies, Entra ID groups per role, platform viewers, ownership and cost labels.
- [2.7 Policy enforcement with the Azure Policy add-on](docs/2.7-policy-enforcement.md) – the single policy engine:
  the day-1 rule set, mutations and validations per cluster type.

**3. The fleet**

- [3.1 Cluster types: stateless and stateful](docs/3.1-cluster-types-stateless-and-stateful.md) – where a workload
  runs; internal and external in separate subscriptions; cells with DNS affinity, home cells and migration; the
  address plan; adding a country online.
- [3.2 Environments (fourteen to twenty clusters)](docs/3.2-environments.md) – dev, acc and prd with two subscriptions
  each, and the cost and capacity model.
- [3.3 Keeping clusters in sync: Flux for stateless, pipelines for stateful](docs/3.3-keeping-clusters-in-sync.md) –
  one fleet repository and one signed artifact, delivered by Flux and by a pipeline.
- [3.4 Zero-downtime application upgrades](docs/3.4-zero-downtime-application-upgrades.md) – rollout guardrails
  enforced by policy; releases that move through the cells one at a time.
- [3.5 Zero-downtime cluster upgrades](docs/3.5-zero-downtime-cluster-upgrades.md) – the update policy with two
  speeds, drain-and-upgrade per cell, in-place upgrades of the stateful cluster.

**4. Encryption**

- [4.1 Encryption in transit and TLS](docs/4.1-encryption-in-transit-and-tls.md) – VNet encryption between nodes, an
  HTTPS-only Gateway API gateway per zone, certificates issued centrally and distributed through the platform Key
  Vault.
- [4.2 Encryption at rest with customer-managed keys](docs/4.2-encryption-at-rest-and-customer-managed-keys.md) – a
  key per control plane, per cluster's node disks and per zone's persistent volumes; rotation and revocation.

**5. Egress control**

- [5.1 Advanced networking: eBPF host routing and FQDN egress](docs/5.1-advanced-networking-and-fqdn-egress.md) –
  Advanced Container Networking Services with per-application Cilium FQDN egress policies.
- [5.2 Egress control options and the company firewall](docs/5.2-egress-control-options-and-the-company-firewall.md)
  – overlay or pod subnet, Cilium or the hub firewall: the four combinations and a fifth, one AKS Automatic
  cluster per zone; the default (pod subnet + the hub Firewall), and working with a firewall another team owns.
- [5.3 Traffic flow documentation: a picture per application and per zone](docs/5.3-traffic-flow-documentation.md)
  – generated from Git, every destination with its status.

**6. Operations**

- [6.1 AI-driven day 2 operations](docs/6.1-ai-driven-day-2-operations.md) – agents that observe with read-only
  identities and change the platform only by pull request, inside guardrails that humans own.
- [6.2 Observability with Grafana Cloud](docs/6.2-observability-with-grafana-cloud.md) – one stack per environment,
  Grafana Alloy collecting node-locally, Private Link, SLO gates and security detections.
- [6.3 Backup and region recovery](docs/6.3-backup-and-region-recovery.md) – only persistent data is backed up,
  immutably, into the paired region; clusters are rebuilt from IaC and Git.

**7. Delivery and decisions**

- [7.1 Implementation project and acceptance testing](docs/7.1-implementation-project-and-acceptance-testing.md) – a
  separate build tenant, the phases and the backlog, the acceptance tests, security reviews and the connection
  readiness gate.
- [7.2 Decisions](docs/7.2-decisions.md) – the decision log with options and justification, the Azure capability and
  verification matrix, and the human sign-offs still needed.
- [7.3 Open questions](docs/7.3-open-questions.md) – the recently added features a person still has to weigh, each with
  the design's default until then.
- [7.4 Outlook: 2030 and the options kept open](docs/7.4-outlook-2030-and-the-options-kept-open.md) – what is meant
  to hold, what is changing, the rule that keeps the platform simple, and every feature left out today with its way in.

**8. Appendix**

- [8.1 Comparison with Wolkwacht](docs/8.1-wolkwacht-comparison.md) – where the design agrees with, differs from, or closed
  a gap raised by a well-known AKS blog.
- [8.2 Editing the pictures and the site](docs/8.2-editing-the-pictures.md) – diagram sources and rendering, the site's
  layout and navigation, the PDF, building it locally.
- [8.3 Release notes](docs/8.3-release-notes.md) – the design's versions from v1.0 on, one sentence and the pull request
  per change.

## Repositories

| Repository | What it holds |
|---|---|
| [onek8s.github.io](https://github.com/onek8s/onek8s.github.io) | This design ([onek8s.github.io](https://onek8s.github.io/)) |
| [azure-landing-zone](https://github.com/onek8s/azure-landing-zone) | The Azure landing zone of the build tenant: management groups, policy, hub, subscriptions, the public DNS zone |
| [aks-terraform](https://github.com/onek8s/aks-terraform) | The AKS clusters and what an environment's clusters share: network, Key Vault, container registry, Traffic Manager |
| [aks-fluxcd-platform](https://github.com/onek8s/aks-fluxcd-platform) | What Flux deploys into every cluster: the zones' Gateways, External Secrets, external-dns, policies, tenants |
| [aks-fluxcd-example](https://github.com/onek8s/aks-fluxcd-example) | An application team's repository – cloud-neutral manifests |
| [aks-hello](https://github.com/onek8s/aks-hello) | The example application, deployed in the dev lab's internal cells (`hello.int-fi.dev.onek8s.lol`, reachable over the lab's VPN) |
| [aks-ai-agents](https://github.com/onek8s/aks-ai-agents) | AI agents for day-2 operations ([section 6.1](docs/6.1-ai-driven-day-2-operations.md)) |
