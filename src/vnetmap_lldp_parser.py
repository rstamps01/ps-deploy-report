"""
VNetMap LLDP Output Parser

Parses ``vnetmap_lldp.py --operation show-mapping`` output (node-side LLDP
neighbour data, no switch login) into the same topology-row contract that
``VNetMapParser`` emits, so ``EnhancedPortMapper`` and ``network_diagram_v2``
can render a port map and diagram without switch credentials (NET-7).
"""

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_SERVICE_STATUS_RE = re.compile(r"LLDP service status:\s*(\d+)\s+active,\s*(\d+)\s+inactive", re.IGNORECASE)
_OPERATION_FAILED_RE = re.compile(r"^\s*Operation failed\b", re.MULTILINE)
_NO_CONNECTIONS_RE = re.compile(r"^\s*No (?:LLDP )?connections found\b", re.MULTILINE)
_SWITCH_SECTION_RE = re.compile(r"^\s*Connections for switch:\s*(.*?)\s*$")
_FINAL_SECTION_RE = re.compile(r"^\s*LLDP Connection Mapping:?\s*$", re.IGNORECASE)

_VERTICAL_BARS = str.maketrans({"│": "|", "┃": "|", "║": "|"})
_SEPARATOR_CHARS = set("+-=:─━═┼┬┴├┤┌┐└┘╞╡╪╋┏┓┗┛┣┫┳┻╔╗╚╝╠╣╦╩╬")
_RULE_CHARS = set("-=─━═")

# Normalised header text -> row field. Unknown headers are ignored so upstream
# column additions or reordering do not break parsing.
_COLUMN_ALIASES = {
    "hostname": "hostname",
    "node": "node",
    "port": "port",
    "ips": "ips",
    "ip": "ips",
    "switch": "switch",
    "switch name": "switch",
    "switch port": "switch_port",
}


def _ipv4_subnet_24(ip: str) -> Optional[str]:
    """Return the /24 prefix as ``"a.b.c"`` for a valid IPv4, else ``None``.

    Mirrors ``RackCentricDiagramGenerator._ipv4_subnet_24``; importing
    ``network_diagram_v2`` here would pull in its rendering stack.
    """
    if not ip or not isinstance(ip, str):
        return None
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return None
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return None
    if not all(0 <= o <= 255 for o in octets):
        return None
    return f"{octets[0]}.{octets[1]}.{octets[2]}"


def _most_common_subnet(ips: List[str]) -> Optional[str]:
    """Return the most frequent /24 among ``ips`` (the NET-3 switch-subnet rule).

    Ties resolve exactly as ``RackCentricDiagramGenerator._compute_switch_subnet``
    does (highest count, then the lexicographically greatest subnet) so the
    parser's labels agree with the diagram's subnet colouring.
    """
    counts: Dict[str, int] = defaultdict(int)
    for ip in ips:
        subnet = _ipv4_subnet_24(ip)
        if subnet:
            counts[subnet] += 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _subnet_sort_key(subnet: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in subnet.split("."))


def _network_label(index: int) -> str:
    """Return ``A``..``Z``, then ``AA``, ``AB``... for a zero-based index."""
    label = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        label = chr(ord("A") + rem) + label
    return label


def _clean_lines(text: str) -> List[str]:
    """Strip ANSI codes and resolve ``\\r`` overwrites to what a terminal shows.

    Progress bars redraw a line with ``\\r``; the last non-blank segment is the
    text left on screen.
    """
    text = _ANSI_RE.sub("", text).replace("\r\n", "\n")
    lines = []
    for line in text.split("\n"):
        if "\r" in line:
            segments = [s for s in line.split("\r") if s.strip()]
            line = segments[-1] if segments else ""
        lines.append(line.translate(_VERTICAL_BARS))
    return lines


def _is_separator(stripped: str) -> bool:
    body = stripped.replace("|", "").replace(" ", "")
    return bool(body) and set(body) <= _SEPARATOR_CHARS and bool(set(body) & _RULE_CHARS)


def _is_table_row(stripped: str) -> bool:
    return len(stripped) > 1 and stripped.startswith("|") and stripped.endswith("|")


def _split_cells(stripped: str) -> List[str]:
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _extract_tables(lines: List[str]) -> List[Tuple[Optional[str], List[str], List[List[str]]]]:
    """Return ``(section_switch, header_cells, data_rows)`` for every bordered table.

    ``section_switch`` is the name from the preceding ``Connections for
    switch:`` line (per-switch tables), or ``None``.
    """
    tables: List[Tuple[Optional[str], List[str], List[List[str]]]] = []
    section_switch: Optional[str] = None
    header: Optional[List[str]] = None
    rows: List[List[str]] = []
    header_closed = False

    def close() -> None:
        nonlocal header, rows, header_closed
        if header is not None:
            tables.append((section_switch, header, rows))
        header, rows, header_closed = None, [], False

    for line in lines:
        stripped = line.strip()
        if _is_separator(stripped):
            if header is None:
                continue
            if not rows and not header_closed:
                header_closed = True
                continue
            close()
            continue
        if _is_table_row(stripped):
            cells = _split_cells(stripped)
            if header is None:
                header = cells
            else:
                rows.append(cells)
            continue

        close()
        section_match = _SWITCH_SECTION_RE.match(line)
        if section_match:
            section_switch = section_match.group(1) or None
        elif _FINAL_SECTION_RE.match(line):
            section_switch = None
    close()
    return tables


def _collect_records(
    tables: List[Tuple[Optional[str], List[str], List[List[str]]]],
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Map table cells to records by header name.

    Returns the final-table records when that table has rows, otherwise the
    records rebuilt from the per-switch tables, plus which source was used.
    """
    final_records: List[Dict[str, str]] = []
    per_switch_records: List[Dict[str, str]] = []

    for section_switch, header, rows in tables:
        columns: Dict[str, int] = {}
        for idx, name in enumerate(header):
            field = _COLUMN_ALIASES.get(re.sub(r"\s+", " ", name).strip().lower())
            if field and field not in columns:
                columns[field] = idx
        if "hostname" not in columns or "switch_port" not in columns:
            continue

        for cells in rows:
            if len(cells) != len(header):
                logger.debug("Skipping vnetmap_lldp row with %d cells (header has %d)", len(cells), len(header))
                continue
            record = {field: cells[idx] for field, idx in columns.items()}
            if "switch" in columns:
                final_records.append(record)
            elif section_switch:
                record["switch"] = section_switch
                per_switch_records.append(record)

    if final_records:
        return final_records, "final"
    if per_switch_records:
        return per_switch_records, "per_switch"
    return [], None


def _build_rows(records: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Convert records to topology rows, dropping switchless and duplicate rows."""
    rows: List[Dict[str, Any]] = []
    seen: set = set()
    for record in records:
        hostname = record.get("hostname", "")
        switch_name = record.get("switch", "")
        if not switch_name:
            logger.warning("Skipping vnetmap_lldp row for %s with no switch name", hostname or "unknown host")
            continue
        ips = [token for token in re.split(r"[,\s]+", record.get("ips", "")) if token]
        row = {
            "hostname": hostname,
            "node_hostname": hostname,
            "node_ip": "",
            "node_mgmt_ip": record.get("node", ""),
            "ips": ips,
            "interface": record.get("port", ""),
            "switch_name": switch_name,
            "switch_ip": switch_name,
            "port": record.get("switch_port", ""),
            "mac": "",
            "network": "",
        }
        key = (hostname, row["node_mgmt_ip"], row["interface"], tuple(ips), switch_name, row["port"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _data_ip_candidates(row: Dict[str, Any]) -> List[str]:
    """Return the IPv4s in the row's ``IPs`` cell that can be its data IP.

    The cell often also lists the node's management IP; drop it (and its /24)
    unless nothing else is left.
    """
    mgmt_ip = row["node_mgmt_ip"]
    mgmt_subnet = _ipv4_subnet_24(mgmt_ip)
    ipv4s = [token.split("/", 1)[0] for token in row["ips"]]
    ipv4s = [ip for ip in ipv4s if _ipv4_subnet_24(ip)]
    off_mgmt = [ip for ip in ipv4s if ip != mgmt_ip and _ipv4_subnet_24(ip) != mgmt_subnet]
    if off_mgmt:
        return off_mgmt
    return [ip for ip in ipv4s if ip != mgmt_ip] or ipv4s


def _assign_data_ips(rows: List[Dict[str, Any]]) -> None:
    """Set each row's ``node_ip``, preferring its switch's dominant /24."""
    candidates = [_data_ip_candidates(row) for row in rows]
    by_switch: Dict[str, List[str]] = defaultdict(list)
    for row, ips in zip(rows, candidates):
        by_switch[row["switch_name"]].extend(ips)
    preferred = {switch: _most_common_subnet(ips) for switch, ips in by_switch.items()}

    for row, ips in zip(rows, candidates):
        target = preferred.get(row["switch_name"])
        matching = [ip for ip in ips if _ipv4_subnet_24(ip) == target]
        if matching:
            row["node_ip"] = matching[0]
        elif ips:
            row["node_ip"] = ips[0]
        else:
            row["node_ip"] = row["ips"][0] if row["ips"] else ""


def _assign_networks(
    rows: List[Dict[str, Any]],
) -> Tuple[Dict[str, Optional[str]], Dict[str, str], List[Dict[str, Any]]]:
    """Label each switch's network by its canonical /24 and tag the rows.

    Distinct canonical subnets are ordered numerically and labelled A, B, C...;
    switches sharing a canonical subnet share its label, and switches with no
    IPv4 evidence get the next labels in name order. A row whose ``node_ip``
    is off its switch's subnet keeps the switch's label (NET-4 reads
    ``node_ip`` per row), and such switches are reported in the
    ``VNetMapParser`` ``cross_connections`` shape.

    Returns:
        ``(switch_subnets, switch_networks, cross_connections)``.
    """
    ips_by_switch: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        ips_by_switch[row["switch_name"]].append(row["node_ip"])

    switch_subnets = {switch: _most_common_subnet(ips) for switch, ips in sorted(ips_by_switch.items())}
    ordered_subnets = sorted({s for s in switch_subnets.values() if s}, key=_subnet_sort_key)
    label_by_subnet = {subnet: _network_label(i) for i, subnet in enumerate(ordered_subnets)}

    switch_networks: Dict[str, str] = {}
    next_index = len(ordered_subnets)
    for switch, subnet in switch_subnets.items():
        if subnet:
            switch_networks[switch] = label_by_subnet[subnet]
        else:
            switch_networks[switch] = _network_label(next_index)
            next_index += 1

    for row in rows:
        row["network"] = switch_networks[row["switch_name"]]

    cross_connections: List[Dict[str, Any]] = []
    for switch, ips in sorted(ips_by_switch.items()):
        subnets = sorted({s for s in map(_ipv4_subnet_24, ips) if s}, key=_subnet_sort_key)
        if len(subnets) > 1:
            cross_connections.append(
                {
                    "switch_ip": switch,
                    "networks": subnets,
                    "network_labels": [label_by_subnet.get(s, "?") for s in subnets],
                }
            )
    return switch_subnets, switch_networks, cross_connections


def _base_result() -> Dict[str, Any]:
    return {
        "available": True,
        "source": "lldp",
        "topology": [],
        "cross_connections": [],
        "lldp_neighbors": [],
        "ib_switch_headers": [],
        "total_connections": 0,
        "switch_names": [],
        "switch_subnets": {},
        "switch_networks": {},
        "lldp_service_status": None,
        "operation_failed": False,
        "no_connections": False,
        "table_source": None,
    }


def _error_result(message: str) -> Dict[str, Any]:
    result = _base_result()
    result["available"] = False
    result["error"] = message
    return result


def parse_lldp_text(text: str) -> Dict[str, Any]:
    """Parse ``vnetmap_lldp.py --operation show-mapping`` output text.

    Reads the final ``LLDP Connection Mapping`` table, or rebuilds the rows
    from the per-switch ``Connections for switch:`` tables when it is missing.
    Columns are matched by header name; banner text, ``\\r`` progress redraws,
    ANSI codes and box-drawing characters are tolerated.

    Empty and failed runs mirror ``VNetMapParser``, which reports
    ``available: True`` with an empty topology whenever the file was read:
    ``No LLDP connections found`` gives ``available: True``, no rows and
    ``no_connections: True``; ``Operation failed`` sets
    ``operation_failed: True`` and keeps any rows already printed. Callers
    decide whether zero connections is a failure.

    Args:
        text: Full captured stdout of the tool.

    Returns:
        The ``VNetMapParser.parse()`` keys (``available``, ``topology``,
        ``cross_connections``, ``lldp_neighbors``, ``ib_switch_headers``,
        ``total_connections``) plus ``source`` (``"lldp"``), ``switch_names``
        (sorted, unique), ``switch_subnets`` (name to canonical ``"a.b.c"``
        or ``None``), ``switch_networks`` (name to network label),
        ``lldp_service_status`` (``{"active": n, "inactive": n}`` or ``None``),
        ``operation_failed``, ``no_connections`` and ``table_source``
        (``"final"``, ``"per_switch"`` or ``None``). Each topology row has
        ``hostname``, ``node_hostname``, ``node_ip`` (data IP), ``node_mgmt_ip``,
        ``ips`` (every address in the ``IPs`` cell), ``interface``,
        ``switch_name``, ``switch_ip`` (the switch name until the extractor
        resolves it), ``port`` (native switch port name), ``mac`` (``""``) and
        ``network``.
    """
    result = _base_result()
    lines = _clean_lines(text)
    cleaned = "\n".join(lines)

    status_matches = _SERVICE_STATUS_RE.findall(cleaned)
    if status_matches:
        active, inactive = status_matches[-1]
        result["lldp_service_status"] = {"active": int(active), "inactive": int(inactive)}
    result["operation_failed"] = bool(_OPERATION_FAILED_RE.search(cleaned))
    result["no_connections"] = bool(_NO_CONNECTIONS_RE.search(cleaned))

    records, table_source = _collect_records(_extract_tables(lines))
    rows = _build_rows(records)
    _assign_data_ips(rows)
    switch_subnets, switch_networks, cross_connections = _assign_networks(rows)

    result.update(
        {
            "topology": rows,
            "cross_connections": cross_connections,
            "total_connections": len(rows),
            "switch_names": sorted(switch_subnets),
            "switch_subnets": switch_subnets,
            "switch_networks": switch_networks,
            "table_source": table_source,
        }
    )
    return result


class VNetMapLLDPParser:
    """Parser for ``vnetmap_lldp.py --operation show-mapping`` output files."""

    parse_lldp_text = staticmethod(parse_lldp_text)

    def __init__(self, output_file: str):
        """
        Initialize parser with a vnetmap_lldp output file.

        Args:
            output_file: Path to the captured ``show-mapping`` output
        """
        self.output_file = Path(output_file)
        self.topology_data: List[Dict[str, Any]] = []
        self.cross_connections: List[Dict[str, Any]] = []

    def parse(self) -> Dict[str, Any]:
        """
        Parse the output file. Never raises.

        Returns:
            The ``parse_lldp_text`` result, or ``available: False`` with an
            ``error`` when the file is missing, unreadable or unparseable.
        """
        if not self.output_file.exists():
            return _error_result(f"VNetMap LLDP output file not found: {self.output_file}")

        try:
            content = self.output_file.read_bytes().decode("utf-8", errors="replace")
        except OSError as e:
            return _error_result(f"Error reading vnetmap_lldp output: {e}")

        try:
            result = parse_lldp_text(content)
        except Exception as e:
            logger.exception("Error parsing vnetmap_lldp output %s", self.output_file)
            return _error_result(f"Error parsing vnetmap_lldp output: {e}")

        self.topology_data = result["topology"]
        self.cross_connections = result["cross_connections"]
        return result

    def get_connections_by_switch(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group parsed connections by switch key.

        Returns:
            Dict mapping ``switch_ip`` (the switch name until resolved) to its
            connections, sorted by switch port number
        """
        connections_by_switch: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for conn in self.topology_data:
            connections_by_switch[conn["switch_ip"]].append(conn)
        for conns in connections_by_switch.values():
            conns.sort(key=lambda c: [int(d) for d in re.findall(r"\d+", c["port"])])
        return dict(connections_by_switch)

    def has_cross_connections(self) -> bool:
        """Check if any switch serves nodes from more than one /24."""
        return len(self.cross_connections) > 0

    def get_cross_connection_summary(self) -> str:
        """
        Get human-readable summary of cross-connection issues.

        Returns:
            Summary string describing cross-connections
        """
        if not self.has_cross_connections():
            return "No cross-connections detected. All cabling is correct."
        return "; ".join(
            f"Switch {issue['switch_ip']} has multiple internal networks ({', '.join(issue['networks'])})"
            for issue in self.cross_connections
        )
