# asbuilt-reporter brief (generated 2026-11-11; keep under 2.5 KB; replace, don't append)

Goal: field-ready as-built PDF/JSON reports and post-install validation for VAST clusters.
Phase: v1.6.2 shipped (2026-10-17); v1.6.3 in progress | Version: 1.6.2 | CI on `develop`: green (2026-11-11)

## Next 3
1. v1.6.3: start from `docs/issues/v1.6.3/handoff.md`. Wave A in review (#52 FR-11, #53 FR-10, #54 TP-4, #55 HCF-3); then OBS-1 after HCF-3 and FR-7 after FR-10.
2. NET-7: N1–N6 committed on `feature/NET-7-vnetmap-lldp` (`~/asbuilt-net7`); parent integration N7–N10 (extractor, Reporter/One-Shot wiring, report text, UI/config) next.
3. Lab gates before the v1.6.3 cut: FR-16 T8, FR-7, NET-7 on a cluster with LLDP active, TP-3 (owner deciding).

## Open PRs / waiting
- v1.6.3: #52–#55 awaiting review/merge to `develop`.
- Dependabot #31 (ReportLab 5, held: title-with-table layout needs 4.4 splitting), #40–#43.
- v1.6.2 ship leftovers needing approval: live UPDATE AVAILABLE check from a real 1.6.1 install; Confluence, Slack and GOV-3 advisory posts.

## Recent decisions (`docs/DECISIONS.md`, top entries)
- 2026-11-11 v1.6.3 scope: critical fixes + NET-7 in one release; HCF-3 moved in; FR-8/9/13–15, HUB-1–9, DATA-1 to v1.7.0.
- 2026-11-10 PIPE-T1 token-efficiency trim (merged #44); thread-length handoff policy.
- 2026-10-17 v1.6.2 shipped.

## Where history lives
`docs/TODO-ROADMAP.md` (live register; Grep it), `docs/ROADMAP-ARCHIVE.md`, `CHANGELOG.md` (v1.6.x) and `docs/CHANGELOG-ARCHIVE.md`, `docs/DECISIONS.md` (read single entries), `docs/PROJECT-STATUS.md`. Code and git outrank this brief.
