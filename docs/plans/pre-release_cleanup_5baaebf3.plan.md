---
name: pre-release cleanup
overview: Centralize hardware images to a single shipped source (assets/) with config/ as runtime-only, retire dead files via git delete behind a recovery tag (not a local-only archive), reconcile the two archive folders, and remove stray tracked artifacts - all before the v1.5.8 release.
todos:
  - id: recovery-tag
    content: Create + push annotated git tag pre-1.5.8-cleanup before any deletion (recovery anchor)
    status: pending
  - id: img-promote
    content: Promote mqm8700-hs2f, nexus_c9332d_gx2b, cisco_ebox to BUILTIN_DEVICES and git mv their images into assets/hardware_images/
    status: pending
  - id: img-runtime
    content: Remove orphan config/hardware_images/ebox_1u.png, reset device_library.json to {}, git rm --cached config/hardware_images, gitignore config/hardware_images/
    status: pending
  - id: img-missing
    content: Reconcile broadwell/cascadelake/arista_7060dx5 missing built-in image references; verify .spec bundles all referenced files
    status: pending
  - id: archive-delete
    content: git rm -r .archive (13 dead files), add .archive/ to .gitignore, fix stale reports/README.md references
    status: pending
  - id: relnotes-check
    content: Inventory release notes; grep for path references before any relocation; keep current-era notes at root unless a reference dictates moving
    status: pending
  - id: stray-artifacts
    content: Verify + git rm --cached any tracked .DS_Store/app.log/web_app.log/coverage.xml/.coverage/src/logs logs; ensure .gitignore covers them
    status: pending
  - id: cleanup-verify
    content: Fresh-checkout simulation + app/library/report smoke test + full quality gate (flake8/black/mypy/version-sync/tests)
    status: pending
isProject: false
---

# Pre-release codebase cleanup

Tighten file/folder structure before v1.5.8. Decisions confirmed: (1) retire dead files by deleting them behind a recovery git tag (best practice), not a local-only `.archive`; (2) consolidate hardware images to `assets/` as the single shipped source with `config/hardware_images/` as a gitignored runtime dir.

This shares the device-promotion and missing-image work with the v1.5.8 release plan's Phase 4 - do it once, here.

## Phase 0 - Recovery anchor (do first, before any deletion)

- Create an annotated tag on the current HEAD so every file removed below stays recoverable AND backed up on GitHub: `git tag -a pre-1.5.8-cleanup -m "Snapshot before pre-1.5.8 structure cleanup"` and push it. This is the "git is your archive" guarantee that replaces a local-only `.archive` mirror.

## Phase 1 - Consolidate hardware images (source vs runtime)

Canonical shipped source = `assets/hardware_images/` (globbed by [packaging/vast-reporter.spec](packaging/vast-reporter.spec), served by `/library/builtin-images/`, loaded by [src/rack_diagram.py](src/rack_diagram.py)). `config/hardware_images/` becomes runtime-only (auto-created by [src/app.py](src/app.py) line 318).

- Promote `mqm8700-hs2f`, `nexus_c9332d_gx2b`, `cisco_ebox` into `BUILTIN_DEVICES` in [src/hardware_library.py](src/hardware_library.py) (same change as release-plan Phase 4).
- `git mv` their images `config/hardware_images/{mqm8700-hs2f_1u.png,nexus_c9332d_gx2b_1u.png,cisco_ebox_1u.png}` -> `assets/hardware_images/`.
- Remove the orphan committed `config/hardware_images/ebox_1u.png` (duplicate of `assets/hardware_images/ebox_1u.png`, unreferenced).
- Reset the shipped [config/device_library.json](config/device_library.json) to `{}` (the 3 entries are now built-in) so fresh installs start with an empty user library; keep the file tracked so the app has a valid seed.
- `git rm -r --cached config/hardware_images` and add `config/hardware_images/` to [.gitignore](.gitignore) (runtime-only; app auto-creates it).
- Reconcile the 3 missing built-in image references (`broadwell_cbox_2u.png`, `cascadelake_cbox_2u.png`, `arista_7060dx5_..._2u.jpeg`) in [src/hardware_library.py](src/hardware_library.py) (shared with release-plan library-missing) - repoint to existing/generic or restore the files (server logs show they previously existed).
- Verify: no code "redirect" needed (built-in -> `assets`, user -> `config` are already correct); `.spec` bundles every referenced filename; `/library` and rack diagrams render the promoted devices from `/library/builtin-images/`.

## Phase 2 - Retire dead files via git delete (behind the Phase 0 tag)

- `git rm -r .archive` (13 tracked files: old release notes v1.2.0/v1.3.0 + push/command notes, `fix-*`/`test_*` scripts, `config.yaml.template`, `report-toc.xlsx`). Confirmed no code/CI/runtime dependencies; recoverable via `pre-1.5.8-cleanup`.
- Add `.archive/` to [.gitignore](.gitignore) (the existing `archive/` rule does not match the dot-prefixed folder), so any future local use stays local.
- Fix stale references in [reports/README.md](reports/README.md) lines 5, 93, 103 (`.archive/development_reports/`, `.archive/README.md` - neither exists).
- The plain `archive/` folder (already gitignored - local run artifacts + `RELEASE_NOTES_v1.4.2.md`) stays local; no git action needed. Note both archive concepts now resolve to "local-only, ignored."

## Phase 3 - Release-notes location (check before moving)

- Inventory root release notes (`RELEASE_NOTES_v1.5.0/1.5.6/1.5.7/1.5.8-beta.md`, plus the new `v1.5.8`). Grep for any path references in [.github/workflows](.github/workflows), docs, and README before relocating.
- Recommendation: keep current-era release notes at repo root (existing convention, low churn) unless a reference dictates otherwise; only the down-rev copies (v1.2.0/v1.3.0/v1.4.2) are retired via Phase 2 / left local. Confirm with a quick reference check; do not move if anything links to root paths.

## Phase 4 - Remove stray tracked artifacts (verify tracked first)

- Re-verify tracked status of `.DS_Store` files, root `app.log`/`web_app.log`, `coverage.xml`, `.coverage`, and `src/logs/*.log` via `git ls-files`. For any that are tracked, `git rm --cached` and confirm [.gitignore](.gitignore) covers them (most patterns already exist: `*.log`, `coverage.xml`, `.coverage`, `.DS_Store`).
- Add a `src/logs/` ignore if `src/logs/vast_report_generator.log` is tracked.

## Phase 5 - Verify

- Simulate a fresh checkout (e.g. `git archive` or a clean clone) and confirm: no `.archive/`, no committed user images, `device_library.json` is `{}`, and `assets/hardware_images/` contains every filename referenced by `hardware_library.py`.
- Launch the app: `/library` lists built-ins (incl. promoted devices), thumbnails load via `/library/builtin-images/`, and a generated report renders the promoted images (not generic fallback).
- Full quality gate: `flake8`, `black --check`, `mypy --ignore-missing-imports --no-strict-optional`, `bash scripts/check-version-sync.sh`, unit tests.

## Risks / notes

- Do NOT literally merge the image folders into one - the frozen `.dmg`/`.zip` needs a writable user dir separate from the read-only bundle; the source/runtime split is the consolidation.
- Phase 0 tag is the single point that makes Phase 2 safe; push it before deleting.
- Library/device-promotion work overlaps the v1.5.8 release plan - execute once and mark both plans' items done together.
- After cleanup, re-run the full test suite since `report_builder`/`rack_diagram` exercise image lookup.
