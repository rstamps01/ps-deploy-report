# TP-4 — Results page cluster filter returns every Tech Port cluster

**Type:** Bug · **Priority:** P2 · **Target:** v1.6.3 · **Status:** Planned (logged 2026-10-16)

## Observed

On the Results page, filtering by one cluster that was reported through the Tech Port also lists the
results of every other cluster reported through the Tech Port, and filtering by any of those clusters
lists the first one's results. Seen in the field with four clusters, all connected via the Tech Port.

## Expected

Filtering by a cluster lists only that cluster's results, however it was connected (Tech Port, VMS
HTTPS or Teleport).

## Root cause (from code reading)

- `frontend/templates/validation_results.html` builds the cluster dropdown from saved profiles with
  `value="{{ prof.cluster_ip }}"`, and the page requests
  `/validation-results/api/results?cluster_ip=<value>`.
- `src/app.py` (`/validation-results/api/results`) passes that IP to `ResultScanner.scan_all(cluster_ip=...)`,
  which matches results by `cluster_ip`.
- Every Tech Port profile stores `cluster_ip = 192.168.2.2`, so the filter matches every Tech Port cluster.
- `ResultScanner.get_known_clusters()` already identifies clusters by `cluster_key` (the per-cluster
  `clusters/<key>/` folder from QP-2) and warns in its docstring that two Tech Port clusters must never be
  grouped by IP alone. The filter path was not moved to the same identity.

## Why

The Results page is how engineers pick a cluster's report, bundle and Test Suite output to hand over.
Mixing clusters risks sending one customer another customer's artifacts.

## Capabilities

- The dropdown lists clusters by identity (`cluster_key`), labelled with the cluster name and IP.
- The results API accepts `cluster_key` and scans only that cluster's folder.
- Results from the legacy flat layout that carry only `192.168.2.2` are not attributed to any one
  Tech Port cluster; they appear under an "Unassigned (legacy)" entry.
- `cluster_ip` stays accepted for non-Tech-Port clusters and old bookmarks.

## Constraints

- Keep the legacy flat-tree read path (QP-2 backward compatibility).
- No customer identifiers in fixtures or docs (the repository is public).

## Non-goals

- Resolving the real management IP during Tech Port discovery (TP-3).
- Re-filing old flat-layout artifacts into per-cluster folders.

## Acceptance criteria

- GIVEN two clusters with different `cluster_key` values that were both reported through `192.168.2.2`
  WHEN the Results page is filtered to the first cluster
  THEN only the first cluster's reports, health checks, workflow outputs and bundles are listed, and the reverse holds.
- GIVEN a VMS-HTTPS cluster WHEN filtered by its IP THEN results are unchanged from today.
- GIVEN flat-layout files with `cluster_ip = 192.168.2.2` WHEN any Tech Port cluster is selected THEN those files are not listed.
- A failing-first regression test in `tests/test_result_scanner.py` (or the route test) pins the two-cluster case.

## Success signal

Filtering by any one of several Tech Port clusters in the field lists only that cluster's artifacts.
