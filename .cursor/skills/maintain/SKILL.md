---
name: maintain
description: Ongoing repository maintenance — triage Dependabot/dependency PRs through the full gate, post success comms on a good release (Slack + Confluence draft), and ship config migrations when config keys change. Use for routine upkeep between feature work, on a Dependabot PR, or as part of a release.
disable-model-invocation: true
---

# maintain

Routine upkeep that keeps the repo healthy between feature work. Three concerns (§28); do the one the situation calls for.

## A. Dependency updates (Dependabot triage)

1. List open dependency PRs: `gh pr list --label dependencies` (Dependabot is configured in `.github/dependabot.yml` for pip + actions).
2. For each: read the changelog/release notes for **breaking changes**; check the version jump (patch/minor/major).
3. Run the **full quality gate** against the PR branch (`quality-gate`: version-sync, black, flake8, mypy, pytest with coverage floor). Security-sensitive bumps also get a `security-review` pass.
4. **Merge** if green and low-risk (patch/minor, no breaking changes). **Escalate** (route to `remediate-failure` / flag for human) if the gate fails, a major bump needs code changes, or a breaking change is involved.
5. Keep `requirements*.txt` current and **pinned**; never leave an unpinned or partially-upgraded dependency set. Record notable upgrades in `CHANGELOG.md`.

## B. Success / stakeholder comms (not only failures)

On a **successful** release (invoked from `ship-release`/`hotfix` step "announce"):

1. Post a Slack announcement via the Slack MCP (`slack_send_message`): version, headline changes, artifact links. Keep it concise and factual.
2. Draft a Confluence release page/update (Atlassian MCP `updateConfluencePage` on page `6664028496`) — **draft-then-confirm**: present the draft and get explicit approval before publishing.
3. Redact any secrets from comms via the existing `SensitiveDataFilter` conventions — never paste tokens/creds/log excerpts with credentials.

## C. Config / data migration

When config keys change (e.g. the `notifications:` block, or any new `config.yaml` key):

1. Add the new keys to `config/config.yaml.template` (the only tracked config) and document them in `README.md` (per `config-security-11`).
2. Ship a safe **migration/backfill**: on startup the app copies missing keys from the template into the user’s existing `config.yaml` without clobbering their values (deep-merge, not overwrite).
3. Add the migration to the `prepare-release` checklist so upgrading users are handled every release. Cover it with a test.

## Leverages

Rules: `ci-pipeline-13`, `config-security-11`, `documentation-08`, `change-control-07`. Skills: `quality-gate`, `remediate-failure`, `open-pr`, `publish-docs`, `prepare-release`, `update-tracker`. MCPs: Slack, Atlassian.

## Completion checklist

- [ ] (A) Dependency PRs gated + merged/escalated; requirements pinned
- [ ] (B) Success comms posted (Slack) + Confluence draft confirmed before publish
- [ ] (C) New config keys in template + README; non-clobbering migration shipped + tested
