---
name: rollback
description: Revert a bad release by re-pointing the GitHub "latest" release to the prior good tag and/or replacing a broken artifact, then documenting how users downgrade. Use as the FIRST option when a post-release smoke test or field report shows a release is broken. Requires explicit approval before changing published releases.
disable-model-invocation: true
---

# rollback

Restore users to a known-good release quickly. Rollback is the **first** option offered when a post-release smoke test fails (a hotfix is the second) because it is fast and low-risk: it re-points "latest" rather than shipping new code. Changing published releases is user-visible — **pause for explicit approval** before acting.

## When to use

- A just-shipped release (`vX.Y.Z`) is broken (failed post-release smoke test, corrupt/missing artifact, or a severe field-reported regression) and the prior release (`vX.Y.(Z-1)` or last good tag) is known good.
- Prefer rollback first; if the defect is small and well-understood, `hotfix` may be preferable — the `remediate-failure` loop chooses.

## Steps

1. **Identify the last good tag.** `gh release list` / `git tag --sort=-creatordate`; confirm the prior release’s artifacts are intact (`gh release view <good-tag>`).
2. **Re-point "latest".** Mark the good release latest and the bad one not-latest:
   - `gh release edit <good-tag> --latest`
   - `gh release edit vX.Y.Z --latest=false` (optionally `--prerelease` to demote, or add a "⚠️ withdrawn — use <good-tag>" note to its body).
3. **Replace/remove broken artifacts** if the code is fine but an asset is bad: `gh release delete-asset` / `gh release upload` the corrected artifact (or rebuild via a re-cut tag).
4. **Document the downgrade path** for users: which release to install, and any config/data caveats when moving back a version (tie to the `prepare-release` config-migration notes).
5. **Do NOT delete the bad tag/commit** — keep history. Leave the bad release published-but-not-latest with a clear warning so links don’t 404.
6. **Feed the remediation loop.** Record the incident in `docs/DECISIONS.md` + tracker; open a `fix/`/`hotfix/` item to actually resolve the defect. Route through `remediate-failure` so the fix is bounded and escalated if needed.
7. **Announce.** Post the rollback (Slack + Confluence draft-then-confirm): what broke, current recommended version, ETA on the fix.

## Leverages

Rules: `release-packaging-12`, `change-control-07`. Skills: `remediate-failure`, `hotfix`, `publish-docs`, `update-tracker`.

## Completion checklist

- [ ] Last good tag confirmed (artifacts intact)
- [ ] "latest" re-pointed to the good release; bad release demoted + annotated (not deleted)
- [ ] Broken artifacts replaced/removed if applicable
- [ ] Downgrade path documented; incident recorded + fix item opened
- [ ] Rollback announced
