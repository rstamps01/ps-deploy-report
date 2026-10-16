"""ClusterShell group resolution (NET-6, EBox field report).

EBox clusters write ``/etc/clustershell/groups.d/local.cfg`` with the same
group key repeated across sections (``cnodesub0`` and ``dnodesubN`` appear
several times).  ClusterShell's default ``local`` source resolves a group with
``sed -n 's/^$GROUP:\\(.*\\)/\\1/p'``, so every matching line contributes to the
group (union).  Both workflow parsers kept only the last definition, so Network
Extraction and vnetmap missed CNode 172.16.128.2 on a 12-EBox cluster.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.clustershell_groups import (  # noqa: E402
    expand_nodeset,
    fold_nodeset,
    parse_group_file,
    resolve_group,
)
from workflows.network_config_workflow import NetworkConfigWorkflow  # noqa: E402
from workflows.vnetmap_workflow import VnetmapWorkflow  # noqa: E402

EBOX_LOCAL_CFG = """cnodesub0: 172.16.128.[1-12]

cnodesub0: 172.16.128.[1-3]
cnodesub1: 172.16.128.[8-10]

cnodesub0: 172.16.128.[4-7]
cnodesub1: 172.16.128.[11-12]

dnodesub0: 172.16.128.[1-1]
dnodesub1: 172.16.128.[1-2]
dnodesub2: 172.16.128.[2-3]
dnodesub3: 172.16.128.[3-4]
dnodesub4: 172.16.128.[4-5]
dnodesub5: 172.16.128.[5-6]
dnodesub6: 172.16.128.[6-7]
dnodesub7: 172.16.128.[7-8]
dnodesub8: 172.16.128.[8-9]
dnodesub9: 172.16.128.[9-10]
dnodesub10: 172.16.128.[10-11]
dnodesub11: 172.16.128.[11-12]
dnodesub12: 172.16.128.[12-12]

dnodesub0: 172.16.128.[1-2]
dnodesub1: 172.16.128.[2-3]
dnodesub2: 172.16.128.[5-5]
dnodesub3: 172.16.128.[5-5]
dnodesub4: 172.16.128.[7-9]
dnodesub5: 172.16.128.[11-12]
dnodesub6: 172.16.128.[12-12]

dnodesub0: 172.16.128.[1-1]
dnodesub1: 172.16.128.[3-4]
dnodesub2: 172.16.128.[4-4]
dnodesub3: 172.16.128.[6-6]
dnodesub4: 172.16.128.[6-10]
dnodesub5: 172.16.128.[10-11]


cnodes: @cnodesub0
cnodes_group1: @cnodesub0,@cnodesub1
cnodes_group2: @cnodesub0,@cnodesub1
dnodes: @dnodesub0,@dnodesub1,@dnodesub2,@dnodesub3,@dnodesub4,@dnodesub5,@dnodesub6,@dnodesub7,@dnodesub8,@dnodesub9,@dnodesub10,@dnodesub11,@dnodesub12
dnodes_left: @dnodesub0,@dnodesub1,@dnodesub2,@dnodesub3,@dnodesub4,@dnodesub5,@dnodesub6
dnodes_right: @dnodesub0,@dnodesub1,@dnodesub2,@dnodesub3,@dnodesub4,@dnodesub5

all: @cnodes,@dnodes
"""

ALL_12 = [f"172.16.128.{i}" for i in range(1, 13)]


class TestParseGroupFile:
    def test_duplicate_keys_are_kept_in_order(self):
        groups = parse_group_file(EBOX_LOCAL_CFG)
        assert groups["cnodesub0"] == ["172.16.128.[1-12]", "172.16.128.[1-3]", "172.16.128.[4-7]"]
        assert groups["dnodesub0"] == ["172.16.128.[1-1]", "172.16.128.[1-2]", "172.16.128.[1-1]"]

    def test_comments_blank_lines_and_non_group_lines_ignored(self):
        groups = parse_group_file("# header\n\nnot a group line\ncnodes: 10.0.0.1\n")
        assert groups == {"cnodes": ["10.0.0.1"]}


class TestExpandNodeset:
    def test_comma_list_inside_brackets(self):
        assert expand_nodeset("10.0.0.[1-3,5]", {}) == ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.5"]

    def test_single_index_bracket(self):
        assert expand_nodeset("10.0.0.[5]", {}) == ["10.0.0.5"]

    def test_comma_and_space_separated_tokens(self):
        assert expand_nodeset("10.0.0.1,10.0.0.2 10.0.0.3", {}) == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def test_zero_padding_preserved(self):
        assert expand_nodeset("node[08-10]", {}) == ["node08", "node09", "node10"]

    def test_multiple_bracket_groups(self):
        assert expand_nodeset("10.0.[1-2].[1-2]", {}) == ["10.0.1.1", "10.0.1.2", "10.0.2.1", "10.0.2.2"]

    def test_duplicates_removed_order_preserved(self):
        assert expand_nodeset("10.0.0.[2-3],10.0.0.[1-2]", {}) == ["10.0.0.2", "10.0.0.3", "10.0.0.1"]

    def test_comma_joined_group_refs(self):
        groups = {"a": ["10.0.0.1"], "b": ["10.0.0.2"]}
        assert expand_nodeset("@a,@b", groups) == ["10.0.0.1", "10.0.0.2"]

    def test_unknown_group_and_cycles_do_not_raise(self):
        groups = {"a": ["@b"], "b": ["@a", "10.0.0.9"]}
        assert expand_nodeset("@a,@missing", groups) == ["10.0.0.9"]


class TestResolveGroupFieldConfig:
    def test_cnodes_is_the_union_of_every_cnodesub0_line(self):
        groups = parse_group_file(EBOX_LOCAL_CFG)
        assert sorted(resolve_group("cnodes", groups), key=lambda ip: int(ip.rsplit(".", 1)[1])) == ALL_12

    def test_dnodes_includes_172_16_128_2(self):
        groups = parse_group_file(EBOX_LOCAL_CFG)
        dnodes = resolve_group("dnodes", groups)
        assert "172.16.128.2" in dnodes
        assert len(dnodes) == len(set(dnodes)) == 12


class TestFoldNodeset:
    def test_contiguous_run_folds_to_range(self):
        assert fold_nodeset(ALL_12) == "172.16.128.[1-12]"

    def test_gaps_and_singles(self):
        ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.5", "10.0.0.7", "10.0.0.8"]
        assert fold_nodeset(ips) == "10.0.0.[1-3],10.0.0.5,10.0.0.[7-8]"

    def test_multiple_subnets(self):
        ips = ["172.16.129.1", "172.16.128.1", "172.16.128.2", "172.16.129.2"]
        assert fold_nodeset(ips) == "172.16.128.[1-2],172.16.129.[1-2]"

    def test_empty(self):
        assert fold_nodeset([]) == ""


class TestNetworkConfigDiscoversEveryNode:
    def test_parse_local_cfg_unions_duplicate_keys(self):
        wf = NetworkConfigWorkflow()
        groups = wf._parse_local_cfg(EBOX_LOCAL_CFG)
        assert set(groups["cnodes"]) == set(ALL_12)
        assert set(groups["all"]) == set(ALL_12)

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_step1_discovers_all_12_ebox_hosts(self, mock_ssh):
        wf = NetworkConfigWorkflow()
        wf.set_credentials({"cluster_ip": "172.16.128.5", "node_user": "vastdata", "node_password": "pw"})
        wf.set_output_callback(MagicMock())
        mock_ssh.side_effect = [
            (0, "ebox-5\n", ""),
            (0, 'NAME="Rocky Linux"\n', ""),
            (0, EBOX_LOCAL_CFG, ""),
        ]
        result = wf.run_step(1)
        assert result["success"] is True
        discovered = set(wf._step_data["all_nodes"].values())
        assert discovered == set(ALL_12)


class TestVnetmapHostListIncludesEveryNode:
    def test_parse_local_cfg_returns_full_union(self):
        wf = VnetmapWorkflow()
        wf.set_output_callback(MagicMock())
        cnodes, dnodes = wf._parse_local_cfg(EBOX_LOCAL_CFG)
        assert cnodes == "172.16.128.[1-12]"
        assert dnodes == "172.16.128.[1-12]"

    def test_brace_conversion_of_folded_ranges(self):
        wf = VnetmapWorkflow()
        wf.set_output_callback(MagicMock())
        cfg = "cnodesub0: 10.0.0.[1-3,5]\ncnodes: @cnodesub0\ndnodes: 10.0.1.[7]\n"
        cnodes, dnodes = wf._parse_local_cfg(cfg)
        assert cnodes == "10.0.0.[1-3],10.0.0.5"
        assert wf._convert_ip_format(cnodes) == "{10.0.0.{1..3},10.0.0.5}"
        assert dnodes == "10.0.1.7"
