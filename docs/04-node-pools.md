# 4. Node pools

![Node pools](../images/04-node-pools.svg)

Every isolation zone has its own nodes in that zone's subnets, labelled `platform/zone=<zone>` and tainted
`platform/zone=<zone>:NoSchedule`. How the nodes are created differs per cluster type, because the two cluster types
run different kinds of workloads:

| | Stateless clusters | Stateful cluster |
|---|---|---|
| Zone nodes | [Node auto provisioning](https://learn.microsoft.com/en-us/azure/aks/node-autoprovision) (NAP, AKS-managed Karpenter): two Karpenter `NodePool`s per zone – on-demand (`intfi`, `extfi`, …) and spot (`intfispot`, `extfispot`, …) – sharing one `AKSNodeClass`; no classic node pools for workloads | Classic AKS node pools (VM scale sets), one per zone *and* AZ (`intfiz1`, `intfiz2`, `intfiz3`, …) |
| Subnet | `AKSNodeClass` `vnetSubnetID` = the zone's `snet-<zone>-nodes` | `--vnet-subnet-id` `snet-<zone>-nodes`, `--pod-subnet-id` `snet-<zone>-pods` |
| Availability zone | `NodePool` requirement `topology.kubernetes.io/zone In [<region>-<N>]` – the cell's AZ | `--zones 1` / `2` / `3`, one pool per AZ |
| VM sizes | Chosen by NAP for the pending pods from an allow-list of several VNet-encryption-capable SKU families in the `NodePool` requirements, **amd64 and arm64** | One fixed size per pool, chosen when the workload's exception is onboarded; amd64 |
| Capacity type | On-demand and **spot**, chosen per application ([below](#cpu-architecture-and-spot-chosen-by-the-application)) | On-demand only |
| Scaling | Nodes are created for pending pods and removed or consolidated when they are empty or under-used, **down to zero**: a zone without application pods has no nodes, because the zone's gateway and ESO run on the system pool ([below](#zone-nodes-only-for-applications)); the `NodePool` `limits` (CPU, memory) are the upper bound, sized for N+1 | **No autoscaling.** Fixed node count per pool, set in IaC; capacity changes are planned changes |
| Node replacement | Drift (new node image or Kubernetes version), consolidation and `expireAfter`, limited by the `NodePool` disruption budgets; PDBs are respected | Surge upgrade per pool, one AZ at a time ([section 12](12-zero-downtime-cluster-upgrades.md#stateful-cluster)) |
| Defined by | Flux, in `infrastructure/stateless` (subnet IDs and AZ from the `cluster-vars` ConfigMap), applied before anything that runs on zone nodes | Cluster IaC |
| Disk encryption | Cluster's disk encryption set (`key-<cluster>-disk`) on the ephemeral OS disks; `security.encryptionAtHost: true` in every `AKSNodeClass` | Cluster's disk encryption set on the OS disks, `--enable-encryption-at-host`; persistent volumes with the zone's own key ([section 18](18-encryption-at-rest-and-customer-managed-keys.md)) |
| System pool | Classic node pool `system`, fixed node count, pinned to the cell's AZ | Classic node pool `system`, fixed node count, spread over AZ 1–3 |

**Why two models.** Stateless workloads scale on load all day and can be moved at any time, so NAP fits them: it
picks the VM size from what the pending pods need, packs them tightly and gives unused nodes back, and the platform
does not maintain a node pool per zone × VM size or plan the capacity of a freshly built cell. The stateful cluster
runs a few approved StatefulSets and operators that are sized when they are onboarded and do not scale on load;
every node change moves a replica and re-attaches its disks. Fixed-size node pools keep its capacity predictable,
and its nodes change only in planned upgrades – never because an autoscaler decided to consolidate.

### Zone nodes only for applications

In the stateless clusters a zone's nodes exist only while the zone has application pods. The zone's platform
components – its gateway (`<zone>-gateway`, [section 13](13-encryption-in-transit-and-tls.md)) and its External
Secrets Operator (`<zone>-secrets`, [section 6](06-workload-identity-and-secrets.md)) – run on the system pool next to
the platform's own controllers, so they never hold a zone node. A zone that no application uses yet, or no longer,
costs no VMs: NAP creates the first node when an application pod of the zone is pending and consolidates the last
one away when it is empty. The zone's separation does not depend on where these two components run: the gateway's
load balancer is still the zone's own, in the zone's subnet, its routes are still limited to the zone's namespaces,
the ESO still reaches only the zone's vault, and Cilium policies still separate both from every other zone. What the
system pool loses is node-level separation between the zones' gateways, which share the platform's nodes; it is
sized for them (at least two Envoy replicas per zone and cell, the minimum of App Routing's HPA). The gateways also
share one control plane per cell, App Routing's istiod ([section 13](13-encryption-in-transit-and-tls.md)): the data
plane is per zone, the control plane is not.

NAP details in the stateless clusters:

- NAP is enabled with `--node-provisioning-mode Auto`; the AKS-created default `NodePool`s are disabled
  (`--node-provisioning-default-pools None`), so every NAP node belongs to a zone's `NodePool`. NAP requires Azure CNI
  Overlay powered by Cilium, which the stateless clusters use anyway. The cluster autoscaler is not used anywhere.
- All nodes run **Azure Linux 3.0** (`AKSNodeClass` `imageFamily: AzureLinux`, system pool `--os-sku AzureLinux`),
  which eBPF host routing requires on every node of the cluster ([section 16](16-advanced-networking-and-fqdn-egress.md)).
- Several SKU families in each allow-list lower the risk that the cell's single AZ runs out of capacity for one VM size
  when a cell is pre-scaled to carry the full load ([section 12](12-zero-downtime-cluster-upgrades.md#stateless-clusters)).
- Disruption budgets keep consolidation slow (e.g. at most 10 % of a zone's nodes at a time) and block it while a cell
  is being changed; all applications have ≥ 2 replicas and a PDB, so consolidation never takes an application down.
- Only the platform manages `NodePool` and `AKSNodeClass` objects (Kubernetes RBAC), and Azure Policy rejects any whose
  subnet, label, taint or VM sizes do not match its zone ([section 14](14-policy-enforcement.md)).

## CPU architecture and spot, chosen by the application

To lower cost, the stateless clusters offer **amd64 and arm64** nodes and **on-demand and spot** nodes in every
zone. The platform supports all four combinations; the team that builds an application decides what the application
supports and declares it with two labels in the pod template. Without labels an application gets the safe default,
amd64 on on-demand nodes, so nothing changes for applications that do not opt in.

| Pod label | Values | Effect (injected by Azure Policy mutation) |
|---|---|---|
| `platform/arch` | `amd64` (default) | `nodeSelector` `kubernetes.io/arch: amd64` |
| | `arm64` | `nodeSelector` `kubernetes.io/arch: arm64` |
| | `multi` | no architecture constraint: NAP picks the cheapest fitting VM size of either architecture (usually arm64) and the scheduler may use any free node |
| `platform/capacity` | `on-demand` (default) | nothing – the pod cannot tolerate the spot taint, so it runs only on on-demand nodes |
| | `spot` | toleration `platform/capacity=spot:NoSchedule` and a *preferred* node affinity for `karpenter.sh/capacity-type: spot`: the pod runs on spot nodes when there are any, and on on-demand nodes when spot capacity is not available |

How the platform handles them:

- **Two `NodePool`s per zone**, both allowing `kubernetes.io/arch In [amd64, arm64]`:
  - `<zone>` – `karpenter.sh/capacity-type In [on-demand]`, no extra taint;
  - `<zone>spot` – `karpenter.sh/capacity-type In [spot]`, taint `platform/capacity=spot:NoSchedule`, and a higher
    `weight`, so NAP tries spot first for pods that tolerate it and falls back to the on-demand `NodePool` when Azure
    has no spot capacity for the allowed SKUs in the cell's AZ.

  Both share the zone's `AKSNodeClass` (subnet, image), label and zone taint; the spot taint is what keeps every
  application that did not choose spot away from spot nodes, also from spot nodes that already exist and have room.
- **Allow-lists per architecture**: the SKU allow-list holds amd64 families (e.g. Dsv5/Dsv6, Esv5/Esv6) and arm64
  families (e.g. Dpsv6/Epsv6, Cobalt 100) – only those that support VNet encryption, because it is the only encryption
  between nodes ([section 13](13-encryption-in-transit-and-tls.md)), and encryption at host, which every node has
  ([section 18](18-encryption-at-rest-and-customer-managed-keys.md)). The spot `NodePool` uses the same allow-list:
  several families per architecture also give spot more places to find capacity.
- **Capacity and N+1**: the on-demand `NodePool` limits alone are sized for N+1 (one cell carrying the whole
  environment), because spot capacity can disappear exactly when a cell is pre-scaled. The spot `NodePool` limits cap
  how much of a zone can run on spot.
- **Spot evictions** come with about 30 seconds' notice and do **not** respect PDBs; Azure can evict many spot nodes
  at once. NAP replaces evicted capacity – with spot if it is available, otherwise on-demand. An application may
  choose `spot` only if it tolerates losing replicas suddenly: graceful shutdown within 30 seconds, no long-running
  requests that cannot be retried, and work that is safe to repeat (queue consumers, batch jobs, stateless APIs with
  enough replicas). Latency-critical entry points and singletons-by-design stay on-demand.
- **Images**: `arm64` needs an arm64 image, `multi` a multi-architecture image (OCI image index with `linux/amd64`
  and `linux/arm64`). Admission cannot inspect images, so the build pipeline checks the platforms of the image index
  in ACR against the labels in the rendered manifests before an image is promoted, and the application's tests run on
  every architecture it declares. All platform DaemonSets (Cilium, CSI drivers, monitoring agent) are
  multi-architecture.
- **Validation**: applications set only the labels; Azure Policy rejects unknown label values, pods that set
  `kubernetes.io/arch` or `karpenter.sh/capacity-type` in their own `nodeSelector` / affinity, and pods that tolerate
  `platform/capacity` without the `spot` label ([section 14](14-policy-enforcement.md)).
- **System pool and stateful cluster**: the system pool stays amd64 on-demand. The stateful cluster runs only
  on-demand nodes – a spot eviction would move a replica and re-attach its disks without a PDB – and only amd64 pools;
  in the stateful cluster any label value other than the defaults is rejected. An arm64 pool set (one per zone and
  AZ) can be added when an onboarded workload needs it.

Choosing is a trade-off the application team owns: `multi` + `spot` is the cheapest, `amd64` + `on-demand` the most
predictable. The choice can be changed in any release, because it is only a label in the pod template.

## Pod right-sizing: vertical scaling in place

NAP picks VM sizes, packs nodes and sizes the N+1 headroom from the pods' **requests**, so requests that are far from
real use cost money (too high) or reliability (too low: OOM kills, CPU throttling). Since Kubernetes 1.35 a running
container's CPU and memory can be changed **in place** (GA), and since 1.36 the same works for the pod-level budget
`spec.resources` ([in-place pod-level resources, beta, on by default](https://kubernetes.io/blog/2026/04/30/kubernetes-v1-36-inplace-pod-level-resources-beta/)).
Changing the size of a running pod no longer needs a new pod, and usually not even a container restart. The
platform uses it in two loops:

| Loop | Who | How fast | Writes |
|---|---|---|---|
| **Online**: resize running pods to their usage | [Vertical Pod Autoscaler](https://learn.microsoft.com/en-us/azure/aks/vertical-pod-autoscaler) (AKS add-on) in mode `InPlaceOrRecreate` – deterministic, in the cluster | Minutes | The pods' `resize` subresource only, within the bounds of the application's `VerticalPodAutoscaler` |
| **Policy**: which applications may be resized, the bounds, and the requests new pods start from | **Right-sizing agent** ([section 15](15-ai-driven-day-2-operations.md#agents)) | Daily, and on OOMKill / throttling / stuck-resize alerts | Pull requests to the fleet repository, tiered by the merge gate |

The agent never resizes a pod itself: an agent with write access to pods would break *Git is the only write path*,
and a language model does not belong in a loop that must react in minutes. It is the same split as HPA / KEDA
(controllers scale replicas online inside bounds that are in Git) and NAP (creates nodes inside `NodePool` limits
that are in Git).

**How it is set up – on by default**

- Every cluster starts on Kubernetes **1.36** ([update policy](12-zero-downtime-cluster-upgrades.md#update-policy)), so
  container-level (GA) and pod-level (beta) in-place resize are available in every cell from day one. The VPA add-on
  (`--enable-vpa`) is enabled by the cluster IaC in every cluster; all nodes are Azure Linux 3.0, which has the
  cgroup v2 and containerd 2.0 that in-place resize needs.
- **Every stateless Deployment is right-sized by default.** The onboarding agent creates a `VerticalPodAutoscaler` in
  the application's overlay (`apps/<app>/stateless/<env>/vpa.yaml`) with `updateMode: InPlaceOrRecreate` from the first
  deploy, and safe starting bounds taken from the requests the team declared: memory `minAllowed` = the declared
  request (nothing shrinks before there is usage data), CPU `minAllowed` = a quarter of it, `maxAllowed` = twice the
  declared values. The right-sizing agent widens the bounds once it has 14 days of usage. The requests new pods start
  from are a patch next to it (`resources.yaml`). Both files are platform-maintained; the application's own manifests
  stay the team's. CI checks on the rendered manifests that every Deployment has its VPA (like the PDB check).
- **Opt-out**: an application team that does not want its pods resized sets the pod label
  `platform/rightsizing: off`. Its VPA then stays in `updateMode: "Off"` – recommendations only, which the
  right-sizing agent still uses to move the baseline in Git by pull request. The right-sizing agent also falls back to
  `Off` by itself for an application whose resizes misbehave (oscillation, restarts), and says so in an issue.
- **Bounds**: `controlledValues: RequestsOnly` and a `maxAllowed` for every resource it controls; the merge gate
  checks modes and bounds against `rightSizing` in `limits.yaml` (inside = tier low, over the soft limit = medium,
  over the hard limit = rejected). A pull request that changes only requests / limits of a workload is low when each
  value moves at most ×2.
- **Only requests move, limits stay in Git.** A runtime that sizes its heap from the memory limit at start (JVM
  `MaxRAMPercentage`, .NET, Node) is therefore not affected by a resize, and memory `maxAllowed` must not exceed the
  container's memory limit. Containers use `resizePolicy` `NotRequired` for CPU and memory, so a resize never
  restarts them.
- **HPA / KEDA**: an HPA on CPU utilisation computes against the CPU request, so a VPA moving CPU would fight it. The
  VPA then controls only memory (HPA on memory: only CPU; KEDA on queue length or request rate: both). An application
  whose HPA scales on both stays `Off`: only its baseline in Git moves.
- **Stateful cluster**: VPA objects only in `Off` – requests = limits for memory and fixed node pools make every size
  change a planned change through the pipeline. Right-sizing by default applies to the stateless clusters.

**What keeps it safe**

- The kubelet admits a resize only if it fits the node; otherwise the pod gets the condition `PodResizePending`
  (`Deferred` – may fit later, `Infeasible` – never fits). NAP does **not** add nodes for a deferred resize; the VPA
  updater then falls back to evicting the pod (PDB respected), and the recreated, pending pod is what makes NAP add a
  node. `maxAllowed` must therefore fit the largest allowed VM size, and many deferred resizes in a zone are a
  capacity signal for the capacity agent.
- Resizes are admitted against the namespace `ResourceQuota`: `maxAllowed` × `maxReplicas` must fit it. The design
  does not count on Azure Policy (Gatekeeper) seeing the `pods/resize` subresource ([open question](open-questions.md)),
  so `maxAllowed`, quota and node allocatable are the bounds of an in-place resize, not the admission policies of
  [section 14](14-policy-enforcement.md).
- An in-place resize changes the pod, not the Deployment: Flux sees no drift. New pods start from the requests the
  VPA's admission webhook sets, or – if the webhook is down – from Git; the right-sizing agent keeps Git close to the
  VPA's target so a rebuilt cell or a drain does not start from stale numbers.
- On increase the kubelet grows the pod cgroup before the containers', on decrease it shrinks the containers first,
  so a pod never overshoots its budget during a resize.

**Pod-level resources** (`spec.resources`) suit pods with several containers – the application and a sidecar share
one budget, and containers without their own limits use what the others leave. On 1.36 the budget can be resized in
place in every cell, but the VPA cannot recommend or actuate pod-level values yet (planned upstream for GA). Until
then a pod-level budget is a value in `resources.yaml`, proposed by the right-sizing agent with the application team's
agreement, and the VPA does not move the same resources of those containers.

## Zone pinning

Application namespaces are named `<zone>-<app>` and carry the matching `platform/zone` label. The Azure Policy
add-on injects the zone's `nodeSelector` and toleration into every pod (one mutation definition per zone, matched by
the namespace prefix `<zone>-*`) and **rejects** pods that try to select or tolerate another zone. The checks use
the namespace *name*, not a lookup of the namespace's labels, because custom Azure Policy definitions cannot use
Gatekeeper data replication; a separate policy makes sure the label of a namespace matches its name prefix. Only platform
DaemonSets (Cilium, CSI drivers, monitoring) run on all nodes.

Note: the kubelet identity is cluster-wide in AKS, so it is **never** granted access to Key Vaults – workloads
use workload identity only (picture 6).

---

[Back to contents](../README.md) · Previous: [3. Control plane](03-control-plane.md) · Next: [5. Allowed and blocked flows](05-allowed-and-blocked-flows.md)
