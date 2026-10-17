"""Resolve ClusterShell node groups from ``/etc/clustershell/groups.d/local.cfg``.

ClusterShell's default ``local`` group source maps a group with
``sed -n 's/^$GROUP:\\(.*\\)/\\1/p' local.cfg``: every line that defines the
group contributes to it.  EBox clusters rely on this and repeat group keys
across sections, so resolution must take the union of all definitions rather
than the last one.  Nodeset operators (``!``, ``&``, ``^``) are not used by
VAST and are not supported.
"""

import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

_BRACKET_RE = re.compile(r"\[([^\[\]]*)\]")
_TRAILING_NUMBER_RE = re.compile(r"^(.*?)(\d+)$")


def parse_group_file(text: str) -> Dict[str, List[str]]:
    """Collect every definition of every group, in file order.

    Args:
        text: Contents of a ClusterShell ``groups.d/*.cfg`` file.

    Returns:
        Mapping of group name to the list of raw value strings, one per
        defining line.
    """
    groups: Dict[str, List[str]] = {}
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if not key or not re.fullmatch(r"[0-9A-Za-z_.-]+", key):
            continue
        groups.setdefault(key, []).append(value.strip())
    return groups


def _split_tokens(expr: str) -> List[str]:
    """Split on commas and whitespace that are outside brackets."""
    tokens: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in expr:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(depth - 1, 0)
        if depth == 0 and (ch == "," or ch.isspace()):
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(ch)
    if current:
        tokens.append("".join(current))
    return tokens


def _expand_range_list(spec: str) -> List[str]:
    """Expand ``1-3,5,08-10`` into ``['1','2','3','5','08','09','10']``."""
    values: List[str] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, _, hi = part.partition("-")
            if not (lo.isdigit() and hi.isdigit()):
                continue
            width = len(lo) if lo.startswith("0") and len(lo) > 1 else 0
            for i in range(int(lo), int(hi) + 1):
                values.append(str(i).zfill(width))
        elif part.isdigit():
            values.append(part)
    return values


def _expand_brackets(token: str) -> List[str]:
    match = _BRACKET_RE.search(token)
    if not match:
        return [token]
    head, tail = token[: match.start()], token[match.end() :]
    expanded: List[str] = []
    for value in _expand_range_list(match.group(1)):
        expanded.extend(_expand_brackets(f"{head}{value}{tail}"))
    return expanded


def expand_nodeset(
    expr: str,
    groups: Dict[str, List[str]],
    _visiting: Optional[Set[str]] = None,
) -> List[str]:
    """Expand a nodeset expression into an ordered, de-duplicated node list.

    Supports comma/space separated tokens, ``@group`` references (recursive,
    cycle-safe), and bracket ranges such as ``172.16.128.[1-3,5]``.

    Args:
        expr: Nodeset expression.
        groups: Output of :func:`parse_group_file`.

    Returns:
        Node names in first-seen order.
    """
    visiting = _visiting if _visiting is not None else set()
    nodes: List[str] = []
    seen: Set[str] = set()

    def _add(items: Iterable[str]) -> None:
        for item in items:
            if item not in seen:
                seen.add(item)
                nodes.append(item)

    for token in _split_tokens(expr or ""):
        if token.startswith("@"):
            name = token[1:]
            if name in visiting or name not in groups:
                continue
            _add(resolve_group(name, groups, visiting))
        else:
            _add(_expand_brackets(token))
    return nodes


def resolve_group(
    name: str,
    groups: Dict[str, List[str]],
    _visiting: Optional[Set[str]] = None,
) -> List[str]:
    """Resolve a group to the union of all of its definitions.

    Args:
        name: Group name without the ``@`` prefix.
        groups: Output of :func:`parse_group_file`.

    Returns:
        Node names in first-seen order; empty if the group is unknown.
    """
    visiting = set(_visiting or ())
    visiting.add(name)
    return expand_nodeset(",".join(groups.get(name, [])), groups, visiting)


def resolve_all_groups(groups: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Resolve every group; groups that expand to nothing are omitted."""
    resolved: Dict[str, List[str]] = {}
    for name in groups:
        nodes = resolve_group(name, groups)
        if nodes:
            resolved[name] = nodes
    return resolved


def fold_nodeset(nodes: Iterable[str]) -> str:
    """Fold nodes into a comma-separated ClusterShell expression.

    Nodes sharing a prefix with a trailing number are folded into
    ``prefix[a-b]`` runs; single members stay unbracketed.  The result is
    sorted by prefix and number.

    Args:
        nodes: Node names or IPs.

    Returns:
        Expression such as ``10.0.0.[1-3],10.0.0.5``; empty for no nodes.
    """
    by_prefix: Dict[str, Set[int]] = {}
    others: List[str] = []
    for node in dict.fromkeys(nodes):
        match = _TRAILING_NUMBER_RE.match(node)
        if match and not (match.group(2).startswith("0") and len(match.group(2)) > 1):
            by_prefix.setdefault(match.group(1), set()).add(int(match.group(2)))
        else:
            others.append(node)

    parts: List[str] = []
    for prefix in sorted(by_prefix, key=_prefix_sort_key):
        for lo, hi in _runs(sorted(by_prefix[prefix])):
            parts.append(f"{prefix}{lo}" if lo == hi else f"{prefix}[{lo}-{hi}]")
    parts.extend(others)
    return ",".join(parts)


def _prefix_sort_key(prefix: str) -> Tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", prefix))


def _runs(numbers: List[int]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    for n in numbers:
        if runs and n == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], n)
        else:
            runs.append((n, n))
    return runs
