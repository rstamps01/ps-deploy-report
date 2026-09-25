# Project Plan Archive

Versioned, redacted copies of the Cursor plans that belong to this project. Cursor writes plan files to `~/.cursor/plans/`, which is local to one machine, shared by every project, and not under version control. This folder is the durable record: use it to trace past activity and to audit whether each plan was fully implemented or still has open work.

**Status of each plan** (shipped, superseded, residual tail, open) lives in [`../PLANS-INDEX.md`](../PLANS-INDEX.md), not here. The archived copies keep the plan's original frontmatter, so a `pending` todo in a copy does not by itself mean the work is outstanding. The audit is roadmap item PLN-1.

## Contents

- `*.plan.md` — one file per plan, same filename as in `~/.cursor/plans/`.
- [`MANIFEST.txt`](MANIFEST.txt) — the allow-list of plans that belong to this repo, plus the `last-triaged` date. Plans from other projects that share the Cursor plans directory are never copied.

## Redaction

The repository is public, so every copy passes through the redaction in [`scripts/sync-cursor-plans.py`](../../scripts/sync-cursor-plans.py) before it lands here:

| Replaced | With |
|----------|------|
| Host IPv4 addresses. Loopback, `0.0.0.0`, the documented Tech Port address `192.168.2.2`, and network ranges such as `10.0.0.0/8` are kept. | `<ip>` |
| Values after `password`/`token`/`secret`/`api_key`-style keys. Code expressions such as `password: str` are kept. | `<redacted>` |
| Email addresses | `<email>` |
| Lab hostnames and clusters, customer cluster and site names, and factory-default passwords (the `REDACT_PATTERNS` list) | `<lab-host>`, `<lab-cluster>`, `<customer-cluster>`, `<customer-site>`, `<customer>`, `<default-password>` |

If a plan still identifies a customer after redaction, remove it from `MANIFEST.txt` and keep it local. Add a new name to `REDACT_PATTERNS` when a sync report or review turns one up.

## Keeping it current

```bash
python3 scripts/sync-cursor-plans.py           # copy new or changed plans (redacted)
python3 scripts/sync-cursor-plans.py --check   # exit 1 on drift or untriaged plans
```

`--check` reports two things:

- **Drift:** an archived copy that no longer matches its redacted source.
- **Untriaged plans:** a plan in `~/.cursor/plans/` modified after the manifest's `last-triaged` date and not listed in the manifest.

To triage a new plan, add it to `MANIFEST.txt` if it belongs to this project, then bump `last-triaged`. If a source plan is deleted locally, its archived copy stays as the record.
