---
name: Project Housekeeping Cleanup
overview: Identify and archive stale files, clean up project structure, update documentation, and recommend best practices for the v1.5.0 codebase.
todos:
  - id: create-archive
    content: Create archive/ directory, add to .gitignore, move all stale files preserving structure
    status: completed
  - id: gitignore-safety
    content: "Update .gitignore: add archive/, verify logs/operations/ coverage"
    status: completed
  - id: pyproject-update
    content: Update pyproject.toml coverage omit to remove archived modules
    status: completed
  - id: fix-dup-test
    content: Fix duplicate test method name in test_workflows.py
    status: completed
  - id: doc-cleanup
    content: Update README/docs to remove references to archived files; correct session_manager.py narrative
    status: completed
  - id: verify-qa
    content: Run full test suite, lint, format checks after cleanup
    status: completed
isProject: false
---

# Project Housekeeping and Stale File Cleanup

## Archive Strategy

Create `archive/` at project root, added to `.gitignore`. Stale files are moved preserving their original directory structure (e.g., `src/enhanced_report_builder.py` -> `archive/src/enhanced_report_builder.py`).

## Files to Archive

### Definitely Stale -- Dead Code Modules

- `src/comprehensive_report_template.py` -- Only imported by `enhanced_report_builder.py`; excluded from coverage; never part of the runtime pipeline
- `src/enhanced_report_builder.py` -- No importers anywhere in app, CLI, GUI, or oneshot; dead alternate PDF implementation

### Definitely Stale -- Root Files

- `start_server.py` -- Duplicate Flask launcher (port 5173); canonical entrypoint is `python3 src/main.py --gui`; zero references in repo

### Definitely Stale -- Orphan Documentation

- `docs/CI-VALIDATION-REPORT.md` -- Point-in-time CI report; no references from any other file
- `docs/BUILD-STATUS.md` -- Previous cycle build status; no references
- `docs/FAILED-TESTS-ASSESSMENT.md` -- Historical test failure triage; issue already fixed per doc
- `docs/RELEASE-WORKFLOW-LOG-REVIEW.md` -- v1.4.2 Windows build incident log; historical
- `docs/superpowers/plans/2026-03-26-ssh-proxy-hop.md` -- Agent planning scratchpad; SSH proxy hop already shipped

### Definitely Stale -- Test Data

- `tests/data/test-installation.sh` -- No references anywhere
- `tests/data/test-cluster-full.txt` -- No references anywhere
- `tests/data/curl_test_report_20250929_*.txt` (3 files) -- Manual capture artifacts; no references
- `tests/data/mock_prometheus_devices.txt` -- Not imported by any test (only mentioned in a dev guide as "suggested fixture")

### Stale Script

- `scripts/curl_dnode_state.sh` -- No callers or documentation references

### Historical Release Notes (Archive, Not Delete)

- `RELEASE_NOTES_v1.4.2.md` -- Superseded by CHANGELOG entries; archive for posterity

## Files to Keep (Clarifications)

- `src/session_manager.py` -- **Actively used** by `script_runner.py` for tmux execution; should NOT be archived. Remove from "dead code" grouping in docs.
- `docs/confluence/`* -- All 26 files referenced by `.cursor/rules/design-guidelines-01.mdc`; gitignored, local-only reference docs. The extra `<customer-cluster>.3.0.md` can be archived since it's not in the rule's reference list.
- `RELEASE_NOTES_v1.5.0.md` -- Current release; keep

## .gitignore Updates

- Add `archive/` to `.gitignore`
- Verify `logs/operations/` is covered (credential safety -- JSONL files may contain switch passwords in reproduced shell commands)

## Documentation Updates

- Update `pyproject.toml` coverage omit to remove the two archived modules (keep `session_manager.py` since it's actually used)
- Update any README or doc references to archived files
- Remove `session_manager.py` from "dead code" narrative in docs

## Recommended Best Practices

- **Credential safety**: Ensure `logs/operations/` explicitly covered by `.gitignore` (JSONL files may contain passwords in command reproductions)
- **Duplicate test methods**: `tests/test_workflows.py` has duplicate `test_get_switch_ips_v1_fallback` method names -- the second silently overrides the first
- **Import graph validation**: Consider a CI step or pre-commit hook that detects unused source modules (prevents future dead code accumulation)
- **Doc link validation**: Orphan docs accumulate because nothing checks for unreferenced markdown files; a periodic link scan would catch these
- **Packaging icons**: `packaging/icons/icon.icns` and `icon.ico` referenced in spec but may be missing locally -- verify they exist for clean builds
