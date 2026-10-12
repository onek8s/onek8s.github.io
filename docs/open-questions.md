# Open questions

- Single cluster with zones vs. one cluster per zone (or per country) – trade-off between operational cost and
  blast radius / hard network boundary.
- Can the corporate IP plan reserve a `/12` per environment for the platform (or a `/17` per country if not), and
  is the platform the owner of these prefixes in the central IPAM?
- Is CoreDNS on the shared system pool acceptable, or should each zone run its own CoreDNS? (The standard NodeLocal
  DNS setup needs host iptables rules and does not fit eBPF host routing, see [section 16](16-advanced-networking-and-fqdn-egress.md).)
- One Front Door profile per environment with a WAF policy per external zone (current draft), or a profile per zone?
- Release cadence: is one fleet release train per environment and day (or a few) fast enough, given that each cell
  costs a drain, rollout, tests and a return ramp? Which applications need a faster path?
- Client-IP affinity (external zones): how much traffic comes from large NATs (carrier-grade NAT, partners' proxies)
  or from clients that change addresses? This decides how even the load is and how many clients can meet both versions in a release.
- Internal applications, one home cell each: what recovery time is acceptable when a cell fails (alert →
  migration → DNS)? Do the corporate DNS forwarders honour a 60 s TTL, or do they enforce a minimum cache time?
- ExternalDNS across cells: confirm that a shared `txt-owner-id` with policy `upsert-only` lets the target cell take
  over records reliably (also with the source cell gone), and that the `gateway-httproute` source with an annotation
  filter publishes exactly the routes of the placed applications.
- Node auto provisioning in the stateless clusters: confirm that NAP with custom subnets per `NodePool` is supported
  (and generally available) in our region together with a private cluster, API Server VNet Integration, outbound type
  `userDefinedRouting` and the Azure Policy add-on. Fallback: classic node pools per zone with the cluster autoscaler.
- arm64 and spot in the stateless clusters: confirm that NAP offers spot and arm64 SKUs together with custom subnets
  per `NodePool`, which arm64 families (Dpsv6/Epsv6, Cobalt 100) support Azure Virtual Network encryption in our
  region, and that the Azure Policy mutations can match on pod labels (`platform/arch`, `platform/capacity`). If an
  architecture has no VNet-encryption-capable SKU, it cannot be offered. How large a share of a zone may run on spot
  (spot `NodePool` limits), and is spot allowed in prd for all zones?
- In-place OS patching of the stateful cluster (node OS channel `Unmanaged`) needs the OS package repositories, but
  the cluster is network isolated: is a private package mirror in the backend network acceptable, and is the channel
  supported for network isolated clusters? If not, the fallback is node OS channel `SecurityPatch` (security-only node
  images, which replaces nodes) inside the maintenance window.
- Update speeds: does `sl-az2` running the oldest supported minor leave enough time for its 1-month steps in every
  AKS release cycle, and should `sl-az3` follow the slow speed (current draft) or the fast one? With NAP, confirm that
  nodes created during scale-out use the pinned node image, not the newest one.
- Pod right-sizing ([section 4](04-node-pools.md#pod-right-sizing-vertical-scaling-in-place)): confirm in prototyping
  that the AKS VPA add-on runs `InPlaceOrRecreate` on 1.36 with NAP; whether Gatekeeper (Azure Policy add-on)
  sees the `pods/resize` subresource; that the built-in "requests set" policies and deployment safeguards accept pods
  whose limits are only pod-level (`spec.resources`) – the safeguards may inject container defaults that break a shared
  budget; and that `Azure Kubernetes Service RBAC Reader` can read `autoscaling.k8s.io` objects. Are the default
  starting bounds (memory not below the declared request, at most twice the declared values) right for the reference
  workloads? Should the operations agent get a safe runbook that resizes the pods of an opted-out application *up* in
  place during an incident (it reverts itself at the next rollout)?
- Key Vault ABAC is preview – acceptable for production, or fall back to vault per application until GA? (Affects only
  applications with a secret exception.)
- External Secrets Operator per zone: confirm in prototyping that a controller can be limited to its zone's
  namespaces (`controllerClass`, RoleBindings for `Secret` writes and `serviceaccounts/token`) – ESO's default
  chart lists and watches `Secret`s cluster-wide. ESO is a community project (CNCF), not an AKS add-on: is the
  platform team's own patching of it acceptable, or is commercial support needed?
- Which application stacks lack Entra ID support in their drivers/SDKs, and are they upgraded or given a secret
  exception?
- Two or three stateless clusters per environment? Two is the minimum, but then each must carry 100 % of the load and
  an AZ outage *during* an upgrade leaves no redundancy; three needs only 50 % headroom per cluster.
- "No Internet" for the stateful cluster: is the Entra ID (`AzureActiveDirectory` service tag) exception for workload
  identity acceptable, or must stateful workloads avoid Entra-authenticated access?
- Which workloads are expected to get a stateful-cluster exception, and when? The stateful cluster is built only when
  the first one is approved; is it then built in all three environments at once (recommended, to keep the topology
  identical)?
- Is one wildcard certificate per zone and environment acceptable, or do some applications need their own
  certificate (own key)?
- One platform Key Vault per environment shared by all zones (current draft), or one certificate vault per zone and
  environment if a separate vault per country is a hard requirement for keys too?
- DNS naming for the internal Let's Encrypt names (`<zone>.<env>.example.com`) and who owns the public
  validation zone.
- "No Internet" for the stateful cluster: are the Azure Policy add-on FQDNs acceptable as a second exception next to
  Entra ID?
- AI-driven operations: which model provider and region are acceptable for the agents (data residency of logs and
  diagnostics sent to the model), and is a private endpoint to it required? The agents read application logs and
  traces in Grafana Cloud like every stack user, so whatever personal data the logs hold may reach the model.
- Risk tiers: may tier-low changes (patches per timetable, digest promotion that passed acc, limits inside
  `limits.yaml`) really merge to prd without a human, or does every prd change need one human at first? Who owns
  `limits.yaml` – platform team alone, or platform + security?
- eBPF host routing: confirm with Microsoft that it is supported together with Azure Virtual Network encryption,
  node auto provisioning, API Server VNet Integration, outbound type `userDefinedRouting` and – for the stateful
  cluster – network isolated clusters, Azure CNI with a pod subnet and LTS; and that every platform DaemonSet
  (monitoring agent, Defender sensor, CSI drivers) works without host iptables rules.
- FQDN egress: is the ACNS FQDN-filtering throughput (~1 000 DNS-proxied requests per second per pod) enough for the
  busiest applications, or do some need a documented exception? Do applications accept declaring Entra ID and their
  zone Key Vault themselves (current draft, via presets), or should the platform baseline allow them for every
  workload-identity pod?
- Who approves a new Internet FQDN for a zone's Firewall allow-list (security team per request, or a pre-approved
  catalogue of common SaaS / package endpoints)?
- Git platform: GitHub (organisation rulesets, required workflows, GitHub Apps) as in the draft, or Azure DevOps with
  branch policies and build validation?
- Implementation project: is a separate build tenant, not connected to the corporate network and with Azure Policy
  in audit mode, acceptable to security and the landing zone owners ([section 17](17-implementation-project-and-acceptance-testing.md))?
  Can the platform's address prefixes be reserved in the corporate IPAM already for the build tenant? Is the accepted
  version redeployed into the corporate tenant (current draft), or is the build tenant's hub connected to the
  corporate network instead?
- Acceptance targets: latency, error budget, failover time, RPO / RTO and prd peak load for the reference
  application – who sets them, and who signs off the connection readiness gate?
- Customer-managed keys ([section 18](18-encryption-at-rest-and-customer-managed-keys.md)): ask Microsoft whether a
  disk encryption set per node pool or per `AKSNodeClass` is planned, so the OS-disk key can follow the requirement
  of a key per node pool (today one per cluster). Confirm that NAP nodes use the cluster's disk encryption set and
  encryption at host, that ephemeral OS disks with encryption at host use the customer-managed key, and in which
  subnet AKS places the private endpoint it creates to the platform vault for KMS (`snet-apiserver` is a /28).
- Is Key Vault Contributor on the platform vault for every cluster's control plane identity (needed by KMS with a
  private vault) acceptable, or do the keys move to a separate `kv-<env>-keys` vault per environment? Do the keys
  have to be HSM-protected (Key Vault Premium or Managed HSM)? Is a 12-month rotation enough?
- KMS data encryption (versionless key, automatic rotation, no re-encryption of Secrets) is preview: switch to it when
  it is GA, or earlier in dev?
- Grafana Cloud ([section 19](19-observability-with-grafana-cloud.md)): every user of an environment's stack sees
  the telemetry of all countries and zones (decided). Which Grafana Cloud region on Azure meets the data residency
  requirements for that, and which personal data may the logs therefore hold? Confirm that Azure Private Link to
  the stacks works across regions (private endpoint in the primary region, stack in another region), and which
  ingest and query host names need a Private DNS zone in the hub. Retention per signal and environment?
- Region recovery ([section 20](20-backup-and-region-recovery.md)): which RPO and RTO does the business require per
  application, and do the per-store RPOs meet them (SQL geo-restore about 1 h, but the immutable LTR copy is weekly;
  stateful volumes up to 36 h)? Vaulted backup with Cross Region Restore for AKS is still documented as preview –
  acceptable, or rely only on the operators' own backups to the immutable storage account until GA? Does Azure
  Backup for AKS work with the network isolated stateful cluster?
- Region recovery: should the backup vaults use customer-managed keys, and does Cross Region Restore keep working
  when the key's region is lost (fallback: Microsoft-managed keys with infrastructure encryption)? Is a second
  ExpressRoute / VPN connection in the paired region provisioned in advance, or built in the recovery?
- Region recovery: is rebuilding the images from Git acceptable for the RTO, or should the prd ACR be geo-replicated
  to the paired region so the deployed digests stay valid? Who owns the backup subscription and the Resource Guard
  (backup administrators and security team, current draft)?

Raised by the [comparison with Wolkwacht](wolkwacht-comparison.md):

- Image signatures ([section 14](14-policy-enforcement.md)): AKS Image Integrity (Ratify) is preview, verifies only
  Notation signatures and supports only the `audit` effect, so the draft enforces signatures in the promotion
  pipeline and only audits them at admission. Is that enough, or is an admission `deny` required – with open-source
  Ratify on Gatekeeper, which is also what another cloud would run? Does Image Integrity work in the network
  isolated stateful cluster?
- Identity-based east-west authorisation: inside a zone, Cilium policies decide by namespace and labels, and
  traffic between nodes is encrypted by VNet encryption, not mTLS. Do some applications need service-to-service
  authorisation by workload identity and HTTP method / path (for example payments)? If so, is Azure Kubernetes
  Application Network (managed Istio ambient) an option once it is GA – does it work with eBPF host routing, a private
  cluster, Traefik's own Gateway API CRDs and the "no service mesh" rule of R9b?
- Second cloud ([section 21](21-open-standards-and-portability.md#what-stays-cloud-specific)): open-source Gatekeeper
  with the same templates, or Azure Arc-enabled Kubernetes so that Azure Policy stays the one engine (R14) across
  clouds? Which Cilium-based data plane proves R20 on EKS and on GKE?
- Sovereignty ([section 21](21-open-standards-and-portability.md#sovereignty-regulation-and-exit)): do DORA or NIS2
  apply to the organisation, and does the exit strategy have to include a European provider outside US jurisdiction?
  Are GitHub, Grafana Cloud and the model provider acceptable as dependencies under the CLOUD Act?
- Platform services list: [section 21](21-open-standards-and-portability.md#data-in-paas-services-that-every-cloud-offers)
  offers only services with the same protocol in every cloud and excludes Service Bus and Cosmos DB's NoSQL API, while
  sections [6](06-workload-identity-and-secrets.md), [8](08-cluster-types-stateless-and-stateful.md) and
  [20](20-backup-and-region-recovery.md) still list Azure SQL, Service Bus and Cosmos DB. Are Azure-only services
  allowed as a documented, cloud-pinning exception (like a PostgreSQL extension), or removed from those sections?
- Small single-team workloads: may a team run outside OneK8s, for example on Azure Container Apps, when it needs no
  Kubernetes API and scales to zero most of the day – or does every workload belong on the platform for isolation,
  policy and portability?
- GPU and AI inference workloads (for example KAITO model serving) are not in scope today. If they come: which GPU
  VM sizes support VNet encryption and encryption at host, and can NAP provision them per zone?
- Chaos Studio's AKS faults use Chaos Mesh (privileged daemon, network faults through traffic control rules): does it
  work with eBPF host routing and the private API server, or is a different tool (for example Gremlin) needed for the
  in-cluster faults?
- Inspektor Gadget and kube-bench: confirm that both run with eBPF host routing and Azure Linux 3.0, and that Image
  Cleaner works in the network isolated stateful cluster (it needs a vulnerability database).
- Confirm that `--ssh-access disabled` also applies to NAP nodes, and that disabling local accounts does not break
  any AKS add-on or extension the platform uses.

---

[Back to contents](../README.md) · Previous: [21. Open standards and portability](21-open-standards-and-portability.md) · Next: [Comparison with Wolkwacht](wolkwacht-comparison.md)
