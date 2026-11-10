#!/usr/bin/env python3
"""Build a deterministic context pack for a tracker item (no model involved).

Writes ``docs/issues/<ID>/context.md``: where the item's terms appear in the
code (file, enclosing function/class and its line range), the matching test
files, and recent commits touching those files. Planners and worker subagents
read the pack instead of re-exploring the codebase, and later chats reuse it.

Terms come from ``--terms`` or, if omitted, from backticked identifiers and
paths in ``docs/issues/<ID>/spec.md``.

Usage:
    python3 scripts/context-pack.py FR-16 [--terms run_ssh_command _emit_run_output] [--stdout]
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

SEARCH_DIRS = ("src", "tests", "frontend", "scripts")
MAX_BYTES = 6000
MAX_TERMS = 15
MAX_HITS_PER_TERM = 8
IDENT_RE = re.compile(r"`([A-Za-z_][\w./-]{2,80})`")


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    return Path(out.stdout.strip()) if out.returncode == 0 else Path.cwd()


def terms_from_spec(spec: Path) -> List[str]:
    """Extract backticked identifiers and paths from a spec, most frequent first."""
    if not spec.is_file():
        return []
    counts: Dict[str, int] = defaultdict(int)
    for match in IDENT_RE.findall(spec.read_text(encoding="utf-8", errors="ignore")):
        term = match.strip("./")
        if term.lower() in {"true", "false", "none", "main", "develop"} or term.isdigit():
            continue
        counts[term] += 1
    return [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:MAX_TERMS]


def grep(root: Path, term: str) -> List[Tuple[str, int]]:
    """Return (path, line) hits for ``term`` in tracked files under SEARCH_DIRS."""
    if "/" in term or term.endswith((".py", ".html", ".js", ".md", ".sh")):
        out = subprocess.run(["git", "ls-files", "--", f"*{term}"], cwd=root, capture_output=True, text=True)
        return [(p, 0) for p in out.stdout.split()]
    out = subprocess.run(
        ["git", "grep", "-n", "-I", "-F", "-w", term, "--", *SEARCH_DIRS],
        cwd=root,
        capture_output=True,
        text=True,
    )
    hits = []
    for line in out.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            hits.append((parts[0], int(parts[1])))
    return hits


def python_spans(path: Path) -> List[Tuple[int, int, str]]:
    """Return (start, end, qualified name) for every function/class in a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (SyntaxError, ValueError):
        return []
    spans: List[Tuple[int, int, str]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                spans.append((child.lineno, getattr(child, "end_lineno", child.lineno) or child.lineno, name))
                walk(child, name + ".")

    walk(tree, "")
    return spans


def enclosing(spans: List[Tuple[int, int, str]], line: int) -> Optional[Tuple[int, int, str]]:
    best = None
    for start, end, name in spans:
        if start <= line <= end and (best is None or start >= best[0]):
            best = (start, end, name)
    return best


def recent_commits(root: Path, files: Iterable[str], limit: int = 6) -> List[str]:
    files = list(files)[:10]
    if not files:
        return []
    out = subprocess.run(
        ["git", "log", f"-n{limit}", "--date=short", "--format=%h %ad %s", "--", *files],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def build_pack(root: Path, item: str, terms: List[str]) -> str:
    """Return the Markdown context pack for ``item`` and ``terms``."""
    span_cache: Dict[str, List[Tuple[int, int, str]]] = {}
    lines = [f"# Context pack: {item}", "", f"Terms: {', '.join(f'`{t}`' for t in terms) or '(none)'}", ""]
    touched: Dict[str, int] = defaultdict(int)
    tests: Set[str] = set()
    for term in terms:
        hits = grep(root, term)
        if not hits:
            continue
        lines.append(f"## `{term}` ({len(hits)} hits)")
        seen: Set[Tuple[str, str]] = set()
        shown = 0
        for path, line in hits:
            touched[path] += 1
            if path.startswith("tests/"):
                tests.add(path)
            where = f"L{line}" if line else "file"
            if path.endswith(".py") and line:
                spans = span_cache.setdefault(path, python_spans(root / path))
                span = enclosing(spans, line)
                if span:
                    where = f"`{span[2]}` L{span[0]}-{span[1]}"
            if (path, where) in seen or shown >= MAX_HITS_PER_TERM:
                continue
            seen.add((path, where))
            shown += 1
            lines.append(f"- `{path}` {where}")
        lines.append("")
    if touched:
        top = [p for p, _ in sorted(touched.items(), key=lambda kv: -kv[1]) if not p.startswith("tests/")][:10]
        lines += ["## Files by relevance", *[f"- `{p}` ({touched[p]} hits)" for p in top], ""]
        if tests:
            lines += ["## Tests to run", f"`python3 -m pytest {' '.join(sorted(tests)[:8])} -x --lf`", ""]
        commits = recent_commits(root, top)
        if commits:
            lines += ["## Recent commits on these files", *[f"- {c}" for c in commits], ""]
    text = "\n".join(lines)
    if len(text.encode()) > MAX_BYTES:
        text = text.encode()[: MAX_BYTES - 60].decode(errors="ignore").rsplit("\n", 1)[0]
        text += "\n\n_(truncated at 6 KB; narrow the terms with --terms)_\n"
    return text


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build docs/issues/<ID>/context.md without a model.")
    parser.add_argument("item", help="tracker ID, e.g. FR-16")
    parser.add_argument("--terms", nargs="*", default=None, help="symbols/paths to locate (default: from spec.md)")
    parser.add_argument("--stdout", action="store_true", help="print instead of writing the file")
    args = parser.parse_args(argv)

    root = repo_root()
    issue_dir = root / "docs" / "issues" / args.item
    terms = args.terms or terms_from_spec(issue_dir / "spec.md")
    if not terms:
        print(f"No terms: pass --terms or add backticked identifiers to {issue_dir / 'spec.md'}", file=sys.stderr)
        return 1
    pack = build_pack(root, args.item, terms[:MAX_TERMS])
    if args.stdout:
        print(pack)
        return 0
    issue_dir.mkdir(parents=True, exist_ok=True)
    (issue_dir / "context.md").write_text(pack, encoding="utf-8")
    print(f"Wrote {issue_dir / 'context.md'} ({len(pack.encode())} bytes, {len(terms)} terms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
