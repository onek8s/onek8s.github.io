# 3. Control plane

![Control plane](../images/03-control-plane.svg)

The API server uses **API Server VNet Integration**: it is projected as an internal load balancer into a
dedicated, delegated `snet-apiserver` (/28) that contains nothing else. The cluster is **private** (public
endpoint disabled). Admins (Entra ID + PIM, Azure RBAC for Kubernetes) and CI/CD reach it only through a
Private Endpoint / Private Link Service in the management VNet. Nodes talk to the ILB IP directly (no tunnel,
no DNS). The system node pool (tainted `CriticalAddonsOnly`, fixed node count) runs only platform components.

- **No local accounts** (`--disable-local-accounts`): the certificate-based `clusterAdmin` credential would be a
  back door around Entra ID, PIM and the audit log. Every human, pipeline and agent signs in with Entra ID;
  break-glass is a PIM-activated Entra group, not a local credential. Azure Policy denies clusters with local
  accounts enabled.
- **The build tenant's dev lab is the one exception** ([section 17](17-implementation-project-and-acceptance-testing.md)):
  it has no network path into the cells, so its API servers keep a public endpoint, still with Entra ID and Azure RBAC
  on every call and local accounts disabled. The corporate tenant, and acceptance testing, run them private.
- **No SSH to nodes** (`--ssh-access disabled` on every node pool): nodes are replaced, never logged into. Node-level
  diagnosis uses `kubectl debug node/…` or a kernel-level tracing tool, through break-glass only
  ([section 19](19-observability-with-grafana-cloud.md#security-detections-and-forensics)).

---

[Back to contents](../README.md) · Previous: [2. Network layout](02-network-layout.md) · Next: [4. Node pools](04-node-pools.md)
