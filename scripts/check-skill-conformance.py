#!/usr/bin/env python3
"""Validate repo-local Cursor skills for structural conformance.

Credential-free, dependency-free (stdlib only) so it runs anywhere in CI.
Checks every .cursor/skills/<name>/SKILL.md against the authoring standard
documented in .cursor/skills/CATALOG.md:

  - YAML-style frontmatter delimited by '---' lines
  - name: lowercase/hyphen/digit, <= 64 chars, equal to the directory name
  - description: present, non-empty, <= 1024 chars
  - body <= 500 lines
  - at least one '## ' section heading
  - a '## Completion checklist' section

Exit code 0 = all skills conform; 1 = one or more violations.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
MAX_BODY_LINES = 500
MAX_DESC = 1024


def parse_frontmatter(text: str):
    """Return (frontmatter_dict, body_text) or (None, text) if no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    fm = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" in raw:
            key, _, val = raw.partition(":")
            fm[key.strip()] = val.strip()
    body = "\n".join(lines[end + 1 :])
    return fm, body


def check_skill(skill_md: Path):
    errors = []
    dir_name = skill_md.parent.name
    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    if fm is None:
        return [f"missing or unterminated frontmatter (expected '---' block at top)"]

    name = fm.get("name", "")
    if not name:
        errors.append("frontmatter missing 'name'")
    else:
        if not NAME_RE.match(name):
            errors.append(f"name '{name}' must be lowercase letters/digits/hyphens, <=64 chars")
        if name != dir_name:
            errors.append(f"name '{name}' does not match directory '{dir_name}'")

    desc = fm.get("description", "")
    if not desc:
        errors.append("frontmatter missing non-empty 'description'")
    elif len(desc) > MAX_DESC:
        errors.append(f"description too long ({len(desc)} > {MAX_DESC} chars)")

    body_lines = body.splitlines()
    if len(body_lines) > MAX_BODY_LINES:
        errors.append(f"body too long ({len(body_lines)} > {MAX_BODY_LINES} lines)")

    if not any(ln.startswith("## ") for ln in body_lines):
        errors.append("no '## ' section heading found")

    if not re.search(r"(?im)^##\s+completion checklist\s*$", body):
        errors.append("missing '## Completion checklist' section")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    skills_dir = root / ".cursor" / "skills"
    if not skills_dir.is_dir():
        print(f"No skills directory at {skills_dir} — nothing to check.")
        return 0

    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        print("No SKILL.md files found.")
        return 0

    total_errors = 0
    print(f"=== Skill conformance check ({len(skill_files)} skills) ===")
    for skill_md in skill_files:
        rel = skill_md.relative_to(root)
        errs = check_skill(skill_md)
        if errs:
            total_errors += len(errs)
            print(f"FAIL {rel}")
            for e in errs:
                print(f"      - {e}")
        else:
            print(f"OK   {rel}")

    print("")
    if total_errors:
        print(f"=== FAILED: {total_errors} conformance issue(s) ===")
        return 1
    print("=== PASSED: all skills conform ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
