# 16. Advanced networking: eBPF host routing and FQDN egress

![eBPF host routing and FQDN egress](../images/16-fqdn-egress.svg)

> Proposed since 2026-10-16 ([D61](decisions.md#decision-matrix)): the default stateless cell runs **without** ACNS,
> with overlay and the hub Firewall deciding egress per zone ([section 22](22-egress-control-options-and-the-company-firewall.md));
> this section describes the cells that keep ACNS for per-application FQDN egress.

Every cluster enables **[Advanced Container Networking Services](https://learn.microsoft.com/en-us/azure/aks/advanced-container-networking-services-overview)**
(ACNS) on top of Azure CNI powered by Cilium, and uses two of its features:

- **[eBPF host routing](https://learn.microsoft.com/en-us/azure/aks/container-network-performance-ebpf-host-routing)**
  (container network performance) – pod traffic is routed and masqueraded by Cilium's eBPF programs instead of
  iptables / netfilter in the node's network namespace: lower latency, higher throughput and less CPU per node.
- **[FQDN filtering](https://learn.microsoft.com/en-us/azure/aks/container-network-security-fqdn-filtering-concepts)**
  (container network security) – Cilium network policies with `toFQDNs`, resolved by the ACNS security agent, a DNS
  proxy that keeps resolving and enforcing even while the Cilium agent restarts.

Container network observability (Hubble flow logs and metrics) comes with ACNS as well and is used to see dropped
egress per namespace ([below](#observing-and-troubleshooting)).

**Rule: an application can send traffic out of the cluster only to destinations that it has declared by FQDN.** No
policy means no traffic leaves the cluster; IP addresses and CIDRs cannot be used to open egress. This applies to
every destination outside the cluster – Azure PaaS private endpoints, Key Vault (External Secrets Operator and other platform components only), Entra ID, the stateful cluster's
internal load balancers, on-premises systems and the Internet – and to both cluster types.

## Why per-application FQDN policies

The hub Firewall cannot tell applications apart. In the stateless clusters the overlay SNATs pod traffic to the node
IP, so the Firewall sees only the **zone** (`snet-<zone>-nodes`); per-pod egress IPs are not available either, because
the [Static Egress Gateway](https://learn.microsoft.com/en-us/azure/aks/configure-static-egress-gateway) cannot be
combined with eBPF host routing. Without a pod-level control, every application of a zone could reach every
destination that any application of the zone needs.

The two layers therefore split the work:

| Layer | Identity it sees | Owner | Allow-list |
|---|---|---|---|
| Cilium FQDN policy (ACNS) | Pod (namespace, labels, ServiceAccount) | Application team, validated by Azure Policy | Per application: the FQDNs and ports *this* application uses |
| Azure Firewall | Zone (node subnet / pod subnet prefix) | Platform + security (high risk tier, [section 15](15-ai-driven-day-2-operations.md#risk-tiers)) | Per zone: the union of what the zone's applications may use, plus the platform FQDNs |

An application's FQDNs must be a subset of its zone's Firewall allow-list; a CI check on the fleet repository
compares the two and fails a pull request that declares an FQDN the Firewall would drop, so the gap is found at review
time rather than as a timeout in production. Adding a new external destination is therefore two changes: the
application's policy (application team) and, if the zone does not have it yet, the Firewall rule (high tier).

## Cluster settings

| Setting | Stateless clusters | Stateful cluster |
|---|---|---|
| Dataplane | `--network-plugin azure --network-plugin-mode overlay --network-dataplane cilium` | `--network-plugin azure --network-dataplane cilium` + pod subnet (dynamic allocation) |
| ACNS | `--enable-acns` (observability + security) | `--enable-acns` (observability + security) |
| eBPF host routing | `--acns-datapath-acceleration-mode BpfVeth` | `--acns-datapath-acceleration-mode BpfVeth` |
| Node OS | Azure Linux 3.0 – system pool `--os-sku AzureLinux`, NAP `AKSNodeClass` `imageFamily: AzureLinux` | Azure Linux 3.0 – all node pools `--os-sku AzureLinux` |
| Kubernetes | ≥ 1.33 (every cluster starts on 1.36) | ≥ 1.33: created on 1.36 and kept there with LTS, see below |

eBPF host routing requires Kubernetes 1.33 or later, Ubuntu 24.04 or Azure Linux 3.0 on **every** node of the cluster
(it is all or nothing), and no iptables rules in the node's network namespace. Azure Linux 3.0 is chosen because it
is the smaller image with fewer packages to patch; Ubuntu 24.04 would work too. Azure Policy enforces the OS SKU,
`imageFamily`, ACNS and the acceleration mode on the cluster resources ([section 14](14-policy-enforcement.md)).

What eBPF host routing changes for the rest of the design:

- **No iptables in the host network namespace.** AKS installs an *iptables blocker* that prevents new host iptables
  rules, and they would be bypassed anyway. Nothing in this design needs them: applications may not use
  `hostNetwork` or privileged pods, and every platform DaemonSet (CSI drivers, Grafana Alloy, Defender sensor) is
  checked for host iptables use before it is added. The standard **NodeLocal DNS** setup relies on host iptables rules
  and is therefore not used; DNS stays on CoreDNS ([decision D03](decisions.md#decision-matrix)).
- **SNAT moves to eBPF.** In the stateless clusters Cilium masquerades pod traffic with BPF instead of
  `ip-masq-agent`'s iptables rules; the Firewall still sees the node IP, so zone rules do not change. The stateful
  cluster does not masquerade (VNet-routable pod IPs) and keeps it that way.
- **Features that cannot be combined** with eBPF host routing are not used: Static Egress Gateway, Confidential VMs,
  Pod Sandboxing, Windows nodes and a self-managed Istio Ambient. The Azure Policy VM-size allow-list contains no
  confidential SKUs. **Virtual nodes** (Azure Container Instances) are not used either, for a different reason: their
  pods are not enforced by Cilium and run no DaemonSets, so they would bypass the FQDN egress policies, zone pinning
  and the node-local Grafana Alloy.
- **Enabling it rolls the nodes** (rolling node pool upgrade, existing connections may be disrupted). In the
  stateless clusters it is part of the cluster IaC from day one; changing it on an existing cell follows the
  drain-and-upgrade procedure of [section 12](12-zero-downtime-cluster-upgrades.md#stateless-clusters), one cell at a
  time. Nodes carry the label `kubernetes.azure.com/ebpf-host-routing=true`, which the cell's post-upgrade checks verify.
- It can be switched off (`--acns-datapath-acceleration-mode None`) without touching FQDN filtering – the rollback if a
  regression is found in a cell.

### Stateful cluster and LTS

The stateful cluster is created on the **second latest GA minor** (N-1, the same minor as `sl-az1`; 1.36 at the start
of the platform) and then stays on
it with Long Term Support ([update policy](12-zero-downtime-cluster-upgrades.md#update-policy)); its slower upgrade
cycle exists because of the more demanding workloads it runs, not because it starts on an old version. It therefore
meets the 1.33 requirement from day one and runs the same ACNS settings as the stateless clusters – eBPF host routing
and FQDN filtering (which needs only 1.29) – so the whole fleet has one datapath. Its later LTS minor upgrades only
move it forward, so the requirement stays met.

## How an application declares its egress

Each application namespace gets the baseline of [section 7](07-application-multi-tenancy.md) from the platform, as a
`CiliumClusterwideNetworkPolicy` that selects all pods in namespaces labelled `platform/zone`:

- egress to CoreDNS (`k8s-app: kube-dns`) on UDP/TCP 53 with a DNS rule that allows queries for
  `*.cluster.local` only;
- egress within the namespace; ingress from the zone's gateway (stateless) or the zone's node prefixes (stateful).

Because the baseline selects every application pod for egress, Cilium's **default deny** applies to everything
else: a pod without an application egress policy reaches nothing outside its namespace and nothing outside the
cluster.

The application adds **one `CiliumNetworkPolicy` named `egress`** in each of its namespaces, in its own
`apps/<app>/base` in the fleet repository. Every external destination is listed by name with its ports, and the same
names are allowed in the DNS rule, so a pod can neither resolve nor reach anything else (this also blocks data
exfiltration through DNS queries):

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress
  namespace: int-fi-orders
spec:
  endpointSelector: {}                 # all pods of the namespace; narrower selectors are allowed
  egress:
    - toEndpoints:
        - matchLabels: { k8s:io.kubernetes.pod.namespace: kube-system, k8s-app: kube-dns }
      toPorts:
        - ports: [{ port: "53", protocol: ANY }]
          rules:
            dns:
              - matchName: login.microsoftonline.com
              - matchName: psql-prd-int-fi-orders.postgres.database.azure.com
              - matchName: search.int-fi.prd.example.com
    - toFQDNs:
        - matchName: login.microsoftonline.com          # Entra ID – workload identity token exchange
      toPorts: [{ ports: [{ port: "443", protocol: TCP }] }]
    - toFQDNs:
        - matchName: psql-prd-int-fi-orders.postgres.database.azure.com   # PaaS (private endpoint)
      toPorts: [{ ports: [{ port: "5432", protocol: TCP }] }]
    - toFQDNs:
        - matchName: search.int-fi.prd.example.com      # application in the stateful cluster (internal LB)
      toPorts: [{ ports: [{ port: "443", protocol: TCP }] }]
```

- **Names, not private IPs.** Applications use the public service names (`*.postgres.database.azure.com`,
  `*.servicebus.windows.net`); the hub Private DNS zones answer with a CNAME to `privatelink.*` and the private
  endpoint IP, and Cilium allows the addresses returned for the queried name. A private endpoint that moves to a new
  IP needs no policy change.
- **Environment-specific names** (`psql-dev-…`, `psql-prd-…`) come from the Kustomize overlays like image digests;
  `stateless` and `stateful` overlays may differ.
- **Platform presets.** A Kustomize component in `infrastructure/base` offers presets – such as `entra-id` – that expand to the right names per zone and
  environment. They are still part of the application's own `egress` policy: nothing is opened for an application
  that does not ask for it. Telemetry needs no entry: the baseline allows every pod to reach the Grafana Alloy on its
  own node ([section 19](19-observability-with-grafana-cloud.md#collection-grafana-alloy-node-local)).
- **No policy, no egress.** An application that needs nothing outside the cluster simply has no `egress` policy (CI
  reports this explicitly at onboarding, so it is a decision, not an omission).
- **No instance metadata.** The Azure Instance Metadata Service (`169.254.169.254`) is a common pivot for stealing
  credentials. Application pods cannot reach it: it has no name that `toFQDNs` could allow, CIDR egress is rejected,
  and `hostNetwork` is forbidden. Workload identity does not need it. The isolation tests of
  [section 17](17-implementation-project-and-acceptance-testing.md#requirement-and-isolation-tests) check this from
  every zone.

## Two egress models under test (D59)

**Not decided yet.** Besides the model above - Cilium decides each application's egress by FQDN, the hub Firewall
holds a zone-wide allow-list behind it - the dev lab runs a second one, and the two stay configuration options under
test because their feature sets differ and neither is better on every count ([decision D59](decisions.md), sign-off
H15 in [open questions](open-questions.md)). The dev cell `aks-dev-int-stateless-az2` (Finland's `int-fi`) runs
model (a), `aks-dev-int-stateless-az3` (Sweden's `int-se`) model (b).

Model (b), **the hub Firewall decides**: no overlay network. The cell is Azure CNI node subnet with the Cilium
dataplane (node auto provisioning supports it; a pod subnet with dynamic IP allocation it does not), and its address
space is a /16 of the RFC 6598 shared range 100.64.0.0/10 - a zone's node subnet is a /21, so its pods fit beside its
nodes. Every pod keeps its own address up to the hub Firewall (AKS's ip-masq-agent translates nothing in such a
cell), so:

- **Cilium decides only inside the cluster.** The zone's baseline still denies every other endpoint of the cluster;
  a platform policy per zone (`<zone>-firewall-egress`) lets the zone's application namespaces out to the world and
  resolve any name. Applications write no egress policy.
- **The Firewall decides everything that leaves the cluster**, from rules per application
  (azure-landing-zone `firewall-applications/<env>-<exposure>/<namespace>.yaml`) whose source is the application's
  zone - the Firewall tells zones apart by their subnets, not applications within one zone.
- **An AI egress agent proposes the rules** ([section 15](15-ai-driven-day-2-operations.md)): it reads the flows the
  Firewall denied (Log Analytics; labfw ships its log there like an Azure Firewall's diagnostic setting), finds the
  pod behind each source address, checks the destination against the application's configuration, and opens one
  pull request per application with the evidence. Humans of the platform and security merge it; nothing is allowed
  automatically.
- **Nothing in 100.64.0.0/10 leaves the landing zone**: the Firewall Policies' SNAT private ranges are the landing
  zone's own (10.0.0.0/16, 172.16.0.0/12, 100.64.0.0/10), so every allowed flow to the internet or the corporate
  network is translated to the Firewall's address.

| | (a) Cilium decides (overlay) | (b) The hub Firewall decides (no overlay) |
|---|---|---|
| Who writes an application's egress | The team, a Cilium FQDN policy in its repository, checked against the zone's allow-list | Nobody up front: the agent proposes the Firewall rule from the denied flows, a human merges it |
| Granularity | Per pod selector, inside a zone | Per zone at the Firewall (rules are named per application, but open the destination to the zone) |
| Where a denial shows | Cilium (Hubble, off in the dev cells - D56) | The Firewall's log, with the pod's own address |
| Firewall features on every flow | Only on what Cilium let out | IDPS, threat intelligence, TLS inspection, one log for every flow |
| Addresses | Pods in a cluster-internal overlay range; nodes' subnets small | A /16 of 100.64.0.0/10 per cell; pods' addresses reserved per node (110 a node) |
| Node auto provisioning | Overlay - the recommended mode | Node subnet only (no pod subnet with dynamic IP allocation) |
| NSGs between the zones' subnets | Tell pods (overlay range) from nodes | Cannot: pods and nodes share the subnets - Cilium alone separates zones inside the cell |
| Day 2 | Policies change with the application | Rules follow what applications actually do; the agent and the review are the control |

### Pros and cons, one choice at a time

The two models bundle two independent choices: **how pods get their addresses** (overlay or not) and **who enforces
egress** (Cilium FQDN policies of Advanced Container Networking Services, or the hub Firewall). They are compared
separately here; the combinations follow.

**Pod addressing: Azure CNI Overlay or node subnet**

| | Overlay (az2) | No overlay, node subnet (az3) |
|---|---|---|
| Pros | Pods take addresses from a cluster-internal range (one per node block), so the VNet only holds nodes: small subnets, the same pod range in every cluster, no address planning per application. Scales to large clusters without exhausting the landing zone's address space. The recommended mode for node auto provisioning. The NSGs tell nodes (subnet) from pods (overlay range) | Every pod has a VNet address all the way to the Firewall: the Firewall log, NSG flow logs and the egress agent name the pod, not only its node. Peered networks can reach a pod directly when a design needs it. No address translation inside the landing zone, so troubleshooting sees one address end to end |
| Cons | Traffic leaving the cluster is translated to the node's address, so anything outside the cluster (Firewall, flow logs, the other end) sees only the node - it can tell zones apart (a zone has its own node subnet) but not pods or applications. A pod cannot be addressed from outside the cluster except through a load balancer | Addresses are reserved per node for `max_pods` (110 here: a node takes 111 addresses when it starts), so cells need large subnets - hence a /16 of 100.64.0.0/10 per cell, and the VNet's limit of 65,536 addresses is the cell's ceiling. `max_pods` cannot change on a running pool. Pods and nodes share the subnets, so an NSG cannot tell them apart - Cilium alone separates what runs on one subnet. Node auto provisioning supports node subnet but not a pod subnet with dynamic allocation, so pods cannot get a subnet of their own |

**Egress control: ACNS FQDN policies or the hub Firewall**

| | Cilium FQDN policies (ACNS) | Hub Firewall (Azure Firewall Premium; labfw in the lab) |
|---|---|---|
| Pros | Per application: a policy selects the application's pods, so two applications in one zone get different destinations. Enforced at the source node - a denied flow never leaves the node. Owned by the team in its own repository (GitOps), changed with the application, checked by the `fqdn-egress` policy against the zone's allow-list. Works the same in overlay and node subnet. No central bottleneck: the rule set is spread over the clusters | One enforcement point for every flow that leaves the landing zone, from any compute (AKS, VMs, PaaS with VNet integration). Premium features on every flow: IDPS, threat intelligence, TLS inspection and URL filtering, FQDN tags. One log for security, in Log Analytics. Rules are managed and reviewed centrally; applications write no egress policy, and the egress agent proposes the rules from what applications actually do. Survives a misconfigured or compromised cluster: nothing inside the cluster can change it |
| Cons | Needs ACNS (billed per node) and Cilium's DNS proxy - only names the pod resolved are allowed, and DNS rules must cover every search suffix (see the Cilium gotcha in aks-terraform's notes). FQDN and port only: no IDPS, threat intelligence or TLS inspection. Its denials are seen through Hubble, which the dev cells turn off (D56). Every team must write and keep a policy; a mistake shows up as a broken application. A cluster administrator can change the policies | Only as fine as the source address it sees: per zone in overlay, per pod address in node subnet - but its rules name subnets or IP groups, so it opens a destination to a whole zone, not to one application. Cost: a Firewall Premium per exposure (~1.75 USD an hour list) plus data processing per GB. One more hop, and a throughput and availability dependency for every flow. Changes go through central review, so a new dependency waits for a merge. Without TLS inspection its application rules see only the TLS server name |

**Combinations**

- **Overlay + Cilium FQDN + Firewall zone allow-list** - model (a), the design's default: each application's egress
  in Cilium, the Firewall as a second, zone-wide line of defence with its IDPS and log on what Cilium let out.
- **Node subnet + Firewall per application, Cilium inside the cluster** - model (b), az3: the Firewall decides, the
  agent proposes its rules, Cilium keeps the zone baseline inside the cluster.
- **Node subnet + Cilium FQDN + Firewall** - both lines per application: the Firewall sees each pod's address, so
  its log and the agent attribute every flow while the teams' policies still decide per application. Costs the
  address space of (b) and the policy work of (a).
- **Overlay + Firewall only, without ACNS** - the Firewall sees node addresses, so it decides per zone (a zone has
  its own node subnets), and nothing decides per application. The cheapest: no ACNS, no extra address space, no
  egress policy in the applications' repositories - proposed as the default ([D61](decisions.md#decision-matrix),
  [section 22](22-egress-control-options-and-the-company-firewall.md), which also covers a company-owned firewall).

The example application aks-hello shows (b): from 0.4.0 it fetches a weather forecast from api.open-meteo.com, which
the Firewall denies in `int-se` (from the pods' 100.64.32.x addresses) until the agent's pull request is merged.

## What Azure Policy enforces

Azure Policy cannot look up other objects ([section 14](14-policy-enforcement.md)), so it validates each policy object
on its own; together with Cilium's default deny that is enough to make FQDN policies the only way out:

| Rule (application namespaces) | Why |
|---|---|
| `CiliumNetworkPolicy` egress may use only `toEndpoints` (in-cluster), `toServices` with a `k8sService` / `k8sServiceSelector`, and `toFQDNs` with explicit `toPorts`; `toCIDR`, `toCIDRSet`, `toEntities`, `toServices` with external selectors and `toGroups` are rejected | Traffic out of the cluster can be opened only by name |
| `toFQDNs` and DNS `matchPattern`: no bare `*`, the wildcard only in the leftmost label and at least two labels below a public suffix (`*.blob.core.windows.net` is rejected, `*.example.com` only for the zone's own domain) | A wildcard must not open a whole cloud service or the Internet |
| DNS rules only for names that are also in a `toFQDNs` of the same policy, plus `*.cluster.local` | No resolving of names that cannot be reached (DNS exfiltration) |
| Kubernetes `NetworkPolicy` with egress `ipBlock` rejected | Cilium enforces `NetworkPolicy` too; it must not become a CIDR back door |
| `CiliumClusterwideNetworkPolicy`, `CiliumCIDRGroup`, `CiliumEgressGatewayPolicy` and policies in other namespaces: platform only (Kubernetes RBAC + Azure Policy) | Applications cannot widen the baseline |
| No Key Vault names (`*.vault.azure.net`, `*.vaultcore.azure.net`) in application `toFQDNs` or DNS rules | Applications get secrets only from the zone's External Secrets Operator; platform namespaces may name a vault in their own policies ([section 6](06-workload-identity-and-secrets.md#delivered-only-by-external-secrets-operator)) |
| Pod `dnsPolicy` must be `ClusterFirst` (no `None` with own `nameservers`), no `hostNetwork` | DNS must go through CoreDNS and the ACNS DNS proxy, or FQDN policies cannot work |

Platform namespaces (`<zone>-gateway`, `<zone>-secrets` with External Secrets Operator, `flux-system`, `infra-observability`) have
platform-owned egress policies built the same way – FQDNs wherever the destination has a name – and are reviewed
with the platform change. They are the only egress policies that may name a Key Vault; `<zone>-gateway` does not – the gateway gets its
certificate from External Secrets Operator. The gateway pods' egress goes to App Routing's istiod in `aks-istio-system`
(TCP 15012) and to the zone's application pods; they do not call the API server. `kube-system` and node (host network) traffic – kubelet, image pulls, AKS-required FQDNs –
are not pod traffic; they are controlled by the Firewall allow-list as before.

## Observing and troubleshooting

- **Dropped egress is visible per namespace**: ACNS container network logs (Hubble flows with verdict `DROPPED` and
  reason *policy denied*, plus DNS responses `REFUSED` by the DNS proxy) are collected from every node by Grafana
  Alloy into Grafana Cloud Logs, and the Cilium and Hubble metrics into Grafana Cloud Metrics
  ([section 19](19-observability-with-grafana-cloud.md)). Every user of the environment's stack, application teams
  included, can see the flows. The dev lab cells run without Hubble ([D56](decisions.md#decision-matrix)): there
  the drops are read on the cluster, not as flow logs.
- **In dev** the operations agent ([section 15](15-ai-driven-day-2-operations.md)) summarises drops after a
  deployment and proposes the missing FQDN as a pull request to the application – reviewed by the application team,
  plus a Firewall pull request (high tier) if the zone does not allow the name either.
- Alerts on a sudden rise of policy drops or DNS refusals in acc / prd, which usually mean a dependency the
  application did not declare or an exfiltration attempt.

Known limits of ACNS FQDN filtering and how the design handles them:

| Limit | Consequence |
|---|---|
| Kubernetes Service names are not supported in `toFQDNs` | In-cluster destinations use `toEndpoints` / `toServices`; FQDN policies are only for traffic leaving the cluster |
| Other L7 rules (HTTP, Kafka, gRPC) are not combined with FQDN policies | Not used; L7 inspection of external traffic stays on the Firewall (Premium, TLS inspection where agreed) |
| Pods with FQDN policies may degrade beyond ~1 000 DNS-proxied requests per second | Applications must reuse connections and cache DNS (normal SDK behaviour); load tests in acc include the egress path |
| Alpine (musl) images iterate search domains differently | DNS rules list the search-domain variants, generated by the platform preset; prefer glibc or distroless images |
| ACNS is a paid add-on | Part of the platform cost per cluster; the CPU saved by eBPF host routing offsets part of it |
