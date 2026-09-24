# GitHub Workflow Runbook

How to respond to the GitHub notifications this repository generates — the "recent pushes" banner, Dependabot pull requests, and red check marks — without breaking the branching model.

Repository: [`rstamps01/ps-deploy-report`](https://github.com/rstamps01/ps-deploy-report). The enforcing standards are [`.cursor/rules/change-control-07.mdc`](../../.cursor/rules/change-control-07.mdc) (branching, commits) and [`.cursor/rules/release-packaging-12.mdc`](../../.cursor/rules/release-packaging-12.mdc) (versioning, release artifacts). This document is the operational companion: what to click, what to type, and what to ignore.

## Quick reference

| I see this | Do this |
| --- | --- |
| Banner: **"develop had recent pushes… Compare & pull request"** | **Dismiss it.** `develop → main` only happens at release time. Clicking it would propose shipping unreleased work. |
| Banner: **"feature/x had recent pushes… Compare & pull request"** | **Act on it** — open the PR, but confirm the base is `develop`, not `main`. |
| Dependabot PR, CI green, minor/patch bump | `gh pr merge N --squash --delete-branch` |
| Dependabot PR, major bump | Read the changelog for breaking changes affecting *our* usage before merging. |
| Dependabot PR touching one half of a coupled pair (e.g. Pages actions) | Close it with an explanatory comment; bump both halves manually in a `fix/*` branch. |
| Dependabot PR, CI red | Diagnose the failure first: `gh pr checks N`. Never merge red. |
| Red X on a `main` commit that you believe passed | Likely a cancelled `develop` check-suite on the same SHA — see [Cancelled runs showing red on main](#cancelled-runs-showing-red-on-main). |
| Weekly "Security Audit: Vulnerabilities detected" issue | Opened by [`security.yml`](../../.github/workflows/security.yml) on Mondays. Triage the run artifacts; close when resolved. |

## 1. The branching model in one paragraph

`main` is protected and holds tagged releases only. `develop` is the integration branch where everything lands first. Day-to-day work happens on `feature/<name>` or `fix/<name>` branches cut from `develop`. Releases merge `develop → main`, then get tagged `vX.Y.Z`. **Never commit directly to `main`.**

Actual protection state (verify with `gh api repos/rstamps01/ps-deploy-report/branches/main/protection`):

- `main` requires these status checks to pass: `quality-gate`, `unit-tests (3.11)`, `unit-tests (3.12)`, `integration-tests`. Force pushes and deletion are blocked.
- `develop` is **not** branch-protected. Nothing mechanically stops a bad merge there, so the review discipline below is the only gate.

## 2. The "develop had recent pushes" banner

**What it is:** GitHub shows this banner on the repo home page after any push to a non-default branch, offering to open a pull request from that branch into the default branch (`main` here). It is a generic UI affordance, not a signal that anything needs doing.

**Why it is usually noise here:** `develop` receives pushes constantly. In this model `main` receives a merge only at release time, after the version bump and changelog are prepared. Clicking **Compare & pull request** on the `develop` banner proposes exactly the merge you do *not* want mid-cycle: every unreleased commit on `develop` going to `main`. Dismiss the banner (the `x` on its right) and move on. It reappears on the next push; that is expected.

**When the banner is meaningful:** when the branch named in it is a `feature/*` or `fix/*` branch you just pushed. That is real work waiting for integration. Act on it, but **check the base branch** — GitHub defaults the base to `main`, which is wrong for this repo:

```bash
# Open a PR from the current feature/fix branch into develop (correct base)
gh pr create --base develop --fill

# If a PR was already opened against the wrong base, retarget it
gh pr edit <N> --base develop
```

**When the `develop` banner IS the right thing to click:** only when you are deliberately starting a release. See [Release flow](#5-release-flow-brief).

## 3. Dependabot

### How it is configured

From [`.github/dependabot.yml`](../../.github/dependabot.yml) — two ecosystems, both weekly on Monday at 09:00 UTC, both capped at 5 open PRs:

| Ecosystem | Target branch | Limit | Commit prefix | Grouping |
| --- | --- | --- | --- | --- |
| `pip` | `develop` | 5 | `chore(deps)` | `python-minor-patch` group for `minor` + `patch` update types |
| `github-actions` | `develop` | 5 | `chore(ci)` | **none** |

Two things follow from this configuration:

1. **`target-branch: develop`** is the important one. Dependabot PRs base onto `develop`, never `main`, so dependency bumps flow through the same integration branch as everything else and reach `main` only via a release. This is correct and should not be changed.
2. **The `github-actions` ecosystem has no `groups:` key**, so every action version bump arrives as its own pull request. That is why a single Monday run produced a wall of PRs (`actions/checkout`, `actions/setup-python`, `actions/cache`, `actions/upload-pages-artifact`, `softprops/action-gh-release`, …) rather than one batched PR. The `pip` side declares a group, but bumps that are major, or that arrive alone in a cycle, still land as individual PRs — expect a mix.

### Known config wart

Dependabot comments on each PR that it cannot apply the configured labels:

> The following labels could not be found: `ci`, `dependencies`.

The repo's label set does not include them (`gh label list`). Harmless, but it adds a comment — and therefore a notification — to every Dependabot PR. Fix once:

```bash
gh label create dependencies --color 0366d6 --description "Dependency updates"
gh label create ci --color bfd4f2 --description "CI / workflow changes"
```

## 4. Working through a Dependabot backlog

### 4.1 See what is open

```bash
gh pr list --state open --limit 30 \
  --json number,title,baseRefName,author \
  --jq '.[] | "\(.number)\t\(.baseRefName)\t\(.title)"'
```

Confirm the `baseRefName` column reads `develop` for every Dependabot PR. If one bases onto `main`, something is misconfigured — stop and check `dependabot.yml`.

### 4.2 Check CI on one PR

```bash
gh pr checks 12                # per-check status for PR 12
gh pr view 12 --json statusCheckRollup --jq '.statusCheckRollup[] | "\(.name): \(.conclusion)"'
```

### 4.3 Review what actually changed

```bash
gh pr diff 12                  # the requirements.txt / workflow diff — usually one line
gh pr view 12                  # Dependabot's body includes the upstream release notes
```

**Review criteria, in order:**

1. **Is CI green?** No exceptions. A red Dependabot PR means the bump breaks us; that is the whole point of running CI on it.
2. **Is it a major version bump?** Major bumps (`pytest-cov 4 → 7`, `actions/checkout 4 → 7`) need the changelog read. The question is never "did upstream have breaking changes" but "did they break something *we use*". A breaking change in an API we never call is irrelevant.
3. **Is this dependency coupled to another?** See §4.5. Dependabot evaluates one dependency at a time and cannot see pairings. This is the reviewer's job and the most common way a green Dependabot merge causes damage.
4. **Does it touch release-critical machinery?** Bumps to actions used in [`build-release.yml`](../../.github/workflows/build-release.yml) (`softprops/action-gh-release`, `actions/upload-artifact`, `actions/download-artifact`) affect whether release assets get attached at all, and that path is only exercised on a tag push — CI passing does not prove the release path still works. Merge these, then watch the next release closely.

### 4.4 Merge

```bash
gh pr merge 12 --squash --delete-branch
```

Squash keeps `develop` history to one commit per bump, and `--delete-branch` clears the `dependabot/*` remote branch so it stops showing in `git branch -a`. To work through a verified-green batch:

```bash
for n in 7 8 9 11 12 13; do gh pr merge "$n" --squash --delete-branch; done
```

Only do this after checking each one individually — the loop is for the merge step, not the review step.

### 4.5 Close a PR that should not be merged

```bash
gh pr close 10 --comment "Closing in favor of a paired bump. <reason>"
```

Always leave the reason in the comment. Dependabot will not reopen a closed PR for the same version, and a future reader (or you, in three months) needs to know whether it was rejected or merely deferred. Dependabot replies confirming it will not re-notify for that version.

## 5. Case study: PR #10, and why one-at-a-time bumps are dangerous

Dependabot opened [PR #10](https://github.com/rstamps01/ps-deploy-report/pull/10), "Bump `actions/upload-pages-artifact` from 3 to 5". CI was green. Merging it would have been wrong.

[`.github/workflows/pages.yml`](../../.github/workflows/pages.yml) uses two GitHub Pages actions that form a **matched pair**:

```yaml
- uses: actions/upload-pages-artifact@v5   # build job
...
- uses: actions/deploy-pages@v5            # deploy job
```

The Pages artifact format changed between action generations. Upgrading only the upload half while `deploy-pages` stayed on the older major produces a workflow that **reports success while deploying an empty site** — the deploy step finds no artifact it recognises, and neither action treats that as an error. Nothing in CI catches this: the Pages workflow only runs on pushes to `main` under `docs/marketing/**`, and its failure mode is a green check with a blank site.

Dependabot has no model of this coupling. It sees one dependency, finds a newer version, and opens a PR. **The reviewer owns cross-dependency coupling.** PR #10 was closed with an explanation and both actions were bumped together in the `fix/v1.6.1-docs-ci-ui` branch.

Generalised rule: before merging any action or library bump, ask whether the thing being bumped has a counterpart that must move with it. Common pairs in this repo:

- `actions/upload-pages-artifact` ↔ `actions/deploy-pages` (`pages.yml`)
- `actions/upload-artifact` ↔ `actions/download-artifact` (`build-release.yml` passes artifacts between jobs)
- `pytest` ↔ `pytest-cov` (plugin API compatibility)

## 6. Release flow (brief)

Once `develop` is green and the release content is ready, this is when the `develop → main` merge is correct. Full procedure and the version-location table are in [`.cursor/rules/release-packaging-12.mdc`](../../.cursor/rules/release-packaging-12.mdc) — do not duplicate it, follow it. The shape:

1. Bump the version. `APP_VERSION` in `src/app.py` is canonical (currently `1.6.1`); every other location derives from it and `scripts/check-version-sync.sh` fails CI if they drift.
2. Update `CHANGELOG.md`; add `docs/releases/RELEASE_NOTES_vX.Y.Z.md` if the release warrants notes (the release workflow uses it as the release body, falling back to `CHANGELOG.md`).
3. Merge `develop → main` and push.
4. Tag and push the tag:

```bash
git tag -a v1.6.1 -m "Release v1.6.1 — short description"
git push origin v1.6.1
```

5. [`build-release.yml`](../../.github/workflows/build-release.yml) fires on the `v*` tag, runs the blocking quality-gate and test jobs against the tagged commit, then builds **three artifacts** and attaches them to the GitHub Release: `VAST-Reporter-vX.Y.Z-mac-arm64.dmg`, `VAST-Reporter-vX.Y.Z-mac-x64.dmg`, and `VAST-Reporter-vX.Y.Z-win.zip`.

```bash
gh run list --workflow build-release.yml --limit 3
gh release view v1.6.1
```

## 7. Cancelled runs showing red on main

**Symptom:** immediately after a release, `main`'s commit shows a red X even though `main`'s own CI passed and the release built fine.

**Cause:** GitHub attaches check-suites to a **commit SHA**, not to the branch that triggered them. At release time the same commit exists on `develop`, on `main`, and on the tag simultaneously. Every check-suite that ever ran against that SHA — including one triggered by the earlier `develop` push — is displayed on `main`'s commit. A `develop` run that was *cancelled* because a newer `develop` push superseded it therefore renders as a failure badge on `main`.

**Diagnose:**

```bash
SHA=$(git rev-parse main)
gh api repos/rstamps01/ps-deploy-report/commits/$SHA/check-suites \
  --jq '.check_suites[] | "\(.app.slug)\t\(.head_branch)\t\(.status)\t\(.conclusion)"'
```

If the offending row reads `github-actions  develop  completed  cancelled`, this is the false alarm — not a real failure.

**Fixes already applied:**

- [`ci.yml`](../../.github/workflows/ci.yml) no longer cancels in-progress runs on `main`:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

  Superseded runs are still cancelled on `develop` and feature branches (that is the cost saving), but a `main` run always completes so the released commit carries a real conclusion.

- A stale cancelled suite can be cleared by re-running it:

```bash
gh run list --limit 10 --json databaseId,name,headBranch,conclusion,headSha
gh run rerun <run-id>
```

## 8. Notification hygiene

- **Watch settings.** On the repo page, **Watch → Custom** and deselect what you do not act on. Keeping *Pull requests* and *Issues* while dropping *Actions* removes most of the volume — a failing workflow on your own branch still surfaces in `gh run list` and on the PR.
- **Create the missing labels** (§3) to stop Dependabot commenting on every PR it opens.
- **Consider grouping the `github-actions` ecosystem** the way `pip` already is. Adding a `groups:` key to the `github-actions` entry in `dependabot.yml` would collapse a Monday's action bumps into one PR instead of five:

```yaml
    groups:
      github-actions:
        update-types:
          - "minor"
          - "patch"
```

  Tradeoff: a grouped PR is merged or closed as a unit, so a single bad bump in the group blocks the rest. Given that action bumps here are routine and CI-verified, batching is likely the better default — but it is a config change and should go through a `fix/*` branch and PR like anything else.
- **Do not let the backlog build.** Dependabot caps each ecosystem at 5 open PRs; once the cap is hit it silently stops proposing new updates, so an ignored backlog quietly turns into missed security patches.
