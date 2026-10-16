# 22. Egress control options and the company firewall

Who decides what an application may reach outside the landing zone - Cilium inside the cluster, the hub Firewall, or
both - comes down to two independent choices, and both have a cost. This page puts the four combinations side by
side, proposes **overlay + Firewall only, without Advanced Container Networking Services (ACNS)** as the default to
keep the cost in control ([decision D61](decisions.md#decision-matrix), proposed), and explains how the platform
works with a company-wide firewall that another team owns.

[Section 16](16-advanced-networking-and-fqdn-egress.md) describes the Cilium FQDN model in detail and the two models
running in the dev lab ([D59](decisions.md#decision-matrix)); its "Pros and cons, one choice at a time" compares the
two choices one by one.

## The two choices

- **Pod addressing**: Azure CNI **overlay** (pods in a cluster-internal range; traffic leaving the cluster carries the
  node's address) or **node subnet, no overlay** (every pod has a VNet address up to the Firewall).
- **Who enforces egress**: **Cilium FQDN policies** (part of ACNS, billed per node and hour, with Hubble and eBPF host
  routing in the same suite) or the **hub Firewall** (Azure Firewall Premium per exposure, [D53](decisions.md#decision-matrix);
  labfw in the dev lab), or both.

What the Firewall can tell apart depends on the addressing:

| The Firewall sees | Overlay | Node subnet |
|---|---|---|
| A zone's application pods | The zone's **node** addresses: a zone has its own node subnet (NAP AKSNodeClass per zone), so the zone is known | The **pod's** own address, in the zone's subnet |
| Which application | No - every application of the zone shares the zone's nodes | Not from the rule (rules name subnets or IP groups), but the log names the pod, so a flow can be attributed |
| The platform's own components | The system subnet (gateways, ESO, Flux, external-dns) | The system subnet |

## The four combinations

| | **A. Overlay + Firewall only, no ACNS** (proposed default) | **B. Overlay + Cilium FQDN + Firewall** (today's design, az2) | **C. Node subnet + Firewall, Cilium in-cluster** (az3) | **D. Node subnet + Cilium FQDN + Firewall** |
|---|---|---|---|---|
| Who decides egress | The Firewall, per zone | Cilium per application; the Firewall per zone behind it | The Firewall, per zone (rules named per application) | Cilium per application; the Firewall per zone, attributing every flow |
| Application granularity | Zone | Application (pod selector) | Zone at enforcement, pod in the log | Application |
| ACNS (per node and hour) | **No** | Yes | No (yes if Hubble or eBPF host routing is wanted) | Yes |
| Address space | Small: nodes only | Small | A /16 of 100.64.0.0/10 per cell (110 addresses reserved per node) | Same as C |
| What teams write | Nothing for egress: a request (pull request) per destination, reviewed by the Firewall's owners | A Cilium FQDN policy in their repository | Nothing: the egress agent proposes, humans merge | A Cilium FQDN policy |
| Egress agent | Attributes a denial to a zone and its nodes' pods (see below) | Not needed for egress; reads Hubble if on | Attributes a denial to the pod | Attributes to the pod |
| IDPS, threat intelligence, TLS inspection | On every flow | On what Cilium let out | On every flow | On what Cilium let out |
| Visibility of a denial | Firewall log (node address) | Hubble (off in dev, D56) and the Firewall log | Firewall log (pod address) | Hubble and the Firewall log |
| Runs on | Any overlay cell | Any overlay cell | Cells with a 100.64 /16 | Same as C |
| Main weakness | Applications of one zone share the zone's destinations | ACNS cost; every team maintains policies | Address space; NSGs cannot tell pods from nodes | Cost of both |

### A. Overlay + Firewall only, without ACNS - the proposed default

Cheapest to run and simplest for application teams: no ACNS on any node, no extra address space, no egress policy in
the application repositories. The cluster runs Azure CNI powered by Cilium as everywhere else, so the in-cluster rules
stay - the zone baseline, namespace isolation, the platform namespaces' policies - written at layers 3 and 4.

What it takes:

- **The isolation zone is the egress boundary.** The Firewall rules use the zone's IP group (its node subnets in every
  cell) as the source: an allowed destination is open to every application of the zone. The per-application files
  (azure-landing-zone `firewall-applications/<env>-<exposure>/<namespace>.yaml`) still name the owner, the reason and
  the review, so a rule is removed with the application that asked for it.
- **Without ACNS, Cilium has no DNS-aware rules.** The zone baseline's DNS rules (`matchPattern` on names, which run
  through the ACNS DNS proxy) become plain port 53 to kube-dns, and the `fqdn-egress` policy
  ([section 14](14-policy-enforcement.md)) changes: applications write no egress policy, and a platform policy per
  zone lets the zone's application namespaces out of the cluster (today's `firewall-egress` component).
- **eBPF host routing and Hubble go too** (both are ACNS). Pod traffic uses the default iptables path; drops are read
  from Cilium's own counters and the Firewall log.
- **The egress agent attributes by zone and node**: a denial's source is a node address, so the agent finds the node,
  lists the application pods that ran there at the time, and checks the destination against each one's configuration
  ([section 15](15-ai-driven-day-2-operations.md)). One match: a pull request in that application's name. Several or
  none: a pull request for the zone that names the candidates, for the reviewers to settle. Today's agent ignores node
  sources (it was written for model C) - this is its first change for model A.

**When to choose something else**:

- An application that must not share its destinations with the rest of its zone - a regulated integration, a
  third-party API key that should only ever leave from one place - gets its **own zone**, or its zone runs on a cell
  with **Cilium FQDN policies** (B or D: ACNS is a per-cluster setting, so per cell).
- Where every flow must be attributed to a pod in the Firewall's own log (an audit requirement, not an enforcement
  one): **node subnet** (C or D).

The choice is per cell (`network_profile.network_plugin_mode` and `advanced_networking` in aks-terraform, both need a
rebuild to change), so a fleet can run A by default and B, C or D where a zone needs it.

## Working with a company-wide firewall

In many companies the network or security team owns the firewalls, and the platform team does not. The platform's
egress rules are then **requests to that team**, and the design keeps them in a form that team can take without
learning Kubernetes:

- Every rule is a file per application (`firewall-applications/<env>-<exposure>/<namespace>.yaml`: destination FQDNs,
  protocol, port, owner, reason) plus the source **IP groups** the platform maintains (one per zone and per cell
  system subnet, in the platform's resource group). Nothing in a rule refers to pods or namespaces.
- The egress agent's pull requests and every human change go through the same review, so the firewall team sees one
  stream of small, explained requests with their evidence (the denied flows).

How the rules reach the firewall depends on what the company runs and how much it delegates. From least to most
delegation:

### 1. Pull requests to the firewall team's repository (no delegation)

The firewall team keeps its policy as code. The platform's per-application files live in that repository, or are
copied there by a pipeline, and its CODEOWNERS make the firewall team the only approvers. The team's own pipeline
renders them into a rule collection group of its policy and applies it. The platform holds no right on the firewall.

This works with any firewall product - Azure Firewall, a third-party virtual appliance, an on-premises one - because
the files are plain data; only the renderer is product-specific. It is the slowest path: a new dependency waits for
the firewall team's review.

### 2. A child Firewall Policy for the platform, the company's policy as its parent

Azure Firewall Policies are hierarchical, and this is Microsoft's documented way to delegate
([Azure Firewall Manager: rule hierarchy](https://learn.microsoft.com/en-us/azure/firewall-manager/rule-hierarchy),
[policy overview](https://learn.microsoft.com/en-us/azure/firewall-manager/policy-overview)):

- The security team owns the **parent (base) policy**: the company-wide allow and deny rules, threat intelligence and
  the IP allowlist. A child inherits all of it: "Network rule collections inherited from the parent policy are always
  prioritized over network rule collections defined as part of a new policy", and the same for application rules.
  Threat intelligence can only be made stricter in a child, never turned off. So nothing the platform writes can
  override the company's rules.
- The platform owns the **child policy** (in its own resource group, same region as the parent) and writes its rule
  collection groups there.
- The delegation is a **custom role assigned on the child policy**, as in Microsoft's example ("AZFM Rule Collection
  Group Author"): read rights plus `Microsoft.Network/firewallPolicies/ruleCollectionGroups/write` (and `.../delete`,
  which the example leaves out). Holders of the role cannot delete the firewall or the policy, change the hierarchy,
  DNS settings or threat intelligence, or touch any other policy.
- The platform's deployment identity (the landing zone's apply identity, [section 9](09-environments.md)) gets that
  role and applies the rule files with Terraform - the same files as today. Its IP groups stay in its own resource
  group; the parent's owners need only read access to them if their rules refer to them.

The limit: **an Azure Firewall has only one assigned policy**. The child policy is the one assigned, so this pattern
needs a firewall whose policy is the platform's child - which the design already has: **a hub and an Azure Firewall
per exposure** ([D53](decisions.md#decision-matrix)). The company's security team owns the parent and the firewall
resource (association, SKU, IDPS settings); the platform team owns the child's rule collection groups. The dev lab is
built this way already: `afwp-hub-parent-<region>` (platform-wide rules) and a child per exposure that labfw enforces.

### 3. A rule collection group in the company's own policy

If the company runs **one** shared Azure Firewall for everything, its policy is the only one the firewall takes, and
the platform's rules have to be rule collection groups inside it. Azure documents the RCG author role assigned on a
whole policy, which would let the platform write every group of the company's policy, not only its own - too broad
for most security teams. Whether a role assignment scoped to a single rule collection group
(`.../firewallPolicies/<policy>/ruleCollectionGroups/<group>`) is honoured is **not documented** and is open
verification V24 ([decisions](decisions.md#azure-capability-and-verification-matrix)). Until it is verified, this case falls back to option 1.

### What the platform needs from the firewall team, in any case

- **Source addresses that stay stable**: the zones' and system subnets' prefixes come from the address plan
  ([section 8](08-cluster-types-stateless-and-stateful.md#vnets-and-address-plan)) and are published as IP groups, so
  a new cell changes an IP group, not a rule.
- **The platform's base rules** (AKS's required FQDNs, Entra ID, Azure Monitor, the GitOps sources) in the parent or a
  group of their own, reviewed once.
- **Read access to the firewall's denied flows** (its diagnostic setting into a Log Analytics workspace the platform
  can query, through the hub's Azure Monitor Private Link scope): the egress agent's only input.
- **Translation at the firewall** for everything leaving the landing zone's own ranges (SNAT private ranges), so
  100.64 addresses of node-subnet cells never leave it.

## Cost

Per stateless cell, against model B:

| | A | B | C | D |
|---|---|---|---|---|
| ACNS | none | every node, every hour | none | every node, every hour |
| Hub Firewall | shared per exposure (exists in every model, D53) | same | same | same |
| Firewall data processing | every flow leaving the cluster | only what Cilium let out | every flow | only what Cilium let out |
| Address space | nodes only | nodes only | /16 per cell | /16 per cell |
| Firewall log ingestion | denials (all flows only while learning a default-allow environment) | same | same | same |

ACNS and Azure Firewall are priced in the Azure pricing calculator (per node and hour for ACNS; per deployment hour and
per GB processed for the Firewall); the list prices are not repeated here because they change.

---

[Back to contents](../README.md) · Previous: [21. Open standards and portability](21-open-standards-and-portability.md) · Next: [Decisions](decisions.md)
