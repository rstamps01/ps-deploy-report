# SR-3: vnetmap_parser stores IB switch GUIDs as `switch_ip` → port-mapper logs "Unknown switch IP"

**Status:** Resolved — fixed by `vnetmap_parser._parse_ib_switch_headers` + `EnhancedPortMapper._add_ib_guid_aliases` (this branch). 
**Severity:** Medium — does not block report generation, but on InfiniBand clusters every Port Mapping row renders as `SW?-<port>` with no SWA/SWB designation, IPL connections detect 0 ports, and the operator log spams `Unknown switch IP: 0x...` warnings (one per topology row × number of switches). 
**Discovered:** 2026-04-30 in mammoth IB cluster log review (`import/CZ-Bio/`); reproduced in saved fixtures `output/scripts/vnetmap_output_192.168.2.2_*.txt`. 
**Related:** TP-1 (`7b94453`), TP-2 (`f49aa2b`), SR-1 (`8bba3aa`) — all are Tech-Port / IB cluster pipeline fixes; SR-3 is the rendering-layer half of the IB story. 
**Out of scope for:** SR-1 (vnetmap workflow tunnel routing), SR-4 (cluster type heuristic), SR-5 (PDF MAC column wrap).

---

## Symptom

In an end-to-end IB cluster run (mammoth, via Tech-Port `192.168.2.2`):

```
[INFO] enhanced_port_mapper: Built switch map: 2 leaf, 0 spine
[WARNING] enhanced_port_mapper: Unknown switch IP: 0xb83fd20300e856b8
[WARNING] enhanced_port_mapper: Unknown switch IP: 0xb83fd20300e85d18
[WARNING] enhanced_port_mapper: Unknown switch IP: 0xb83fd20300e856b8
[WARNING] enhanced_port_mapper: Unknown switch IP: 0xb83fd20300e85d18
... (40+ warnings, one per topology row) ...
[INFO] data_extractor: Inferred IPL connections using 0 ports between switches
```

Cascading effect:

1. Every Port Mapping table cell in the PDF renders as `SW?-19`, `SW?-25`, etc. instead of `SWA-P19`, `SWB-P19`. The Switch column loses all designation context.
2. IPL inference relies on resolving `switch_ip` to `mgmt_ip` to count IPL ports between leaves. With every IB row falling through to the `Unknown switch IP` branch, the inference returns 0 ports.
3. Operator log noise (40+ identical warnings per report) drowns out genuine signal.

## Root cause

`src/vnetmap_parser.py::_parse_topology_section`, line 99 (pre-fix):

```python
connection = {
    "hostname": parts[0],
    "node_hostname": parts[0],
    "switch_ip": parts[1],   # <-- on IB clusters, parts[1] is a 16-byte GUID like 0xb83fd20300e856b8
    "port": parts[2],
    ...
}
```

On Ethernet clusters `parts[1]` is the switch's mgmt IP (e.g. `10.128.101.141`); on InfiniBand clusters `vnetmap` writes the IB switch's **port GUID** (16 hex bytes prefixed with `0x`) into the same column because IB switches don't have IP addresses on the fabric. Downstream, `EnhancedPortMapper._build_switch_map` keys on the API-supplied `mgmt_ip` (the operator-visible 10.247.x.x address from `/api/switches/`), so GUIDs never resolve.

The IB cluster identity is recoverable from the `Switch MF0;<hostname>:<model> - <0xGUID> has {<subnet>}, ...` per-switch anchor lines that `vnetmap` emits in the post-topology diagnostic section, but the parser was discarding them.

## Fix design (this branch)

**Additive — no API breakage, no Eth regression.**

1. **`src/vnetmap_parser.py`:** 
   - New `_parse_ib_switch_headers()` extracts each `Switch MF0;<hostname>:<model> - <guid> has {<subnet>}, ...` line into `{"hostname", "model", "guid", "internal_subnet"}` records. 
   - De-duplicates by GUID (vnetmap emits each anchor twice — once before each per-switch detail block). 
   - Result exposed in the `parse()` return dict under the new `ib_switch_headers` key. Empty list on Eth output.
   - Existing `topology` rows continue to carry the GUID verbatim in `switch_ip`, preserving backward compat with cross-connection / LLDP / IPL-inference logic that already groups by that field.

2. **`src/enhanced_port_mapper.py`:** 
   - New `ib_switch_headers: Optional[List[Dict[str, str]]]` constructor kwarg (defaults to `None`). 
   - New `_add_ib_guid_aliases()` runs after the canonical `_build_switch_map` if any headers are supplied. 
   - Builds a `hostname → mgmt_ip` map from `self.switches` (tries `name`, `hostname`, `host_name` in order; case-insensitive). 
   - For each header: looks up the matching mgmt_ip, then aliases the GUID into `switch_map[guid] = switch_map[mgmt_ip]` (same dict reference). 
   - GUIDs without a hostname match still flow through to the `Unknown switch IP` branch — graceful, not silently fabricating.

3. **`src/data_extractor.py`:** 
   - Path 1 (vnetmap workflow) and Path 3 (static vnetmap fallback) now pass `ib_switch_headers=vnetmap_result.get("ib_switch_headers", []) or []` into the `EnhancedPortMapper` constructor. Path 2 (External SSH) is unaffected — no IB GUIDs involved.

## Acceptance criteria

1. End-to-end on mammoth `vnetmap_output_192.168.2.2_*.txt` fixture: 
   - 0 `Unknown switch IP` warnings (was 40+). 
   - 0 designations starting with `SW?` (was all 40 rows). 
   - `0xb83fd20300e856b8 → SWA-P19`, `0xb83fd20300e85d18 → SWB-P19`. 
   - `get_switch_hostname(GUID)` returns the API hostname (e.g. `vast-switch1-bot`), not the GUID.
2. Eth cluster (`vnetmap_output_10.143.11.202_*.txt`): 0 `ib_switch_headers`, all `switch_ip` values remain mgmt IPs, no behavioural change. 
3. Unit tests cover: parser header extraction (4 cases), GUID alias resolution (7 cases), Eth no-op (1 case), graceful fallback for unmatched GUIDs (1 case), alternate hostname API field (1 case). 
4. No new mypy errors (13 baseline `Any | None` errors confirmed pre-existing).

## Verification

* `tests/test_vnetmap_pipeline.py::TestSR3IBSwitchHeaders` (5 cases) 
* `tests/test_enhanced_port_mapper_sr3.py::TestSR3GuidAliasing` (7 cases) 
* End-to-end smoke against real mammoth fixture printed: 
 ```
 Parsed 40 topology rows, 2 IB switch headers
 switch_map keys: ['0xb83fd20300e856b8', '0xb83fd20300e85d18', '10.247.2.135', '10.247.2.137']
 Designations starting with SW? (degraded): 0
 "Unknown switch IP" warnings: 0
 SWA → vast-switch1-bot, SWB → vast-switch2-top
 ```
* selab-var-202 Eth fixture round-trip: 0 IB headers, 2 mgmt-IP keys, behaviour identical to pre-fix. 
* 397/397 tests pass across SR-3 blast radius (vnetmap_pipeline + enhanced_port_mapper_sr3 + external_port_mapper + port_mapper + e2e_vnetmap_diagram + vnetmap_status + data_extractor + report_builder + main_from_json + main + workflows).

## Evidence

* `output/scripts/vnetmap_output_192.168.2.2_20260501_153832.txt` — mammoth IB fixture, 40 topology rows, 2 distinct switches (`vast-switch1-bot` / `vast-switch2-top`). 
* `output/scripts/vnetmap_output_10.143.11.202_20260421_050703.txt` — selab-var-202 Eth fixture, 8 topology rows, 0 IB anchor lines. 
* Mammoth fixture preserved as the durable IB regression baseline (live cluster access lost 2026-05-15).
