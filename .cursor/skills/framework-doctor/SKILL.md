---
name: framework-doctor
description: Score a project's ADF adherence (manifest, hooks, tier skills/docs, skill-conformance, version-sync, ADF-version drift) and emit a compliance score plus remediation list. Use for PM: doctor, portfolio audits, or before/after adopt-existing and update-framework.
disable-model-invocation: true
---

# framework-doctor

Audits one project or the whole portfolio. Read-only — never writes into the target
unless you ask it to `--write` a portfolio markdown report.

## Steps

1. **Single project.** From the ADF repo (or any checkout that has `scripts/framework_doctor.py`):
   ```bash
   python3 scripts/framework_doctor.py --target <repo>
   python3 scripts/framework_doctor.py --target <repo> --json
   python3 scripts/framework_doctor.py --target <repo> --fail-under 90
   ```
2. **Portfolio roll-up.** Reads `~/.cursor/pm/projects.md` and scores every listed repo:
   ```bash
   python3 scripts/framework_doctor.py --portfolio
   python3 scripts/framework_doctor.py --portfolio --write docs/PORTFOLIO.md
   ```
3. **Interpret the score.** 90+ green · 70–89 yellow · <70 red. Each `FAIL` check carries a
   concrete remediation (install skill, fix manifest, run `update-framework`, etc.).
4. **Act.** Prefer composing `adopt-existing` / `update-framework` / `quality-gate` for the
   remediations — do not hand-edit core skills. Record material findings in the project's
   `docs/DECISIONS.md` and refresh the PM registry tier/ADF-version columns.
5. **PM integration.** `PM: doctor <path>` runs step 1; `PM: portfolio` runs step 2 and
   updates `docs/PORTFOLIO.md` (ADF) + the registry notes.

## What it checks

| Check | Weight signal |
| --- | --- |
| Manifest present + `validate --strict` | Gates are describable |
| Hooks (`hooks.json` + `guard-git.sh`) | Guardrails installed |
| `AGENTS.md` | Entry point exists |
| Version sync wired | Releases stay consistent |
| Tier skills + docs present | Matches `adoption_tier` |
| Skill conformance | SKILL.md schema valid |
| CI workflow present | Automated gate exists |
| `adf_version` == framework `VERSION` | No drift |

## Guardrails

- Read-only against the target (no overwrite, no delete).
- Operator skill: lives in ADF; not required on every L1 adopter (L2+ may receive it via
  bootstrap). Portfolio audits always run from ADF.

## Completion checklist

- [ ] Doctor ran against the intended target(s); score + remediations captured
- [ ] Remediations routed to the right skill (`adopt-existing` / `update-framework` / gate)
- [ ] Registry / `docs/PORTFOLIO.md` updated when this was a portfolio run
- [ ] Material findings appended to the relevant `docs/DECISIONS.md`
