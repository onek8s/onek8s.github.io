# OneK8s

**One Kubernetes platform, one application contract for every cloud – built on Azure (AKS) first.** The name comes
from the one ring that rules them all: one platform whose applications run in any public cloud **without changes to
the applications or to how they are deployed** (R26). Applications,
their manifests and the platform's in-cluster configuration use only open standards – Kubernetes, OCI, Flux, the
Gateway API, External Secrets, OIDC workload identity – and data lives in PaaS services that every major cloud offers
with the same protocol (PostgreSQL, MySQL, Redis / Valkey, MongoDB, Kafka). Only the landing zone and the cluster
infrastructure-as-code are cloud-specific ([section 1.3](design/1.3-open-standards-and-portability.md)). The *contract* is
portable today; the platform under it is an AKS platform that leans on what Azure manages, and a second cloud is
another implementation of it, not a lift of this one.

**Azure is the first cloud implemented**, and this design describes the Azure implementation:
a large Azure Kubernetes Service (AKS) platform with strong isolation between
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
and the only public endpoints are the external zones' gateways ([D60](design/7.2-decisions.md#decision-matrix)). Egress
leaves through the exposure's **hub Azure Firewall**, which decides per isolation zone from per-application rule
files ([D61](design/7.2-decisions.md#decision-matrix), [section 5.1](design/5.1-egress-control-and-the-company-firewall.md)).

> Status: **draft** for review ([release notes](design/8.1-release-notes.md)). Country codes `fi` / `se` and
> all IP ranges are examples.

**Who owns what.** Humans own the [requirements and acceptance criteria](requirements/0.2-requirements.md) in
`requirements/` (part 0): every change there needs a human's approval. AI owns the design in `design/` (parts 1 to 8)
and the infrastructure as code built from it: every change there needs the AI's review against the requirements.
[0.1 How we work](requirements/0.1-how-we-work.md) shows how a change flows between the two.

**Where to start.** Nobody reads all of it; enter from the side:

| You are | Read |
|---|---|
| Someone who sets or changes a requirement | [0.1 How we work](requirements/0.1-how-we-work.md), then [0.2 Requirements](requirements/0.2-requirements.md) and [0.3 Acceptance criteria](requirements/0.3-acceptance-criteria.md) (also a [PDF](https://onek8s.github.io/onek8s-requirements.pdf)) |
| A reviewer or sponsor who has to decide or sign off | [1.0 Summary](design/1.0-summary.md) (the first pages of the [design PDF](https://onek8s.github.io/onek8s-design.pdf)), then the [sign-offs](design/7.2-decisions.md#human-sign-offs-still-needed) |
| The security team | Parts 2 (inside a cluster), 4 (encryption) and 5 (egress control), then [2.4](design/2.4-allowed-and-blocked-flows.md)'s isolation matrix and the [acceptance criteria](requirements/0.3-acceptance-criteria.md) that prove them |
| An application team | [1.4 The application contract](design/1.4-application-contract.md), then [1.3](design/1.3-open-standards-and-portability.md) for why it is portable |
| An operator | Parts 3 (the fleet) and 6 (operations) |

There are two PDFs, rebuilt with every publish: the [requirements](https://onek8s.github.io/onek8s-requirements.pdf)
(part 0) and the [design](https://onek8s.github.io/onek8s-design.pdf) (every page of parts 1 to 8, the summary first).
This introduction is in neither; the site shows it.

## Contents

The sections are numbered by part and page in reading order; the decision log cites them by number. The pages
marked **(PDF)** are the [design PDF](https://onek8s.github.io/onek8s-design.pdf), those marked **(requirements PDF)**
the [requirements PDF](https://onek8s.github.io/onek8s-requirements.pdf); every page is in one of the two. Each design
page names the requirements it serves under its title.

**0. Requirements**

- [0.1 How we work: requirements-driven collaboration](requirements/0.1-how-we-work.md) (requirements PDF) – humans own
  the requirements and acceptance criteria, AI owns the design and the code; how a change flows and who approves it.
- [0.2 Requirements](requirements/0.2-requirements.md) (requirements PDF) – every requirement R1 to R26 and the
  acceptance criteria that prove it.
- [0.3 Acceptance criteria](requirements/0.3-acceptance-criteria.md) (requirements PDF) – the acceptance tests in dev:
  requirement and isolation tests, CIS benchmark, performance, high availability, upgrades, recovery, operations.

**1. Start here**

- [1.0 Summary](design/1.0-summary.md) (PDF) – the whole design in a few pages: what it is, the bets, the decisions that
  shape it, the sign-offs, the cost structure.
- [1.1 Overview](design/1.1-overview.md) (PDF) – the hub-and-spoke landing zone with a hub per exposure, and the inner layout
  every cluster shares.
- [1.2 How the design meets the requirements](design/1.2-how-the-design-meets-the-requirements.md) (PDF) – how the design
  meets each requirement; the vocabulary: exposures, isolation zones, cells, the Key Vaults.
- [1.3 Open standards and portability](design/1.3-open-standards-and-portability.md) (PDF) – what is the same in every cloud
  and the thin cloud-specific layer.
- [1.4 The application contract](design/1.4-application-contract.md) (PDF) – what an application team has to do, and nothing
  more: manifests, traffic, identity and secrets, the labels, observability, onboarding.

**2. Inside a cluster**

- [2.1 Network layout](design/2.1-network-layout.md) (PDF) – an address space and subnets per isolation zone in the cluster's
  VNet; NSGs and routes through the exposure's firewall.
- [2.2 Control plane](design/2.2-control-plane.md) (PDF) – a private API server in its own subnet, reached only from the
  management network; no local accounts, no SSH.
- [2.3 Node pools](design/2.3-node-pools.md) (PDF) – classic pools per zone with the cluster autoscaler in the stateless clusters,
  fixed pools in the stateful one; arm64 and spot chosen by the application; pods right-sized in place.
- [2.4 Allowed and blocked flows](design/2.4-allowed-and-blocked-flows.md) (PDF) – the few flows Kubernetes needs between a
  zone and the platform, and the isolation matrix of what each principal can reach.
- [2.5 Workload identity first, Key Vault secrets only when needed](design/2.5-workload-identity-and-secrets.md) (PDF) –
  workload identity wherever Entra ID is supported; secrets only through External Secrets Operator, separated per
  application with ABAC.
- [2.6 Application multi-tenancy inside a zone](design/2.6-application-multi-tenancy.md) (PDF) – a namespace per application
  with default-deny policies, Entra ID groups per role, platform viewers, ownership and cost labels.
- [2.7 Policy enforcement with the Azure Policy add-on](design/2.7-policy-enforcement.md) (PDF) – the single policy engine:
  the day-1 rule set, mutations and validations per cluster type.

**3. The fleet**

- [3.1 Cluster types: stateless and stateful](design/3.1-cluster-types-stateless-and-stateful.md) (PDF) – where a workload
  runs; internal and external in separate subscriptions; cells with DNS affinity, home cells and migration; the
  address plan; adding a country online.
- [3.2 Environments (fourteen to twenty clusters)](design/3.2-environments.md) (PDF) – dev, acc and prd with two subscriptions
  each, and the cost and capacity model.
- [3.3 Keeping clusters in sync: Flux for stateless, pipelines for stateful](design/3.3-keeping-clusters-in-sync.md) (PDF) –
  a platform repository and one per team, every change a pull request, delivered from Git by Flux and by a pipeline.
- [3.4 Zero-downtime application upgrades](design/3.4-zero-downtime-application-upgrades.md) (PDF) – rollout guardrails
  enforced by policy; releases that move through the cells one at a time.
- [3.5 Zero-downtime cluster upgrades](design/3.5-zero-downtime-cluster-upgrades.md) (PDF) – the update policy with two
  speeds, drain-and-upgrade per cell, in-place upgrades of the stateful cluster.

**4. Encryption**

- [4.1 Encryption in transit and TLS](design/4.1-encryption-in-transit-and-tls.md) (PDF) – VNet encryption between nodes, an
  HTTPS-only Gateway API gateway per zone, certificates issued centrally and distributed through the platform Key
  Vault.
- [4.2 Encryption at rest with customer-managed keys](design/4.2-encryption-at-rest-and-customer-managed-keys.md) (PDF) – a
  key per control plane, per cluster's node disks and per zone's persistent volumes; rotation and revocation.

**5. Egress control**

- [5.1 Egress control and the company firewall](design/5.1-egress-control-and-the-company-firewall.md) (PDF)
  – the hub Firewall decides from per-application rule files; why not Cilium's FQDN policies; working with a
  firewall another team owns.
- [5.2 Traffic flow documentation: a picture per application and per zone](design/5.2-traffic-flow-documentation.md) (PDF)
  – generated from Git, every destination with its status.

**6. Operations**

- [6.1 AI-driven day 2 operations](design/6.1-ai-driven-day-2-operations.md) (PDF) – agents that observe with read-only
  identities and change the platform only by pull request, inside guardrails that humans own.
- [6.2 Observability with Grafana Cloud](design/6.2-observability-with-grafana-cloud.md) (PDF) – one stack per environment,
  Grafana Alloy collecting node-locally, Private Link, SLO gates and security detections.
- [6.3 Backup and region recovery](design/6.3-backup-and-region-recovery.md) (PDF) – only persistent data is backed up,
  immutably, into the paired region; clusters are rebuilt from IaC and Git.

**7. Decisions**

- [7.2 Decisions](design/7.2-decisions.md) (PDF) – the decision log with options and justification, the Azure capability and
  verification matrix, and the human sign-offs still needed.
- [7.3 Open questions](design/7.3-open-questions.md) (PDF) – the recently added features a person still has to weigh, each with
  the design's default until then.

**8. Appendix**

- [8.1 Release notes](design/8.1-release-notes.md) (PDF) – the current version of the design, one sentence and the pull
  request per change; the older versions are in Git tags.

The environments are built from this design; the implementation lives in the other repositories of the [onek8s](https://github.com/onek8s) organisation. How to edit the pictures, the site, the PDFs and the release notes is in [CONTRIBUTING.md](https://github.com/onek8s/onek8s.github.io/blob/main/CONTRIBUTING.md); reviews of the design against outside sources are kept in [`reviews/`](https://github.com/onek8s/onek8s.github.io/tree/main/reviews) on GitHub and are not part of the
published design, nor is the repository's `archive/` folder, which keeps what no requirement names.
