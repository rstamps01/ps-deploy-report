### Changed
- **Developer workflow (PIPE-T1):** plain `pytest` runs no longer collect coverage; the 60% floor is enforced by `bash scripts/quality-gate.sh` (new one-call local gate) and CI. CI writes a JUnit failure summary to each job and no longer re-runs the health-check and Advanced Operations tests in separate jobs. Release history for v1.5.8 and earlier moved to `docs/CHANGELOG-ARCHIVE.md`.
