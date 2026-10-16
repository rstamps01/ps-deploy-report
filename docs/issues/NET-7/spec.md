# NET-7 — vnetmap fallback to vnetmap_lldp (customer-managed switches)

**Status:** Planned (future enhancement, documentation only; target v1.7.x). Assessed 2026-10-16.

## Problem

The port map and the logical network diagram come from `vnetmap.py`, which logs in to every switch. When the customer manages the switches and does not give us switch credentials, vnetmap cannot run, so the report has no port map or network diagram.

`vnetmap_lldp.py` (VAST Support, `support/vnetperf/`) builds the same node-to-switch map from LLDP neighbour data on the nodes, with no switch login. References:

- Confluence: [How to run vnetmap_lldp](https://vastdata.atlassian.net/wiki/spaces/CS/pages/7347404806/How+to+run+vnetmap_lldp)
- Confluence: [Use LLDP as an alternative to vnetmap](https://vastdata.atlassian.net/wiki/spaces/CS/pages/5491851319/Use+LLDP+as+an+alternative+to+vnetmap+to+scan+for+switch+connectivity)

## Hard guardrails

1. **Never change `lldpad` or `lldpd`.** The workflow must not disable, stop, install, enable or start either service. The Confluence procedure does those steps by hand; they change node configuration and need the customer's agreement, so they are never automated.
2. Readiness is checked read-only: `systemctl is-active lldpd` / `lldpad` on each node, plus the tool's own `LLDP service status: X active, Y inactive` line. If lldpd is not running on the nodes, the step stops and tells the operator to arrange it with the customer.
3. Only `--operation show-mapping` (and `dry-run`) may run. `ifdown` and `ifup` take node interfaces down and are never offered.
4. Field output names customer clusters and switches. It is never committed; fixtures use ACME and documentation-range placeholders (GOV-1).

## What vnetmap_lldp produces

`python3 /vast/data/vnetmap_lldp.py --operation show-mapping` prints per-switch tables and a final table:

```
LLDP Connection Mapping:
| Hostname | Node        | Port     | IPs         | Switch    | Switch Port |
| node-cn1 | 192.0.2.10  | enp7s0f0 | 198.51.100.10 | ACME-SW-01 | swp1s0    |
| node-cn1 | 192.0.2.10  | enp7s0f1 | 203.0.113.10  | ACME-SW-02 | swp1s0    |
```

One row per node data port (two per node on a two-switch fabric). Switch ports keep their native names (Cumulus `swp1s0` breakouts, Onyx `Eth1/13/1`).

## Gap analysis against the vnetmap topology rows

`VNetMapParser` emits rows with `hostname, switch_ip, port, node_ip, interface, mac, network`, consumed by `data_extractor.extract_port_mapping` → `EnhancedPortMapper` → `network_diagram_v2`.

| Field | vnetmap_lldp | Plan |
| --- | --- | --- |
| hostname, node_ip, interface, port | Present (`Hostname`, `Node`, `Port`, `Switch Port`) | Map directly |
| switch identity | Switch **name** only | Use the VMS switches API (name → management IP) when the switch is registered; otherwise key switches by name. `EnhancedPortMapper` and `network_diagram_v2` must accept a name-only key. |
| network A/B | Not given | Derive from the data-IP subnet (the NET-3/NET-4 rule: each switch serves one /24-equivalent group); the -01/-02 switch-name suffix is only a hint |
| mac | Not given | Optional in the diagram; leave blank |
| IPL/MLAG and spine uplinks | Not given (LLDP from nodes only sees the leaf) | Inter-switch links are absent; the diagram marks them "not discovered" rather than drawing none silently |
| Rack | Not given | Unchanged: from VMS rack data / manual placements |

**Conclusion:** no second diagram path is needed. A new `VNetMapLLDPParser` that emits the existing topology-row contract (switch key = management IP when known, else name) lets the current mapper and diagram render the port map. The mapper needs one change: tolerate a missing switch IP.

### Supplemental LLDP scripts (Confluence page 5491851319)

The `tcpdump` one-liners and `nw_check.sh` read the switches' own LLDP frames passively on each node. They add what vnetmap_lldp lacks — switch management IP (Management Address TLV), node MAC, fabric A/B and switch OS/model — **without** needing lldpd on the nodes. They are optional enrichment, not a requirement. Their only intrusion is a short `sudo tcpdump` capture on each node's data interface; that is read-only but must be listed in the step description so the operator can decline it.

## Scope when implemented

1. **Update Tools:** add `vnetmap_lldp.py` to `ToolManager.TOOLS` (`src/tool_manager.py`) with URL `https://vastdatasupport.blob.core.windows.net/support-tools/main/support/vnetperf/vnetmap_lldp.py`, so it appears in the Update Tools list and is cached/deployed like `vnetmap.py`. On the cluster it runs from `/vast/data/vnetmap_lldp.py`.
2. **Fallback selection:** in the vnetmap workflow, when no switch credentials are provided (or switch auth fails for every switch), offer the LLDP path instead of failing; never switch automatically when credentials work.
3. **Readiness check (read-only)** as in Guardrails 2.
4. **Parser:** `VNetMapLLDPParser` for the final "LLDP Connection Mapping" table (tolerant of per-switch tables and progress lines), with tests on a scrubbed fixture.
5. **Mapper/diagram:** name-only switch keys; subnet-derived network side; "inter-switch links not discovered" note.
6. **Report text:** the port-map section states the source ("LLDP from nodes — switch credentials not provided").

## Acceptance (for the future implementation)

- With no switch credentials, the workflow produces a port map and diagram from vnetmap_lldp output.
- No command that touches `lldpad`/`lldpd` state, and no `ifdown`/`ifup`, appears anywhere in the code path (enforced by a test that scans the workflow's command strings).
- Field output never lands in git; fixtures are scrubbed.
