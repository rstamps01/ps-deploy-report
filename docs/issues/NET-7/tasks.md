# NET-7 tasks

- [x] N1 `VNetMapLLDPParser` + ACME fixtures (Onyx and Cumulus) + parser tests (worker A)
- [x] N2 Network side from data subnet in the parser; tests (worker A)
- [x] N3 Mapper and diagram accept name-keyed switches; no inferred ISL/IPL when `isl_discovered` is False; legend note; e2e PNG test (worker B)
- [x] N4 `vnetmap_lldp.py` in `ToolManager.TOOLS`; tool manager tests (worker C)
- [x] N5 `VnetmapLLDPWorkflow` (deploy, read-only readiness, show-mapping with `switch_mapping.json` preserve, validate, save) + guardrail test written first (worker C)
- [x] N6 `select_topology_source()` + `switch_auth_failed_all` flag in `VnetmapWorkflow` step 4; truth-table tests (worker C)
- [ ] N7 `extract_port_mapping` LLDP branch: switch name to `mgmt_ip`, synthetic unregistered switches, `data_source = "lldp"` (parent)
- [ ] N8 Reporter job and One-Shot wiring; output discovery for both filename patterns; bundler and Results scanner (parent)
- [ ] N9 Report source line and unregistered-switch note (parent)
- [ ] N10 UI source select (Reporter, Test Suite), config template keys, README (parent)
- [ ] N11 Independent review, targeted tests, changelog fragment, `quality-gate`, PR to `develop`
- [ ] N12 Lab run on a cluster with LLDP already active on the nodes (owner); sanitized output added to fixtures
