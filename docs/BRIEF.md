# asbuilt-reporter brief (generated 2026-11-10; keep under 2.5 KB; replace, don't append)

Goal: field-ready as-built PDF/JSON reports and post-install validation for VAST clusters.
Phase: v1.6.2 shipped (2026-10-17); v1.6.3 in planning | Version: 1.6.2 | CI on `develop`: green (2026-11-09)

## Next 3
1. FR-16 (P0, v1.6.3 blocker): vperfsanity Step 4 output stalls, then floods and freezes Chrome. Spec: `docs/issues/FR-16/spec.md`.
2. v1.6.3 scope: TP-4, FR-7–15, OBS-1, TP-3, HUB-1–9, DATA-1 (see `docs/TODO-ROADMAP.md` Next steps).
3. PIPE-T4: re-measure PIPE-T1 KPIs on 2026-11-24 (`docs/issues/PIPE-T1/spec.md`). PIPE-T1 merged in #44.

## Open PRs / waiting
- Dependabot #31 (ReportLab 5, held: title-with-table layout needs 4.4 splitting), #40–#43.
- v1.6.2 ship leftovers needing approval: live UPDATE AVAILABLE check from a real 1.6.1 install; Confluence, Slack and GOV-3 advisory posts.

## Recent decisions (`docs/DECISIONS.md`, top entries)
- 2026-11-10 PIPE-T1 token-efficiency trim (merged #44); thread-length handoff policy.
- 2026-10-17 v1.6.2 shipped; 2026-10-16 v1.6.2 scope and product rename to asbuilt-reporter.
- 2026-09-26 Results Hub architecture (separate repos).

## Where history lives
`docs/TODO-ROADMAP.md` (live register; Grep it), `docs/ROADMAP-ARCHIVE.md`, `CHANGELOG.md` (v1.6.x) and `docs/CHANGELOG-ARCHIVE.md`, `docs/DECISIONS.md` (read single entries), `docs/PROJECT-STATUS.md`. Code and git outrank this brief.
