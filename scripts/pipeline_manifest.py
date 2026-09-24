#!/usr/bin/env python3
"""Adapter for the ``.cursor/pipeline.yml`` project manifest (pipeline §30).

Lifecycle skills and scripts read canonical commands, gates, and toggles from
the manifest instead of hardcoding them, so the *same* skill works across
projects without edits. The schema is stack-agnostic: a Node/Go/Docker project
ships its own ``commands``/``artifacts`` under the same keys and every skill
keeps working.

This is the reference **Python adapter**. It has no third-party dependency
beyond PyYAML (already a runtime dependency).

Usage:
    pipeline_manifest.py list                 # list defined command names
    pipeline_manifest.py get <name>           # print one resolved command string
    pipeline_manifest.py gate                 # print blocking-gate commands, in order
    pipeline_manifest.py show                  # print key resolved fields
    pipeline_manifest.py validate [--strict]   # structural self-check (exit 1 on error)

Examples (skills/CI compose these):
    $(python3 scripts/pipeline_manifest.py get test_cov)
    python3 scripts/pipeline_manifest.py gate | while read -r cmd; do eval "$cmd" || exit 1; done
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def find_manifest(start: Optional[Path] = None) -> Path:
    """Locate ``.cursor/pipeline.yml`` by walking up from *start* (default cwd).

    Falls back to walking up from this file's location, so the adapter works
    whether it lives at ``<repo>/scripts/`` (an adopting project) or
    ``<repo>/core/scripts/`` (the framework repo). Returns a best-effort path
    even if nothing is found (``PipelineManifest.load`` then raises clearly).
    """
    searched: List[Path] = []
    base = (start or Path.cwd()).resolve()
    searched.append(base)
    searched.extend(base.parents)
    searched.extend(Path(__file__).resolve().parents)
    for d in searched:
        candidate = d / ".cursor" / "pipeline.yml"
        if candidate.exists():
            return candidate
    return base / ".cursor" / "pipeline.yml"


# Commands every adapter instance must define (skills depend on these keys).
REQUIRED_COMMANDS = ("install", "lint", "format_check", "typecheck", "test", "test_cov")

# Gate step name that resolves to the version-sync check rather than commands.*.
VERSION_SYNC_STEP = "version_sync"


class ManifestError(Exception):
    """Raised when the manifest is missing or structurally invalid."""


class PipelineManifest:
    """Parsed view over ``.cursor/pipeline.yml`` with command/gate resolution."""

    def __init__(self, data: Dict[str, Any], path: Path) -> None:
        self.data = data or {}
        self.path = Path(path)
        # Repo root = the directory that contains the .cursor/ folder holding the
        # manifest, so strict path checks resolve regardless of where the adapter
        # script itself lives.
        self.repo_root = self.path.resolve().parent.parent

    # -- loading -----------------------------------------------------------
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PipelineManifest":
        path = Path(path) if path is not None else find_manifest()
        if not path.exists():
            raise ManifestError(f"manifest not found: {path}")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ManifestError(f"manifest is not valid YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise ManifestError("manifest root must be a mapping")
        return cls(data, path)

    # -- accessors ---------------------------------------------------------
    @property
    def commands(self) -> Dict[str, str]:
        cmds = self.data.get("commands", {}) or {}
        if not isinstance(cmds, dict):
            raise ManifestError("`commands` must be a mapping")
        return cmds

    def command(self, name: str) -> str:
        """Return the shell command string for *name* (raises if undefined)."""
        cmds = self.commands
        if name not in cmds or not str(cmds[name]).strip():
            raise ManifestError(f"command not defined in manifest: {name}")
        return str(cmds[name])

    @property
    def coverage_floor(self) -> int:
        return int((self.data.get("quality", {}) or {}).get("coverage_floor", 0) or 0)

    @property
    def blocking_gate(self) -> List[str]:
        steps = (self.data.get("quality", {}) or {}).get("blocking_gate", []) or []
        if not isinstance(steps, list):
            raise ManifestError("`quality.blocking_gate` must be a list")
        return [str(s) for s in steps]

    def resolve_gate_step(self, step: str) -> str:
        """Map a blocking-gate step to its concrete command string."""
        if step == VERSION_SYNC_STEP:
            sync = (self.data.get("version", {}) or {}).get("sync_check")
            if not sync:
                raise ManifestError("blocking_gate references `version_sync` but `version.sync_check` is unset")
            return str(sync)
        return self.command(step)

    def gate_commands(self) -> List[str]:
        """Ordered list of concrete commands for the blocking gate."""
        return [self.resolve_gate_step(s) for s in self.blocking_gate]

    # -- validation --------------------------------------------------------
    def validate(self, strict: bool = False) -> List[str]:
        """Return a list of problems; empty means the manifest conforms.

        strict: also require that referenced on-disk paths exist.
        """
        errors: List[str] = []

        if self.data.get("schema_version") is None:
            errors.append("missing `schema_version`")

        project = self.data.get("project", {}) or {}
        for key in ("name", "language"):
            if not project.get(key):
                errors.append(f"missing `project.{key}`")

        # Required commands present + non-empty.
        cmds = self.data.get("commands", {}) or {}
        if not isinstance(cmds, dict):
            errors.append("`commands` must be a mapping")
        else:
            for name in REQUIRED_COMMANDS:
                if not str(cmds.get(name, "")).strip():
                    errors.append(f"missing/empty required command: `{name}`")

        # Coverage floor is a non-negative int.
        try:
            if self.coverage_floor < 0:
                errors.append("`quality.coverage_floor` must be >= 0")
        except (TypeError, ValueError):
            errors.append("`quality.coverage_floor` must be an integer")

        # Every blocking-gate step must resolve to a command.
        try:
            for step in self.blocking_gate:
                try:
                    self.resolve_gate_step(step)
                except ManifestError as exc:
                    errors.append(str(exc))
        except ManifestError as exc:
            errors.append(str(exc))

        # Version source declared.
        version = self.data.get("version", {}) or {}
        if not version.get("source_file"):
            errors.append("missing `version.source_file`")

        if strict:
            errors.extend(self._validate_paths(version))

        return errors

    def _validate_paths(self, version: Dict[str, Any]) -> List[str]:
        problems: List[str] = []
        source_file = version.get("source_file")
        if source_file and not (self.repo_root / source_file).exists():
            problems.append(f"`version.source_file` does not exist: {source_file}")
        release_dir = (self.data.get("release", {}) or {}).get("release_notes_dir")
        if release_dir and not (self.repo_root / release_dir).exists():
            problems.append(f"`release.release_notes_dir` does not exist: {release_dir}")
        register = (self.data.get("tracking", {}) or {}).get("register")
        if register and not (self.repo_root / register).exists():
            problems.append(f"`tracking.register` does not exist: {register}")
        return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cmd_list(m: PipelineManifest) -> int:
    for name in m.commands:
        print(name)
    return 0


def _cmd_get(m: PipelineManifest, name: str) -> int:
    print(m.command(name))
    return 0


def _cmd_gate(m: PipelineManifest) -> int:
    for cmd in m.gate_commands():
        print(cmd)
    return 0


def _cmd_show(m: PipelineManifest) -> int:
    project = m.data.get("project", {}) or {}
    print(f"project:        {project.get('name')} ({project.get('language')})")
    print(f"adoption_tier:  {m.data.get('adoption_tier')}")
    print(f"coverage_floor: {m.coverage_floor}")
    print(f"blocking_gate:  {', '.join(m.blocking_gate)}")
    print(f"commands:       {', '.join(m.commands)}")
    return 0


def _cmd_validate(m: PipelineManifest, strict: bool) -> int:
    errors = m.validate(strict=strict)
    if errors:
        print("Manifest validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    try:
        shown: Any = m.path.relative_to(m.repo_root)
    except ValueError:
        shown = m.path
    print(
        f"Manifest OK ({shown}): {len(m.commands)} commands, "
        f"coverage floor {m.coverage_floor}, gate [{', '.join(m.blocking_gate)}]"
    )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read the .cursor/pipeline.yml project manifest.")
    parser.add_argument("--manifest", type=Path, default=None, help="path to pipeline.yml (default: auto-discover)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list defined command names")
    p_get = sub.add_parser("get", help="print one resolved command string")
    p_get.add_argument("name")
    sub.add_parser("gate", help="print blocking-gate commands in order")
    sub.add_parser("show", help="print key resolved fields")
    p_val = sub.add_parser("validate", help="structural self-check")
    p_val.add_argument("--strict", action="store_true", help="also require referenced paths to exist")

    args = parser.parse_args(argv)
    try:
        manifest = PipelineManifest.load(args.manifest)
        if args.cmd == "list":
            return _cmd_list(manifest)
        if args.cmd == "get":
            return _cmd_get(manifest, args.name)
        if args.cmd == "gate":
            return _cmd_gate(manifest)
        if args.cmd == "show":
            return _cmd_show(manifest)
        if args.cmd == "validate":
            return _cmd_validate(manifest, strict=args.strict)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
