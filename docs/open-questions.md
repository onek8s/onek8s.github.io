# Open questions

The former list of open questions has been worked through: each item is now a recorded decision with its
justification, a verification the dev lab or acceptance performs, or a question only a human can answer. The
[decision log](decisions.md) holds all three. This page keeps only what still needs a person, so that it can be
read as the sign-off list for the [connection readiness gate](17-implementation-project-and-acceptance-testing.md#connection-readiness-gate).

## Decisions that need a human sign-off

The design has chosen a default for each and is built on it; the named role confirms or overrules it
([decision log](decisions.md#human-sign-offs-still-needed) for the defaults and the decisions behind them). H01, the
country boundary, was answered by the security team on 2026-10-14 ([D52](decisions.md#decision-matrix)).

| # | Who | What |
|---|---|---|
| H02 | Network team | The platform's prefixes in the corporate IPAM: a `/12` per environment or a `/17` per country, reserved already for the build tenant ([D02](decisions.md#decision-matrix)) |
| H03 | Security team | No WAF for the external zones at launch, or Application Gateway WAF v2 per zone and cell; ownership of the pre-approved Internet FQDN catalogue ([D04](decisions.md#decision-matrix), [D28](decisions.md#decision-matrix)) |
| H04 | Business, application owners | Availability, latency, error budget, failover and recovery targets; RPO and RTO per data store and environment; the internal recovery time ([D44](decisions.md#decision-matrix), [D07](decisions.md#decision-matrix)) |
| H05 | Platform owner | Budget for three cells in prd, the cells paid once per exposure ([D52](decisions.md#decision-matrix)), a second hub with its own Azure Firewall Premium for the external exposure ([D53](decisions.md#decision-matrix)), the DDoS Network Protection plan and prd's standby connectivity in the paired region; the prd cost estimate once measured ([D08](decisions.md#decision-matrix), [D32](decisions.md#decision-matrix), [D34](decisions.md#decision-matrix)) |
| H06 | Platform owner | The slow update speed shortened from 1 month to 3 weeks per step, a change to R12a ([D11](decisions.md#decision-matrix)) |
| H07 | Security team | Risk acceptance of Key Vault ABAC in preview; the platform vault layout with Key Vault Contributor for the cluster identities; Premium HSM-protected keys with 12-month rotation; backup subscription ownership ([D15](decisions.md#decision-matrix), [D20](decisions.md#decision-matrix), [D21](decisions.md#decision-matrix), [D36](decisions.md#decision-matrix)) |
| H08 | Platform owner | Community External Secrets Operator without commercial support ([D16](decisions.md#decision-matrix)) |
| H09 | DNS team | The registered parent domain for the zone names and ownership of the public validation zone ([D23](decisions.md#decision-matrix)) |
| H10 | Privacy, legal | Personal data in logs that every stack user sees; the Grafana Cloud region; the model provider and what may be sent to it ([D24](decisions.md#decision-matrix), [D45](decisions.md#decision-matrix)) |
| H11 | Security, landing zone owners | A separate build tenant without corporate connectivity and with Azure Policy in audit mode ([D30](decisions.md#decision-matrix)) |
| H12 | Platform owner | Gatekeeper or Azure Arc as the policy engine when the second cloud starts ([D39](decisions.md#decision-matrix)) |
| H13 | Legal, compliance | DORA and NIS2 applicability; a European provider in the exit strategy; GitHub, Grafana Cloud and the model provider under the CLOUD Act ([D43](decisions.md#decision-matrix)) |
| H14 | Security team, platform architect | API Server VNet Integration ([section 3](03-control-plane.md), and with it KMS with a private vault, [section 18](18-encryption-at-rest-and-customer-managed-keys.md)) or VNet encryption between the nodes ([section 13](13-encryption-in-transit-and-tls.md)): Azure refuses the first on an encrypted network with v4+ VM sizes. Options: Private Link API servers and KMS with a public-network vault behind its firewall; VNet integration with node-to-node encryption from Cilium (WireGuard) instead; or wait for Azure. The dev lab runs Private Link ([D58](decisions.md#decision-matrix)) |

## Assumptions still to be proven

No decision to make: the [capability matrix](decisions.md#azure-capability-and-verification-matrix) lists every
Azure feature the design relies on, what the dev lab has already proven, what phase 3 still has to show, and the
fallback if it fails. The ones not yet proven at all are V02 (NAP image pinning), V13 (`SecurityPatch` on a network
isolated cluster – whose documentation now lists only `NodeImage` and `None`), V16 (vault-tier backup with Cross Region
Restore in the chosen regions), V17 (Grafana Cloud Private Link across regions), V18 (Chaos Mesh with eBPF host
routing), V19 (Inspektor Gadget, kube-bench and Image Cleaner), V21 (VNet encryption on every allowed VM family in the
region) and V22 (a hub and Firewall per exposure – the lab runs without any Firewall).

---

[Back to contents](../README.md) · Previous: [Decisions](decisions.md) · Next: [Comparison with Wolkwacht](wolkwacht-comparison.md)
