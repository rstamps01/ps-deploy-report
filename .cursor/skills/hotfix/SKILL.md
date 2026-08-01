---
name: hotfix
description: Ship an urgent patch for a released version by branching off the release tag (not develop), applying a minimal failing-first fix, running a fast-tracked gate, cutting a patch release, and back-merging. Use when a shipped release has a user-affecting defect that cannot wait for the normal develop cycle. Requires explicit approval before tagging/releasing.
disable-model-invocation: true
---

# hotfix

Fast, bounded patch path for a defect in an already-released version. Unlike normal work (which branches off `develop`), a hotfix branches off the **released tag** so the fix ships without pulling in unreleased `develop` changes. Every release action is destructive — **pause for explicit approval before tagging**.

## When to use

- A shipped release (`vX.Y.Z`) has a user-affecting bug or a broken artifact, and waiting for the next normal release is not acceptable.
- For non-urgent defects, use the normal `start-work` → delivery loop off `develop` instead.

## Steps

1. **Branch off the released tag** (not `develop`): `git checkout -b hotfix/<id> vX.Y.Z`.
2. **Reproduce + failing-first test.** Add a regression test that fails on the current code (per `testing-standards-06`; bug fixes require a failing-first test). Use `systematic-debugging`.
3. **Apply the minimal fix.** Smallest change that resolves the defect — no scope creep, no unrelated refactors.
4. **Bump the PATCH version** in all locations (canonical `src/app.py` `APP_VERSION`; verify with `scripts/check-version-sync.sh`). `vX.Y.Z` → `vX.Y.(Z+1)`.
5. **Update CHANGELOG + release notes.** Add `## [X.Y.(Z+1)]` with the fix; write `docs/releases/RELEASE_NOTES_vX.Y.(Z+1).md`.
6. **Fast-tracked quality gate.** Run `quality-gate` (version-sync, black, flake8, mypy, pytest with the coverage floor). Must be green; route failures to `remediate-failure`.
7. **Approval gate.** Present a concise brief (defect, fix, blast radius, test) and **pause for explicit approval** before releasing.
8. **Release the patch.** Merge `hotfix/<id>` → `main`, tag `vX.Y.(Z+1)`, push (triggers `build-release.yml`); verify the run is green and the `.dmg`/`.zip` attach (as in `ship-release`).
9. **Back-merge** the fix into `develop` (and confirm `main` is current) so the patch is not lost on the next release: `git checkout develop && git merge main`, push.
10. **Record + announce.** Log in `docs/DECISIONS.md`, `update-tracker`, and post success comms (Slack + Confluence draft-then-confirm).

## Leverages

Rules: `release-packaging-12`, `change-control-07`, `testing-standards-06`. Skills: `quality-gate`, `ship-release`, `remediate-failure`, `rollback`, `update-tracker`, `publish-docs`.

## Completion checklist

- [ ] Branched off the released tag, not `develop`
- [ ] Failing-first regression test added; minimal fix applied
- [ ] PATCH version bumped everywhere (version-sync green); CHANGELOG + release notes written
- [ ] Gate green; approval obtained before tag
- [ ] Patch tagged + released; artifacts attached
- [ ] Fix back-merged to `develop`; recorded + announced
