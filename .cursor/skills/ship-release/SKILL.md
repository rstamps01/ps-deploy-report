---
name: ship-release
description: Ship a prepared release — merge develop to main, tag vX.Y.Z, push, and verify build-release.yml produces and attaches the macOS .dmg and Windows .zip. Use after prepare-release, as the final release step. Requires explicit approval before merging/tagging.
disable-model-invocation: true
---

# ship-release

Final release stage. Merges to `main`, tags, and verifies artifacts. Every step here is destructive/irreversible — **pause for explicit user approval before merging to `main` and before tagging**.

## Preconditions

- `prepare-release` complete: version synced, CHANGELOG folded, release notes written, quality gate green.
- User has approved the release.

## Steps

1. **Merge to main.** `git checkout main && git pull origin main && git merge --no-ff develop`. Resolve conflicts; do not force.
2. **Push main.** `git push origin main`.
3. **Tag** the release commit: `git tag -a vX.Y.Z -m "Release vX.Y.Z — <summary>"` (annotated). For pre-releases use `vX.Y.Z-beta`/`-rc1` (the build workflow marks these prerelease).
4. **Push the tag.** `git push origin vX.Y.Z` — this triggers `.github/workflows/build-release.yml`, which checks out the tagged commit and builds from the release code.
5. **Verify the build** via `gh`: `gh run watch` / `gh run list --workflow=build-release.yml`. Confirm the run is green.
6. **Verify artifacts.** Confirm the GitHub Release for `vX.Y.Z` has both mac DMGs (`-mac-arm64.dmg`, `-mac-x64.dmg`) and the `-win.zip` attached, and is marked **latest / non-prerelease** (`gh release view vX.Y.Z`).
7. **Live update-pill check (QA §6b).** From a real *previous-version* build on an online machine, confirm the header pill flips to **UPDATE AVAILABLE** and Download offers the OS-matched installer (`docs/development/QA-TEST-PLAN.md`).
8. **Back to develop.** `git checkout develop && git merge main` (keep develop current) and push.
9. **Announce + record.** Post the success comms (Slack + Confluence release page, draft-then-confirm); record the release in `docs/DECISIONS.md`; `update-tracker`.

## Failure handling

If the build-release run fails or a post-release smoke test fails, route to `remediate-failure`; **rollback** (re-point latest release / replace artifact) is the first option offered.

## Leverages

Rules: `release-packaging-12`, `change-control-07`. Skills: `finishing-a-development-branch`, `remediate-failure`, `publish-docs`, `update-tracker`.

## Completion checklist

- [ ] Approval obtained before merge + tag
- [ ] `develop` merged to `main`; both pushed
- [ ] Annotated tag `vX.Y.Z` pushed; build-release run green
- [ ] `.dmg` + `.zip` attached to the GitHub Release
- [ ] develop re-synced; release recorded + announced
