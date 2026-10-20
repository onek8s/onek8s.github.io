# OneK8s

**One Kubernetes platform, one application contract for every cloud – built on Azure (AKS) first.** One platform whose applications run in any public cloud **without changes to
the applications or to how they are deployed** ([R26](requirements/0.2-requirements.md#r26)). Applications,
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
