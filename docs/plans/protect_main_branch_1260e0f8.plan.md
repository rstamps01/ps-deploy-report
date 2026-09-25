---
name: Protect Main Branch
overview: Configure GitHub branch protection rules for the `main` branch to enforce the documented workflow in change-control-07.mdc, requiring CI status checks and code review before merge.
todos:
  - id: enable-protection
    content: Enable branch protection for main in GitHub Settings > Branches
    status: pending
  - id: add-status-checks
    content: "Add required status checks: quality-gate, unit-tests, integration-tests"
    status: pending
  - id: optional-develop
    content: (Optional) Add lighter protection rules for develop branch
    status: pending
  - id: update-readme
    content: Add Contributing/Development note to README about PR requirements for main/develop
    status: completed
isProject: false
---

# Protect Main Branch in GitHub

## Context

Your [change-control-07.mdc](.cursor/rules/change-control-07.mdc) already documents that `main` should be protected:

```
- `main` — protected, production-ready releases only (tagged)
```

The CI pipeline in [.github/workflows/ci.yml](.github/workflows/ci.yml) provides status checks that can gate merges.

---

## Recommended Protection Rules

### Step 1: Navigate to Branch Protection Settings

1. Go to **GitHub > Settings > Branches**
2. Click **Add branch ruleset** (or **Add rule** for classic protection)
3. Target: `main`

### Step 2: Configure Protection Settings

| Setting                                   | Recommended Value                  | Rationale                                    |
| ----------------------------------------- | ---------------------------------- | -------------------------------------------- |
| **Require a pull request before merging** | Enabled                            | Enforces code review; prevents direct pushes |
| **Require approvals**                     | 1 (minimum)                        | At least one reviewer must approve           |
| **Dismiss stale approvals**               | Enabled                            | New commits require re-review                |
| **Require status checks to pass**         | Enabled                            | CI must pass before merge                    |
| **Require branches to be up to date**     | Enabled                            | Prevents merge conflicts                     |
| **Do not allow bypassing**                | Enabled for all (including admins) | No exceptions for force push                 |
| **Restrict deletions**                    | Enabled                            | Prevents accidental branch deletion          |
| **Block force pushes**                    | Enabled                            | Preserves commit history                     |

### Step 3: Required Status Checks

Add these CI job names from your workflow:

| Status Check        | Purpose                            |
| ------------------- | ---------------------------------- |
| `todo-list-check`   | Ensures roadmap is maintained      |
| `quality-gate`      | Lint, format, type checking        |
| `unit-tests`        | Python 3.11 + 3.12 test matrix     |
| `integration-tests` | Integration test suite             |
| `ui-tests`          | Playwright browser tests           |
| `build-smoke`       | Validates macOS and Windows builds |

**Minimum recommended:** `quality-gate`, `unit-tests`, `integration-tests`

---

## Optional: Protect `develop` Branch

Since `develop` is your primary development branch, consider lighter protection:

| Setting               | Value                        |
| --------------------- | ---------------------------- |
| Require pull request  | Enabled                      |
| Require status checks | `quality-gate`, `unit-tests` |
| Allow force push      | Disabled                     |

---

## Implementation Steps (GitHub Web UI)

1. **Repository > Settings > Branches**
2. **Add branch protection rule**
3. Branch name pattern: `main`
4. Check:

- Require a pull request before merging
- Require approvals: 1
- Require status checks to pass before merging
- Search and add: `quality-gate`, `unit-tests`, `integration-tests`
- Require branches to be up to date before merging
- Do not allow bypassing the above settings
- Restrict deletions

1. **Create** / **Save changes**

---

## README Update

Add a brief note to `README.md` in the Development or Contributing section:

```markdown
### Branch Protection

The `main` and `develop` branches are protected. All changes require:
- A pull request (no direct pushes)
- Passing CI status checks (quality-gate, unit-tests, integration-tests)
- At least one approval for `main`

See [change-control-07.mdc](.cursor/rules/change-control-07.mdc) for the full branching strategy.
```

---

## Verification

After enabling, test by:

1. Creating a branch off `main`
2. Attempting to push directly to `main` (should fail)
3. Opening a PR and verifying status checks appear
4. Confirming merge is blocked until checks pass and approval received
