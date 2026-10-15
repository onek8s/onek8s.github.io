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
- **Open: VNet integration and VNet encryption exclude each other** (H14): Azure refuses API Server VNet Integration on
  an encrypted virtual network with v4 and newer VM sizes, and the cells' networks are encrypted
  ([section 13](13-encryption-in-transit-and-tls.md)); the private vault for KMS ([section 18](18-encryption-at-rest-and-customer-managed-keys.md))
  depends on VNet integration.
- **The build tenant's dev lab runs them private too** (D58), over Private Link (a classic private cluster, the
  endpoint in the cell's `snet-system`), its public FQDN resolving to the private address (no private DNS zone, since
  the cells resolve through the hub firewall's DNS proxy), reached through the hub from the management network and the
  lab firewall's VPN, which the lab's GitHub-hosted runners join.
- **No SSH to nodes** (`--ssh-access disabled` on every node pool): nodes are replaced, never logged into. Node-level
  diagnosis uses `kubectl debug node/…` or a kernel-level tracing tool, through break-glass only
  ([section 19](19-observability-with-grafana-cloud.md#security-detections-and-forensics)).

---

[Back to contents](../README.md) · Previous: [2. Network layout](02-network-layout.md) · Next: [4. Node pools](04-node-pools.md)
