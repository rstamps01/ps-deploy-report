# Repository Structure

The canonical, streamlined layout for this repository. The enforcing rule is [`.cursor/rules/repo-structure-17.mdc`](../../.cursor/rules/repo-structure-17.mdc); this document is the detailed reference (rationale, the layered `src/` map, and the runtime convention).

Status: the standard is **defined** here. The one-time consolidation that moves existing files into this layout (release notes → `docs/releases/`, CHANGELOG split, untrack `.archive/`, etc.) is tracked as a separate cleanup step in the pipeline plan (§11 structural-consolidation) and is applied as its own reviewable change.

## Top-level layout

```
.
├── README.md                # entry doc
├── CHANGELOG.md             # user-facing change history (Keep a Changelog)
├── AGENTS.md                # agentic pipeline entry point
├── requirements*.txt        # dependencies
├── pyproject.toml           # build/test/tool config
├── .flake8 / .pre-commit-config.yaml / .gitignore / dotfiles
├── src/                     # application code (see layered map below)
├── tests/                   # mirrors src/
├── frontend/                # templates + static assets
├── config/                  # runtime config (gitignored actuals; *.template committed)
├── packaging/               # PyInstaller spec + build scripts
├── scripts/                 # dev/CI helper scripts
├── assets/                  # shipped source assets (e.g. hardware_images/)
├── docs/                    # all documentation (sub-homes below)
├── .github/                 # workflows + collaboration scaffolding
└── .cursor/                 # rules/, skills/, hooks.json, plans/
```

**Root holds only config + entry docs.** No release notes, logs, generated artifacts, coverage files, or scratch files at root.

## `docs/` sub-homes

| Path | Contents |
| --- | --- |
| `docs/deployment/` | install / update / uninstall / permissions guides |
| `docs/development/` | internal implementation guides, incl. this file + `AGENTIC-CICD-PIPELINE.md` |
| `docs/api/` | API reference |
| `docs/confluence/` | local mirror of Confluence page 6664028496 |
| `docs/marketing/` | one-pager + screenshots |
| `docs/issues/<ID>/` | per-work-item spec/plan/tasks/evidence |
| `docs/releases/` | `RELEASE_NOTES_vX.Y.Z.md` (written by `prepare-release`/`ship-release`) |

Pipeline tracking docs live directly under `docs/`: `PROJECT-STATUS.md`, `TODO-ROADMAP.md`, `ROADMAP-ARCHIVE.md`, `PLANS-INDEX.md`, `DECISIONS.md`, `PIPELINE-METRICS.md`, `CHANGELOG-ARCHIVE.md`.

## Layered `src/` map (enforced for NEW modules)

The application follows the layered architecture in [`architecture-03`](../../.cursor/rules/architecture-03.mdc). New modules are placed by concern:

| Concern | Modules |
| --- | --- |
| **Pipeline** | `api_handler` → `data_extractor` → `report_builder` |
| **Port mapping** | `port_mapper`, `enhanced_port_mapper`, `external_port_mapper`, `vnetmap_parser` |
| **Diagrams** | `network_diagram*`, `rack_diagram` |
| **Advanced ops** | `advanced_ops`, `oneshot_runner`, `script_runner`, `tool_manager`, `session_manager`, `result_*`, `workflows/` |
| **Web UI** | `app.py` |
| **Health** | `health_checker` |
| **Shared utilities** | `src/utils/` |

**Decision:** existing `src/` stays flat (~28 top-level modules) to avoid 40+ test-import churn. A phased subpackage refactor is a deferred backlog item, out of the current pipeline's scope. The map above governs where NEW modules and their tests go.

## Runtime / generated convention

These directories are **gitignored and never committed** — they are produced at runtime:

```
logs/ output/ clusters/ reports/ import/ telemetry/
build/ dist/ test_output/ tracer-output/ archive/
```

- `scripts/clean-workspace.sh` (a.k.a. `make clean`) purges them.
- `.archive/` / `archive/` is retirement storage: **local-only, gitignored**. Retired files are moved here (surviving in git history), never pushed.

## Enforcement

- **`codebase-health` skill** — recurring orphan / dead-file / duplication / oversized-module / boundary-violation sweep; proposes archival or consolidation with a diff for approval, feeding a prioritized refactor list into the tracker.
- **`.cursor/hooks.json` warn** — fires when a new file lands outside this standard (new top-level file, release note outside `docs/releases/`, generated artifact staged).
- **`bootstrap-pipeline`** seeds this same baseline into sibling repos.

Every new skill, agent, workflow, and doc adheres to this structure by default.
