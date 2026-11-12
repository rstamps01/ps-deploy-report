# Context pack: NET-7

Terms: `lldpad`, `EnhancedPortMapper`, `VNetMapLLDPParser`, `ifdown`, `ifup`, `lldpd`, `network_diagram_v2`, `vnetmap.py`, `vnetmap_lldp.py`, `Eth1/13/1`, `Hostname`, `Node`, `Port`, `ToolManager.TOOLS`, `VNetMapParser`

## `EnhancedPortMapper` (50 hits)
- `src/data_extractor.py` `VastDataExtractor.extract_port_mapping` L1620-1871
- `src/enhanced_port_mapper.py` `EnhancedPortMapper` L16-652
- `src/network_diagram_v2.py` `RackCentricDiagramGenerator._sort_switches_by_network` L727-771
- `src/vnetmap_parser.py` `VNetMapParser.__init__` L92-112
- `src/vnetmap_parser.py` `VNetMapParser._parse_topology_section` L158-194
- `src/vnetmap_parser.py` `VNetMapParser._parse_ib_switch_headers` L237-279
- `tests/test_enhanced_port_mapper_dnode.py` L21
- `tests/test_enhanced_port_mapper_dnode.py` `_mapper` L24-32

## `network_diagram_v2` (22 hits)
- `src/report_builder.py` `VastReportBuilder._create_logical_network_diagram` L3955-4191
- `tests/test_e2e_vnetmap_diagram.py` `TestEndToEndVnetmapDiagram.test_vnetmap_to_png` L30-126
- `tests/test_network_diagram_v2.py` L21
- `tests/test_network_diagram_v2.py` `TestLeafSpineISL._render` L326-351
- `tests/test_network_diagram_v2.py` `TestLeafSpineISL.test_spine_topology_draws_isl_and_suppresses_ipl` L353-364
- `tests/test_network_diagram_v2.py` `TestLegendSizing.test_five_item_legend_not_clipped_on_narrow_page` L414-469
- `tests/test_network_diagram_v2.py` `TestNET2BEdgeRouting.test_rack_gap_clears_left_rack_right_side_fan` L1058-1067
- `tests/test_network_diagram_v2.py` `TestNET2BEdgeRouting.test_canvas_reserves_clearance_for_right_fan` L1069-1101

## `Hostname` (20 hits)
- `frontend/templates/generate.html` L30
- `frontend/templates/health.html` L29
- `src/enhanced_port_mapper.py` `EnhancedPortMapper._add_ib_guid_aliases` L329-395
- `src/external_port_mapper.py` `ExternalPortMapper.__init__` L248-359
- `src/external_port_mapper.py` `ExternalPortMapper._resolve_neighbor_to_switch_ip` L1714-1741
- `src/report_builder.py` `VastReportBuilder._create_cnodes_network_configuration` L3333-3440
- `src/report_builder.py` `VastReportBuilder._create_dnodes_network_configuration` L3442-3549
- `src/report_builder.py` `VastReportBuilder._create_comprehensive_network_configuration` L3599-3937

## `Node` (70 hits)
- `frontend/templates/advanced_ops.html` L54
- `frontend/templates/advanced_ops.html` L58
- `frontend/templates/advanced_ops.html` L84
- `frontend/templates/advanced_ops.html` L95
- `frontend/templates/generate.html` L132
- `frontend/templates/generate.html` L136
- `frontend/templates/generate.html` L161
- `frontend/templates/generate.html` L186

## `Port` (202 hits)
- `frontend/templates/advanced_config.html` L244
- `frontend/templates/advanced_ops.html` L83
- `frontend/templates/advanced_ops.html` L84
- `frontend/templates/advanced_ops.html` L1648
- `frontend/templates/dashboard.html` L478
- `frontend/templates/dashboard.html` L535
- `frontend/templates/generate.html` L125
- `frontend/templates/generate.html` L160

## `ToolManager.TOOLS` (5 hits)
- `tests/test_tool_manager.py` `TestToolManagerInit.test_initialization` L32-35
- `tests/test_tool_manager.py` `TestToolManagerLocalOps.test_update_all_tools` L78-87
- `tests/test_tool_manager.py` `TestToolStatusSummary.test_all_fresh_no_attention` L135-142
- `tests/test_tool_manager.py` `TestToolStatusSummary.test_one_stale_triggers_attention` L144-152
- `tests/test_tool_manager.py` `TestToolStatusSummary.test_one_missing_triggers_attention` L154-161

## `VNetMapParser` (35 hits)
- `src/app.py` `_run_report_job` L2542-3064
- `src/data_extractor.py` `VastDataExtractor.extract_port_mapping` L1620-1871
- `src/enhanced_port_mapper.py` `EnhancedPortMapper.__init__` L35-86
- `src/enhanced_port_mapper.py` `EnhancedPortMapper._build_switch_map` L254-327
- `src/oneshot_runner.py` `OneShotRunner._run_report` L1728-2109
- `src/vnetmap_parser.py` `VNetMapParser` L89-426
- `src/workflows/vnetmap_workflow.py` `VnetmapWorkflow._merge_fabric_report` L1430-1440
- `src/workflows/vnetmap_workflow.py` `VnetmapWorkflow._step_save_output` L1442-1501

## Files by relevance
- `src/report_builder.py` (52 hits)
- `src/oneshot_runner.py` (25 hits)
- `src/enhanced_port_mapper.py` (24 hits)
- `src/external_port_mapper.py` (18 hits)
- `src/app.py` (18 hits)
- `src/data_extractor.py` (16 hits)
- `src/main.py` (14 hits)
- `frontend/templates/reporter.html` (11 hits)
- `frontend/templates/generate.html` (10 hits)
- `src/workflows/support_tool_workflow.py` (10 hits)

## Tests to run
`python3 -m pytest tests/data/mock_api_responses.json tests/test_api_handler.py tests/test_app.py tests/test_e2e_vnetmap_diagram.py tests/test_enhanced_port_mapper_dnode.py tests/test_enhanced_port_mapper_sr3.py tests/test_external_port_mapper.py tests/test_functional_validation.py -x --lf`

## Recent commits on these files
- be4412a 2026-11-10 fix(web): stream vperfsanity Step 4 output and keep Output Results responsive (FR-16)
- b672773 2026-10-16 fix(report): mask credentials in saved ops logs; flag empty /vast/log copies
- 39648ac 2026-10-16 fix(report): mask credentials in the bundled operation log; review follow-ups
- a09e3f1 2026-10-16 chore(release): prepare v1.6.2
- 2b167cb 2026-10-16 refactor(ui): rename the product to asbuilt-reporter in visible text
- a1ae0bc 2026-10-16 fix(report): list generic placeholder images as fallbacks in rack validation
