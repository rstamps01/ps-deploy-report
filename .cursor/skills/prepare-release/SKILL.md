---
name: prepare-release
description: Prepare a release on develop — bump every version location, fold CHANGELOG [Unreleased] into the new version, generate release notes, and run the full quality gate. Use when changes on develop are ready to become a tagged release, before ship-release.
disable-model-invocation: true
---

# prepare-release

Release-prep stage. Gets `develop` into a releasable, version-consistent state. Does NOT merge/tag (that is `ship-release`). Enforces `release-packaging-12`.

## Preconditions

- On `develop`, all intended work merged, `quality-gate` green.
- Decide the SemVer bump: PATCH (fix), MINOR (feature), MAJOR (breaking) per `change-control-07`.

## Steps

1. **Bump the version — canonical first.** Update `src/app.py` `APP_VERSION` to `X.Y.Z`, then sync every other location:
   - `src/main.py` (argparse `--version`), `src/__init__.py` (`__version__` + docstring), `packaging/vast-reporter.spec` (`CFBundleShortVersionString`, `CFBundleVersion`), `README.md` version badge.
   - `packaging/build-mac.sh` / `packaging/build-windows.ps1` read `src/app.py` dynamically — no manual edit.
2. **Verify sync:** `bash scripts/check-version-sync.sh` must pass.
3. **Fold the CHANGELOG.** Move `## [Unreleased]` entries under `## [X.Y.Z] - YYYY-MM-DD` (Keep a Changelog: Added/Changed/Fixed).
4. **Release notes.** Create `docs/releases/RELEASE_NOTES_vX.Y.Z.md` (highlights, fixes, upgrade notes; include config/data migration steps if config keys changed).
5. **Docs consistency.** Run `publish-docs` (draft) so README/in-app/Confluence version + feature text match; confirm before publishing external surfaces.
6. **Full quality gate.** Run `quality-gate` end-to-end; produce a release checklist (tests, lint, format, types, version-sync, coverage).
7. **Cross-platform QA.** Work the per-release checklist in `docs/development/QA-TEST-PLAN.md`: confirm CI `qa-cross-os` + `build-smoke` are green, run the cross-OS functional subset for any OS at hand, validate the release-specific functional cases, and run the update-pill staged dry-run (`tests/test_update_release_readiness.py`). Schedule the live update-pill check for immediately after the tag.
8. **Update the register** (`update-tracker`): mark released items Done, refresh "Last updated" and "Next steps".

## Leverages

Rules: `release-packaging-12`, `change-control-07`, `documentation-08`, `ci-pipeline-13`. Skills: `quality-gate`, `publish-docs`, `update-tracker`. Docs: `docs/development/QA-TEST-PLAN.md`. Next stage: `ship-release`.

## Completion checklist

- [ ] All 6 version locations bumped; `check-version-sync.sh` passes
- [ ] CHANGELOG `[Unreleased]` folded into `[X.Y.Z]`
- [ ] `docs/releases/RELEASE_NOTES_vX.Y.Z.md` created
- [ ] Full quality gate green; release checklist produced
- [ ] Cross-platform QA (`QA-TEST-PLAN.md`) worked; update-pill dry-run green
- [ ] Register updated
