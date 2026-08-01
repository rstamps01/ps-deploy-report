---
name: remediate-failure
description: Run a bounded assess -> troubleshoot -> solve -> re-run loop (max 3 attempts per issue) when a gate fails, then escalate to a human via SMTP email + Slack with up to 4 ranked options and drive a reply-triggered 2nd loop. Use when quality-gate, CI, a blocking build-release, functional-validate, or a QA/regression check fails and needs automated remediation.
disable-model-invocation: true
---

# remediate-failure

Bounds the "iterate-until-green" behavior so the pipeline neither ships red nor thrashes forever. Composes the local `iterative-improvement-loop` (its `stop.maxCycles` = the 3-attempt bound), `systematic-debugging`, and `dispatching-parallel-agents`. Enforces `ci-pipeline-13`.

## When it triggers

Any failed gate: `quality-gate`, CI (`ci.yml`), a blocking `build-release`, `functional-validate`, or a QA/regression check. Also invoked when two independent-reviewer REJECTs stack up in `implement-change`/`open-pr`.

## Bounded loop (max 3 attempts on the SAME issue)

For each distinct failing issue:

1. **Classify** the failure: lint / type / test / build / security / runtime.
2. **Root-cause** via a FRESH subagent (independent of the code author): `ci-investigator` for CI failures; `explore`/`generalPurpose` for local. State a written hypothesis.
3. **Fix** per `systematic-debugging` + TDD (failing-first test for a real defect; do not delete/skip a legit test to go green).
4. **Re-run** the exact failed gate.
   - Pass → resume the pipeline (return to the calling stage).
   - Fail, attempt < 3 → loop back to step 1 with the new evidence.
   - Fail, attempt = 3 → **stop and escalate**.

Log every attempt (hypothesis, change, result) to `docs/issues/<ID>/` and the memlog (`docs/DECISIONS.md`). Do not exceed the per-loop wall-clock/turn/cost budget (§21/§22) — budget exhaustion escalates early.

## Do not remediate nondeterminism

A failure that passes on re-run is **flaky**, not a defect: mark `@pytest.mark.flaky`, quarantine it from the blocking gate, and file it as a BUG (test-reliability policy). The loop never burns attempts on flakiness.

## Escalation (after 3 failed attempts)

Build a structured escalation and deliver it on both channels via `src/utils/notifier.py`:

1. **Compose** an `EscalationReport(gate, summary, root_cause, actions_taken, options)` — (1) failure description, (2) root-cause assessment, (3) actions taken across the 3 attempts, (4) **up to 4 ranked next-step options with pros/cons**. Secrets are auto-redacted by the notifier.
2. **Email (formal record):** `Notifier(cfg).send_email(report)` (SMTP; creds from `SMTP_USERNAME`/`SMTP_PASSWORD`). A disabled/misconfigured channel returns a result — never raises.
3. **Slack (interactive reply):** post `notifier.slack_payload(report)["text"]` to the configured channel via the Slack MCP (`slack_send_message`). Mirror the escalation to the tracker.
4. **Reply-driven 2nd loop:** read the Slack thread reply (`slack_read_thread`) to capture the chosen option, then run ONE more bounded (<=3) loop scoped to that path. If it also fails, escalate again and stop — do not loop indefinitely.

## Subagents / MCPs

`ci-investigator`, `explore`, `generalPurpose`; Slack MCP (`slack_send_message` / `slack_read_thread`).

## Leverages

Rules: `ci-pipeline-13`, `config-security-11`. Skills: `iterative-improvement-loop`, `systematic-debugging`, `dispatching-parallel-agents`, `test-driven-development`. Code: `src/utils/notifier.py`.

## Completion checklist

- [ ] Each issue bounded to <= 3 attempts; every attempt logged to the memlog
- [ ] Flaky failures quarantined + filed as BUG, not "fixed"
- [ ] On exhaustion: structured report emailed (SMTP) + posted to Slack, secrets redacted
- [ ] Slack reply captured and drove at most one scoped 2nd loop
- [ ] Outcome (resolved / escalated) recorded in the tracker + `docs/DECISIONS.md`
