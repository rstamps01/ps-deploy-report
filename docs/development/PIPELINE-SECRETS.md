# Pipeline Secrets & Credentials Registry

Single reference for every secret the project and its agentic CI/CD pipeline use,
where each one is set, and how it is kept out of git. Aligns with
[`.cursor/rules/config-security-11.mdc`](../../.cursor/rules/config-security-11.mdc)
and the pipeline plan §19.

> **Golden rule:** secrets are **never** committed. They live only in a local,
> gitignored `.env`, in the OS environment, in GitHub Actions repository secrets,
> or in an MCP auth store. The gitleaks pre-commit hook + `.cursor/hooks/guard-git.sh`
> block any credential-shaped string from reaching a commit.

## Where secrets live (four stores, never git)

| Store | Used by | How it is set | Committed? |
| --- | --- | --- | --- |
| **Local `.env`** (gitignored) | run-from-source app + local pipeline runs | `python-dotenv` loads it; or plain `export` in the shell | No (`.env` is gitignored) |
| **OS environment variables** | app runtime, `src/utils/notifier.py`, `gh` CLI | `export VAR=...` / launchd / systemd / CI shell | No |
| **GitHub Actions repository secrets** | CI/build-release workflows | repo **Settings → Secrets and variables → Actions** | No (masked in logs) |
| **MCP auth store** | Atlassian, Slack, GitLens MCP tools | the plugin OAuth/login flow (`mcp_auth`) | No |

## Secrets registry

Values are illustrative names only — **never** the value itself.

| Secret | Purpose | Scope / where set | Consumed by | Notes |
| --- | --- | --- | --- | --- |
| `VAST_API_TOKEN` | VAST cluster API token auth | env / `.env` (local run) | `api_handler` | In-memory only; destroyed after session |
| `VAST_USERNAME` / `VAST_PASSWORD` | Cluster username/password auth | env / `.env` / `getpass` prompt | `api_handler` | Prefer token; password is fallback |
| `VAST_NODE_USER` / `VAST_NODE_PASSWORD` | SSH to cluster nodes (health checks, tiers 2–3) | env / `.env` / prompt | `utils/ssh_adapter`, `health_checker` | Never logged (sanitized) |
| `VAST_SWITCH_USER` / `VAST_SWITCH_PASSWORD` | SSH to fabric switches | env / `.env` / prompt | `utils/switch_ssh_probe`, workflows | Never logged (sanitized) |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Pipeline escalation email (SMTP app-password) | env / `.env` | `src/utils/notifier.py` | App-password (Gmail/O365); non-SMTP config (host/port/recipient) lives in `config.yaml` `notifications:` |
| Slack auth | Escalation post + threaded reply, release comms | **MCP auth store** (Slack plugin) | Slack MCP tools (`slack_send_message`, `slack_read_thread`) | Interactive OAuth via `mcp_auth`; no token in repo. A raw `SLACK_BOT_TOKEN` is only needed for a non-MCP fallback and would live in env/CI secrets |
| Atlassian auth | Confluence publish (`publish-docs`), optional Jira | **MCP auth store** (Atlassian plugin) | Atlassian MCP tools | Interactive OAuth via `mcp_auth` |
| `GITHUB_TOKEN` / `gh` auth | Release publish, PR/issue ops, `gh run` queries | `gh auth login` (local) / auto-injected `GITHUB_TOKEN` (Actions) | `ship-release`, `open-pr`, CI | In Actions this is the built-in job token; no manual secret needed for same-repo ops |
| `CURSOR_API_KEY` (optional) | Cursor SDK / headless agent runs, if used | env / CI secret | SDK automations | Only if the SDK/CI automation path is enabled |

## Rules for adding a new secret

1. Add it to this registry table (name + purpose + store + consumer) — **value never committed**.
2. If it is an env var the app reads, document it in `config-security-11.mdc` and `README.md`.
3. If a **non-secret** companion setting exists (host, port, recipient, channel), put that in
   `config/config.yaml.template` (committed) — keep the secret out.
4. Confirm `.gitignore` covers any file it could land in (`.env`, `config/config.yaml`).
5. For CI, add it as a GitHub Actions repository secret and reference it as `${{ secrets.NAME }}`
   (never echo it; Actions masks known secrets automatically).

## Attack-surface notes (notifier / Slack / Confluence)

The escalation + docs-publishing surfaces handle untrusted-ish content (failure text,
logs, diffs) and outbound credentials. Key controls already in place, plus the standing
review checklist, are documented in
[`AGENTIC-CICD-PIPELINE.md`](AGENTIC-CICD-PIPELINE.md) and enforced by `src/utils/notifier.py`:

- **Redaction:** all escalation text is passed through the shared `SensitiveDataFilter`
  regex (password/token/secret/credential/authorization) before it is emailed or posted,
  so logs folded into a notification cannot leak a credential.
- **Credentials via env only:** `notifier.py` reads `SMTP_USERNAME`/`SMTP_PASSWORD` from
  the environment — never from `config.yaml`, never hardcoded.
- **No untrusted execution:** notifications are plain text/records; no template that
  evaluates user/log content as code. Confluence/Slack publishing **pauses for human
  confirmation** before anything customer/exec-facing is written.
- A formal `security-review` subagent pass over this surface can be run on request
  (template-injection into emails, credential handling, SSRF via configured SMTP host).

## Related

- Rule: [`config-security-11.mdc`](../../.cursor/rules/config-security-11.mdc) — credential handling, env-var table, SSL/TLS.
- Config: [`config/config.yaml.template`](../../config/config.yaml.template) — non-secret `notifications:` block.
- Code: [`src/utils/notifier.py`](../../src/utils/notifier.py) — escalation email/Slack with redaction.
