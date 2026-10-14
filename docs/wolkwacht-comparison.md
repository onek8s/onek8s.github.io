# Comparison with Wolkwacht

[Wolkwacht](https://wolkwacht.nl) is the blog of Jurgen Allewijn (Microsoft MVP for Azure and Kubernetes). It covers
AKS architecture, security, multi-cluster operations and digital sovereignty. All 50 posts published by
**12 October 2026** were reviewed; the ones that bear on the platform were read in full and compared with this
design. Most of the blog's recommendations are generic AKS
guidance, written for a single cluster or a small fleet. This design is a multi-cluster platform with stricter
isolation and portability requirements, so a difference is not automatically a gap.

The comparison falls into three groups:

1. **Agreements**: the blog and the design reach the same conclusion.
2. **Deliberate differences**: the design chooses otherwise, for a reason that follows from its requirements.
3. **Gaps**: the blog raises something the design did not cover. This comparison closed them in the design, or
   recorded them in the [decision log](decisions.md).

## Agreements

| Topic | Wolkwacht | This design |
|---|---|---|
| API server | Private cluster, Entra ID with Azure RBAC, least privilege, cluster-admin only for emergencies ([Secure AKS](https://wolkwacht.nl/posts/secure-azure-kubernetes-service-aks/)) | Private, VNet-integrated API server reached only from the management VNet; Entra ID, PIM, read-only humans ([section 3](03-control-plane.md)) |
| Workload credentials | Entra Workload ID, no long-lived secrets in the cluster | Workload identity first, local auth disabled on the PaaS services ([section 6](06-workload-identity-and-secrets.md)) |
| Secrets for a platform team | ESO is the better paved road for a platform, *if* it comes with scoped stores, separate identities, restricted `Secret` reads, a KMS posture, stale-sync alerts and tested reloads ([Secrets showdown](https://wolkwacht.nl/posts/2026-09-05_secrets-management-showdown--azure-key-vault-csi-driver-vs-external-secrets-operator/)) | ESO per zone with every one of those controls: one `SecretStore` per namespace, a separate reader identity per application, ABAC, KMS with customer-managed keys, `SecretSynced` alerts, volume mounts that reload ([section 6](06-workload-identity-and-secrets.md#delivered-only-by-external-secrets-operator)) |
| Admission policy | Azure Policy add-on, pod security *restricted* initiative, audit first, then deny | The same, as the single policy engine, rolled out audit → deny per environment ([section 14](14-policy-enforcement.md)) |
| GitOps | Flux, pull-based, drift corrected, clusters rebuilt from Git ([GitOps with Flux](https://wolkwacht.nl/posts/gitops-on-azure-kubernetes-service-building-a-production-ready-platform-with-flux/)) | Flux from signed OCI artifacts; clusters are cattle ([section 10](10-keeping-clusters-in-sync.md)) |
| Node OS | Azure Linux: smaller, faster patches ([Security demystified](https://wolkwacht.nl/posts/azure-kubernetes-security-demystified-from-nodes-to-pods/)) | Azure Linux 3.0 on every node ([section 4](04-node-pools.md)) |
| Network policy | Cilium, deny by default, allow by exception | Cilium default deny, FQDN-only egress, three enforcement layers ([sections 5](05-allowed-and-blocked-flows.md), [16](16-advanced-networking-and-fqdn-egress.md)) |
| Nodes and autoscaling | NAP is the preferred default; autoscalers are interacting control loops; VPA and HPA must not act on the same signal ([Reducing AKS costs](https://wolkwacht.nl/posts/reducing-aks-costs-autoscaling-spot-nodes-rightsizing-and-finops-practices/)) | NAP in the stateless clusters; VPA controls only the resource the HPA does not scale on ([section 4](04-node-pools.md#pod-right-sizing-vertical-scaling-in-place)) |
| Spot | Spot is an interruption domain: tolerate it, *prefer* it, fall back to on-demand, and do not count on PDBs | Tainted spot `NodePool`, preferred affinity, on-demand fallback, applications opt in ([section 4](04-node-pools.md#cpu-architecture-and-spot-chosen-by-the-application)) |
| Encryption at rest | Customer-managed keys; Kubernetes `Secret`s are only base64, so check KMS | CMK for etcd (KMS), node disks and persistent volumes ([section 18](18-encryption-at-rest-and-customer-managed-keys.md)) |
| Blast radius | Architecture decides how far a failure travels; isolate the management plane; separate production from non-production ([Architecture decides the blast radius](https://wolkwacht.nl/posts/architecture-decides-the-blast-radius/)) | Cells and isolation zones (bulkheads), management VNet, environments in separate subscriptions ([requirements](requirements.md#cells-and-bulkheads)) |
| Observability across clouds | Vendor-neutral Prometheus and Grafana instead of one cloud's monitoring ([Chronicles 11](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-11-governing-the-chaos/)) | Grafana Cloud with OpenTelemetry for every cluster ([section 19](19-observability-with-grafana-cloud.md)) |
| Backup and DR | Backups must be tested; DORA requires defined RTO / RPO and recovery tests ([Chronicles 4](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-part-4/)) | Immutable copies in the paired region, region recovery drill every six months ([section 20](20-backup-and-region-recovery.md)) |
| Chaos engineering | Azure Chaos Studio, experiments under load, tied to SLOs ([Harnessing chaos](https://wolkwacht.nl/posts/harnessing-chaos-implementing-chaos-engineering-with-azure-chaos-studio-and-gremlin-on-aks/)) | Chaos Studio in acceptance, every fault under load, each must raise its alert ([section 17](17-implementation-project-and-acceptance-testing.md#high-availability-and-resilience)) |
| Multi-cluster is the norm | Regulation, resilience and separation of concerns lead to many clusters ([Chronicles 7](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-7-the-multi-cluster-reality/)) | Fourteen to twenty clusters per platform: one cell per availability zone and exposure, internal and external in separate subscriptions ([section 9](09-environments.md)) |

## Deliberate differences

| Topic | Wolkwacht recommends | This design | Why |
|---|---|---|---|
| Kubernetes and node image upgrades | Auto-upgrade channel `stable` plus node OS channel `NodeImage`, or AKS Automatic, which manages upgrades for you | Channel `none` in the stateless cells; a version pipeline with two speeds, applied only while a cell is drained ([section 12](12-zero-downtime-cluster-upgrades.md#update-policy)) | Nothing may change a cell outside the drain → change → test → return procedure (R12), and one cell must always run a version already proven in prd (R12a). The blog's own concern – a new node starting from an old image – is answered by pinning the image per cell ([decision D11](decisions.md#decision-matrix)) |
| Secrets delivery | The Secrets Store CSI driver as the secure default for applications that read files ([Secure AKS](https://wolkwacht.nl/posts/secure-azure-kubernetes-service-aks/)) | CSI disabled; ESO only (R7b) | One delivery path for all applications, pods start during a Key Vault outage, and ESO has providers for every cloud. The blog's later [showdown](https://wolkwacht.nl/posts/2026-09-05_secrets-management-showdown--azure-key-vault-csi-driver-vs-external-secrets-operator/) reaches the same conclusion for platform teams |
| Monitoring | Container Insights and Azure Managed Prometheus / Grafana | Grafana Cloud through Private Link; the monitoring add-on is not enabled | R22, and the same collector in every cloud |
| Ingress | [Application Gateway for Containers](https://wolkwacht.nl/posts/application-gateway-for-containers-the-future-of-cloud-native-ingress/) as a managed Gateway API implementation, behind Front Door | AKS App Routing's Gateway API implementation (Azure-managed, sidecar-less Istio) inside the cell, one `Gateway` per isolation zone on the system pool; no AGC and no Front Door ([section 13](13-encryption-in-transit-and-tls.md)) | The Azure standard offering, upgraded by AKS, and open-source Istio is available in other clouds too. Each zone's entry point (Envoy pods, load balancer) is part of its bulkhead; the control plane is shared per cell. Applications write only `HTTPRoute`s, so they would not change if a cell used AGC instead |
| East-west security | [Azure Kubernetes Application Network](https://wolkwacht.nl/posts/azure-kubernetes-application-network-part-1-what-appnet-is-and-how-to-get-started/): managed Istio ambient, mTLS and authorisation by workload identity and HTTP method / path | No service mesh: VNet encryption between nodes, Cilium policies by namespace and label (R9b) | No sidecars or waypoints to run and upgrade; AppNet is preview and AKS-only. The cost is that there is no identity-based L7 authorisation between services inside a zone – decided against for now ([decision D38](decisions.md#decision-matrix)) |
| Multi-cluster management | [Azure Kubernetes Fleet Manager](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-6/): resource placement and update runs from a hub | Flux per cell and pipelines that drain each cell at Traffic Manager ([section 11](11-zero-downtime-application-upgrades.md#releases-cell-by-cell)) | Releases and upgrades are tied to draining the cell, which Fleet does not do. Fleet is AKS-only, as the blog itself notes in [Chronicles 8](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-8-fleet-in-focus/) |
| Burst capacity | [Virtual nodes](https://wolkwacht.nl/posts/when-your-cluster-isnt-sufficient-introducing-virtual-pools-in-aks/) (Azure Container Instances) as a pressure relief valve | Not used ([section 16](16-advanced-networking-and-fqdn-egress.md#cluster-settings)) | The blog lists the limits itself: no Cilium policies, no DaemonSets. Here that would bypass FQDN egress, zone pinning and telemetry |
| Kernel-level tracing | [Inspektor Gadget](https://wolkwacht.nl/posts/when-kubernetes-lies/) installed in the cluster as a privileged DaemonSet | Deployed only during an incident, through break-glass ([section 19](19-observability-with-grafana-cloud.md#security-detections-and-forensics)) | A privileged, cluster-wide tracer is itself a high-value target |
| Backup tool | Velero or Kasten K10 ([Chronicles 4](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-part-4/)) | Azure Backup for AKS, vault tier, locked immutable ([section 20](20-backup-and-region-recovery.md)) | Immutability that an `Owner` cannot undo, and Cross Region Restore. In another cloud, Velero is the portable equivalent |
| Application building blocks | [Dapr](https://wolkwacht.nl/posts/what-is-dapr-and-why-run-it-on-kubernetes/) as a portable API for state, pub/sub and service calls | Not offered by the platform; applications use the open protocols of the PaaS services ([section 21](21-open-standards-and-portability.md#data-in-paas-services-that-every-cloud-offers)) | Dapr adds a sidecar and its own mTLS, which overlaps with the "no service mesh" rule. The blog also points out that changing the Dapr component does not remove the differences between brokers |
| Agents for operations | The [AKS-MCP server](https://wolkwacht.nl/posts/using-the-aks-mcp-server-in-day-to-day-operations/) with Contributor or cluster-admin, so an assistant can scale or deploy | Agents read only and change everything by pull request ([section 15](15-ai-driven-day-2-operations.md)) | Git is the only write path (R18). AKS-MCP fits as the agents' read-only tool layer |

## Gaps closed in this design

| # | What the blog raised | Change | Section |
|---|---|---|---|
| 1 | Local accounts are a back door around Entra ID ([Secure AKS](https://wolkwacht.nl/posts/secure-azure-kubernetes-service-aks/)) | `--disable-local-accounts` on every cluster, enforced by Azure Policy, tested | [3](03-control-plane.md), [14](14-policy-enforcement.md), [17](17-implementation-project-and-acceptance-testing.md) |
| 2 | SSH to nodes should be disabled ([GitOps with Flux](https://wolkwacht.nl/posts/gitops-on-azure-kubernetes-service-building-a-production-ready-platform-with-flux/)) | `--ssh-access disabled`; node diagnosis only through break-glass | [3](03-control-plane.md), [14](14-policy-enforcement.md) |
| 3 | Pods should not reach the instance metadata service | Stated and tested: the default deny and FQDN-only egress already block it | [16](16-advanced-networking-and-fqdn-egress.md#how-an-application-declares-its-egress), [17](17-implementation-project-and-acceptance-testing.md) |
| 4 | Images should be signed and the signature verified at admission ([Security demystified](https://wolkwacht.nl/posts/azure-kubernetes-security-demystified-from-nodes-to-pods/)) | CI signs every image; promotion verifies the signature, so only signed images reach acc and prd; admission audits it (AKS Image Integrity is preview and supports only `audit` today) | [9](09-environments.md), [14](14-policy-enforcement.md) |
| 5 | Hardened pod baseline beyond *restricted*: read-only root file system, no unneeded service account token | Two new admission rules, audit then deny | [14](14-policy-enforcement.md) |
| 6 | Hardening drifts; track CIS scans and the secure score over time and alert on a drop | Weekly kube-bench, secure score trend, both to the security agent; checklist repeated per minor upgrade | [14](14-policy-enforcement.md), [15](15-ai-driven-day-2-operations.md) |
| 7 | Stale vulnerable images on nodes (Image Cleaner) | Enabled on the long-lived stateful nodes; not needed on regularly replaced NAP nodes | [12](12-zero-downtime-cluster-upgrades.md#stateful-cluster) |
| 8 | Exceptions should be visible, time-limited and a little uncomfortable ([Security fails quietly](https://wolkwacht.nl/posts/security-fails-quietly-when-nobody-owns-it/)) | Azure Policy exemptions always expire; renewal is a high-tier pull request | [14](14-policy-enforcement.md) |
| 9 | Define what must never happen, and give every alert an owner ([Logging everything](https://wolkwacht.nl/posts/you-are-logging-everything-and-seeing-almost-nothing/)) | A table of security detections with owners | [19](19-observability-with-grafana-cloud.md#security-detections-and-forensics) |
| 10 | Emergency access is often never tested ([Identity is the perimeter](https://wolkwacht.nl/posts/identity-is-the-perimeter-you-forgot-to-guard/)) | Break-glass and every detection exercised in acceptance, break-glass again every six months | [17](17-implementation-project-and-acceptance-testing.md#operations) |
| 11 | Cost needs request *and* allocation efficiency; reservations cover the baseline | Both ratios in Grafana; the cost agent proposes reservations for the steady baseline | [15](15-ai-driven-day-2-operations.md#agents), [19](19-observability-with-grafana-cloud.md#what-grafana-cloud-does) |
| 12 | Across clouds, policy and identity fragment: EKS has no Azure Policy, networking differs ([Chronicles 9](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-9-eks-in-the-enterprise/), [11](https://wolkwacht.nl/posts/azure-kubernetes-chronicles-11-governing-the-chaos/)) | Section 21 claimed the in-cluster rules were portable Pod Security and CEL; they are Gatekeeper templates delivered by the Azure Policy add-on. The section now says how they, FQDN egress and human access move to another cloud | [21](21-open-standards-and-portability.md#what-stays-cloud-specific) |
| 13 | Sovereignty is location *and* jurisdiction; DORA expects an exit strategy ([Digital sovereignty](https://wolkwacht.nl/posts/digital-sovereignty-and-the-public-cloud/)) | What the design contributes to DORA / NIS2, and every dependency outside the corporate tenant listed together | [21](21-open-standards-and-portability.md#sovereignty-regulation-and-exit) |
| 14 | Chaos Studio's AKS faults depend on Chaos Mesh | Installed only for the tests, with a time-limited exemption; compatibility checked first | [17](17-implementation-project-and-acceptance-testing.md#high-availability-and-resilience) |

## Questions it raised

Recorded in the [decision log](decisions.md), each with a decision or a verification: whether signature checks at promotion are enough while Image
Integrity can only audit; identity-based east-west authorisation and Application Network; the policy engine and data
plane in a second cloud; sovereignty and a European exit target; Azure-only PaaS services that sections 6, 8 and 20
still list but section 21 excludes; Container Apps for small workloads; GPU and AI inference workloads; Chaos Mesh,
Inspektor Gadget, kube-bench and Image Cleaner compatibility; SSH and local accounts on NAP nodes and add-ons.

## Not relevant to this design

These posts were read but do not touch the design: the Azure Container Apps guides
([hands-on](https://wolkwacht.nl/posts/from-code-to-cloud-a-hands-on-guide-to-azure-container-apps/),
[costs](https://wolkwacht.nl/posts/optimizing-azure-container-apps-costs-scaling-to-zero-workload-profiles-and-finops/))
apart from the open question above, Apple container on macOS, local Dapr with OrbStack, k3s at the edge, Talos,
[AKS Desktop](https://wolkwacht.nl/posts/operating-aks-from-your-workstation/) (an operator tool that changes nothing
in the platform), the CNI and eBPF introductions (Chronicles 1–3, already reflected in sections 2 and 16), and the
general cloud cost essay.

---

[Back to contents](../README.md) · Previous: [Open questions](open-questions.md) · Next: [Editing the pictures](editing-the-pictures.md)
