# 21. Open standards and portability

![Open standards and portability](../images/21-portability.svg)

**OneK8s** is named after the one ring that rules them all: **one platform that runs in any public cloud without
changes to the applications or to how they are deployed.** Azure (AKS) is the first cloud implemented and the
only one built today; AWS (EKS) and Google Cloud (GKE) are the targets. Everything this design describes for Azure
is chosen so that a second cloud is *another implementation of the same platform*, not a second platform.

The rule that makes it work: **applications, their manifests and the platform's in-cluster configuration speak
only open standards. Cloud-specific choices live in exactly two places** – the infrastructure-as-code repositories
of that cloud, and a handful of values per cluster (`cluster-settings`) that the IaC hands to Flux.

## What is the same in every cloud

| Layer | Open standard / project | In this platform |
|---|---|---|
| Container images | [OCI image and distribution specs](https://opencontainers.org/) | Every app is an OCI image; every cloud registry (ACR, ECR, Artifact Registry) serves the same image |
| Cluster API | Kubernetes, [CNCF certified](https://www.cncf.io/training/certification/software-conformance/) on AKS, EKS and GKE | Manifests use only GA Kubernetes APIs; no cloud CRDs in team repositories |
| Delivery | [Flux](https://fluxcd.io/) (CNCF graduated), Kustomize, Helm | The same Git repositories and Kustomizations reconcile every cluster ([section 10](10-keeping-clusters-in-sync.md)) |
| Ingress | [Gateway API](https://gateway-api.sigs.k8s.io/) with Traefik Proxy | Teams write `HTTPRoute`s; the Gateway, its listeners and TLS are the platform's ([section 13](13-encryption-in-transit-and-tls.md)) |
| Secrets | [External Secrets Operator](https://external-secrets.io/) | Teams write `ExternalSecret`s against a `SecretStore` named `key-vault`; only the store's provider is cloud-specific ([section 6](06-workload-identity-and-secrets.md)) |
| Identity | OIDC workload identity federation | Pods get cloud tokens through a Kubernetes service account – Entra Workload ID, EKS Pod Identity / IRSA, GKE Workload Identity Federation – never stored keys |
| DNS | [external-dns](https://kubernetes-sigs.github.io/external-dns/) | Publishes listener hostnames in Azure DNS, Route 53 or Cloud DNS – one provider flag |
| Network policy | Kubernetes `NetworkPolicy`, Cilium | Deny-by-default between namespaces in every cloud; AKS, EKS and GKE all offer Cilium-based data planes |
| Workload security | Pod Security Standards, `ValidatingAdmissionPolicy` (CEL) | Built into Kubernetes, enforced the same way everywhere ([section 14](14-policy-enforcement.md)) |
| Telemetry | [OpenTelemetry](https://opentelemetry.io/), Prometheus | Apps emit OTLP; the collector's destination is configuration ([section 19](19-observability-with-grafana-cloud.md)) |

The example application shows it end to end: [aks-hello](https://github.com/onek8s/aks-hello) and its manifests in
[aks-fluxcd-example](https://github.com/onek8s/aks-fluxcd-example) contain no Azure name at all. The same
`Deployment` and `HTTPRoute` run on `aks-dev-stateless-az1` and `aks-dev-stateless-az2` today, and
https://hello.onek8s.lol says which cluster answered.

## Data in PaaS services that every cloud offers

Data belongs in managed PaaS services ([section 8](08-cluster-types-stateless-and-stateful.md)). To stay portable,
an application **talks to a data service through its open protocol, never through a cloud SDK**, and gets its
endpoint and credentials from a Kubernetes `Secret` (synced by External Secrets, or – preferably – an identity-based
login with workload identity). The platform offers only services that **every major cloud runs as a managed
service with the same wire protocol**:

| Service | Protocol / API | Azure | AWS | Google Cloud |
|---|---|---|---|---|
| PostgreSQL | PostgreSQL wire protocol | Azure Database for PostgreSQL – Flexible Server | Amazon RDS for PostgreSQL, Aurora PostgreSQL | Cloud SQL for PostgreSQL, AlloyDB |
| MySQL | MySQL protocol | Azure Database for MySQL – Flexible Server | Amazon RDS for MySQL, Aurora MySQL | Cloud SQL for MySQL |
| Redis / Valkey | RESP (Redis protocol) | Azure Managed Redis | Amazon ElastiCache (Valkey, Redis OSS), MemoryDB | Memorystore for Valkey / Redis |
| MongoDB | MongoDB wire protocol | Azure Cosmos DB for MongoDB (vCore) | Amazon DocumentDB (MongoDB compatible) | Firestore with MongoDB compatibility |
| Kafka | Kafka protocol | Azure Event Hubs (Kafka endpoint) | Amazon MSK | Google Cloud Managed Service for Apache Kafka |
| Object storage | S3 API (on Azure through a gateway) | Azure Blob Storage | Amazon S3 | Cloud Storage (S3-compatible XML API) |
| Secrets | External Secrets provider | Azure Key Vault | AWS Secrets Manager | Google Secret Manager |
| Container registry | OCI distribution | Azure Container Registry | Amazon ECR | Artifact Registry |

Every cloud's offer is *compatible*, not identical: version support, extensions (for example PostgreSQL
extensions), MongoDB feature coverage and Redis modules differ. So:

- An application uses **the common subset**: core PostgreSQL features and widely available extensions, standard
  Redis commands without modules, the MongoDB features DocumentDB, Cosmos DB and Firestore all support. A team that
  needs more records it as an exception in its onboarding, because that exception pins it to one cloud.
- **Vendor-neutral managed offers** that run in all three clouds – MongoDB Atlas, Confluent Cloud, Aiven, Redis
  Cloud – are acceptable alternatives where the cloud-native service falls short, ordered through the marketplace
  so billing and networking (Private Link / PrivateLink / Private Service Connect) stay in the cloud.
- Services **without** a cross-cloud equivalent with the same protocol (for example Cosmos DB's NoSQL API, DynamoDB,
  Spanner, Service Bus) are not offered as platform services.

## What stays cloud-specific

| Piece | Where | Azure today |
|---|---|---|
| Tenant, accounts / subscriptions, policy, hub network | Landing zone repository | [azure-landing-zone](https://github.com/onek8s/azure-landing-zone) (ALZ accelerator) |
| Clusters and what an environment's clusters share: network, secret store, registry, DNS, global traffic manager | Cluster IaC repository | [aks-terraform](https://github.com/onek8s/aks-terraform) |
| The few facts the cluster needs about its cloud: secret store URL, identities' client IDs, DNS zone, load balancer annotations, StorageClass | `cluster-settings` of each cluster, filled in by the IaC | `clusters/<cluster>/cluster-settings.yaml` in [aks-fluxcd-platform](https://github.com/onek8s/aks-fluxcd-platform) |
| Providers of a few platform components | Platform repository, per cloud overlay | External Secrets `azurekv`, external-dns `azure`, Azure load balancer annotations on Traefik |
| Day-2 tools that read the cloud | [aks-ai-agents](https://github.com/onek8s/aks-ai-agents) | Azure tools behind a cloud-neutral tool interface |

Two Azure specifics are accepted on purpose and have a counterpart elsewhere: the AKS GitOps extension installs
Flux (on EKS / GKE Flux is bootstrapped the usual way – the `GitRepository` and `Kustomization` objects are the same),
and the Azure Policy add-on enforces Azure-side policy (the in-cluster rules use portable Pod Security and
`ValidatingAdmissionPolicy`).

## Adding a cloud

Adding AWS or Google Cloud is a defined amount of work, and none of it touches application repositories:

1. **Landing zone** for the cloud (AWS Control Tower / Landing Zone Accelerator, Google Cloud Foundation
   blueprints): accounts or projects, policy, network hub, the public DNS delegation.
2. **Cluster IaC** (`eks-terraform`, `gke-terraform`): the same inputs as aks-terraform – clusters, shared network,
   secret store, registry, DNS zone, workload identities per namespace, global traffic steering – and the same
   outputs into `cluster-settings`.
3. **Platform overlay**: the cloud's provider for External Secrets and external-dns, load balancer annotations for
   Traefik, the StorageClass of portable disks.
4. **Clusters directory** per new cluster in the platform repository, and the team namespaces in the cluster IaC.
5. **Acceptance**: the reference application and aks-hello deploy unchanged from the same commits, and the same
   tests pass ([section 17](17-implementation-project-and-acceptance-testing.md)).

Teams then choose a cloud per environment or per workload through configuration – or run in several at once behind
global DNS, as `hello.onek8s.lol` already runs across two clusters.

---

[Back to contents](../README.md) · Previous: [20. Backup and region recovery](20-backup-and-region-recovery.md) · Next: [Open questions](open-questions.md)
