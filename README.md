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
external) in **dev, acc and prd**, i.e. fourteen clusters (twenty with the stateful clusters) kept in sync from one Git repository – the stateless clusters with **FluxCD**, the stateful cluster
with **CI/CD pipelines** – with fully automated zero-downtime upgrades of applications and clusters.
Data belongs in **Azure PaaS services**; the stateful cluster is the *last option*, used only when no suitable PaaS
service exists or a special use case requires it, and it is **not built at all until the first such workload is
approved**. All admission policies are implemented with the AKS-native **Azure Policy add-on** (Gatekeeper managed by AKS).
Pictures 1–7 describe what is *inside* one cluster; pictures 8–14 describe the fleet of clusters and how traffic is
encrypted; picture 15 shows how AI agents operate the platform through pull requests within human-defined guardrails;
picture 16 shows how every cluster uses **Advanced Container Networking Services** with **eBPF host routing**, and
how applications may send traffic out of a cluster only to destinations they have declared in an **FQDN-based egress
policy**. Picture 17 shows how the platform is built and accepted in a separate **build tenant** that is not connected
to the corporate network, before the accepted version is deployed to the corporate landing zone. Picture 18 shows how data at rest is encrypted with **customer-managed keys** from
the platform Key Vault: one key per control plane and per cluster's node disks, and one per isolation zone for
persistent volumes. Picture 19 shows how all metrics, logs and traces go to **Grafana Cloud** through Private Link,
collected node-locally by Grafana Alloy, with one stack per environment whose users see all of its data. Picture 20
shows how the platform survives the loss of the region: **only persistent data is backed up, immutably, into the
paired region**, and the clusters are rebuilt there from IaC and Git.

Picture 21 shows what makes the platform portable: what is the same in every cloud, the thin layer of cloud
adapters, and the PaaS services every cloud offers. Picture 22 puts the egress control options side by side and
picture 23 shows how the traffic flows are **documented from Git** - a picture per application and per isolation zone,
generated from the per-application firewall rule files and the applications' own configuration, because the hub
Firewall cannot say which application uses a rule.

> Status: **draft** for review. Country codes `fi` / `se` and all IP ranges are examples.

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

## Contents

- [Requirements](docs/requirements.md)
- [1. Overview](docs/01-overview.md)
- [2. Network layout](docs/02-network-layout.md)
- [3. Control plane](docs/03-control-plane.md)
- [4. Node pools](docs/04-node-pools.md)
- [5. Allowed and blocked flows](docs/05-allowed-and-blocked-flows.md)
- [6. Workload identity first, Key Vault secrets only when needed](docs/06-workload-identity-and-secrets.md)
- [7. Application multi-tenancy inside a zone](docs/07-application-multi-tenancy.md)
- [8. Cluster types: stateless and stateful](docs/08-cluster-types-stateless-and-stateful.md)
- [9. Environments (fourteen to twenty clusters)](docs/09-environments.md)
- [10. Keeping clusters in sync: Flux for stateless, pipelines for stateful](docs/10-keeping-clusters-in-sync.md)
- [11. Zero-downtime application upgrades](docs/11-zero-downtime-application-upgrades.md)
- [12. Zero-downtime cluster upgrades](docs/12-zero-downtime-cluster-upgrades.md)
- [13. Encryption in transit and TLS](docs/13-encryption-in-transit-and-tls.md)
- [14. Policy enforcement with the Azure Policy add-on](docs/14-policy-enforcement.md)
- [15. AI-driven day 2 operations](docs/15-ai-driven-day-2-operations.md)
- [16. Advanced networking: eBPF host routing and FQDN egress](docs/16-advanced-networking-and-fqdn-egress.md)
- [17. Implementation project and acceptance testing](docs/17-implementation-project-and-acceptance-testing.md)
- [18. Encryption at rest with customer-managed keys](docs/18-encryption-at-rest-and-customer-managed-keys.md)
- [19. Observability with Grafana Cloud](docs/19-observability-with-grafana-cloud.md)
- [20. Backup and region recovery](docs/20-backup-and-region-recovery.md)
- [21. Open standards and portability](docs/21-open-standards-and-portability.md)
- [22. Egress control options and the company firewall](docs/22-egress-control-options-and-the-company-firewall.md)
- [23. Traffic flow documentation: a picture per application and per zone](docs/23-traffic-flow-documentation.md)
- [Decisions](docs/decisions.md)
- [Open questions](docs/open-questions.md)
- [Comparison with Wolkwacht](docs/wolkwacht-comparison.md)
- [Editing the pictures](docs/editing-the-pictures.md)
