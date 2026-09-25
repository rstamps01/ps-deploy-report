---
name: Bug Tracking Documentation Update
overview: Add 6 observed bugs to TODO-ROADMAP.md as tracked defects under a new "Known Issues" section, update CHANGELOG.md with known issues, and update AO-19 status to reflect state persistence bugs found during testing.
todos:
  - id: add-bugs-roadmap
    content: Add BUG-1 through BUG-6 to TODO-ROADMAP.md under new Known Issues section
    status: pending
  - id: update-changelog-issues
    content: Add Known Issues subsection to CHANGELOG.md [Unreleased]
    status: pending
  - id: update-advops-doc
    content: Add Known Limitations section to ADVANCED-OPERATIONS.md
    status: pending
  - id: update-ao19-status
    content: Update AO-19 status and Next Steps in TODO-ROADMAP.md to reflect bugs found
    status: pending
isProject: false
---

# Bug Tracking and Documentation Update

## Bugs to Track

Six issues observed during Advanced Ops state persistence testing:

| ID  | Summary | Root Cause Area | Severity |
| --- | ------- | --------------- | -------- |

### BUG-1: Profile selection not persistent across page refresh

- **Observed:** Selected Saved Profile reverts to "--Select a Profile--" on navigation/refresh
- **Expected:** Profile selection persists
- **Files:** `frontend/templates/advanced_ops.html` (`saveUIState` / `applySavedUIState`)
- **Likely fix:** `applySavedUIState()` sets `profileSelect.value` but doesn't trigger the `change` event or wait for profiles to be fetched first; profile options may not be populated yet when restore runs

### BUG-2: One-Shot checklist resets to all-checked on refresh

- **Observed:** Previously selected operations are disregarded; all checkboxes are selected
- **Expected:** Last checklist selections are remembered
- **Files:** `frontend/templates/advanced_ops.html` (`saveUIState` / `applySavedUIState`, `populateOneShotChecklist()`)
- **Likely fix:** `populateOneShotChecklist()` builds checkboxes fresh (all checked by default) and runs after the mode toggle is restored; saved checklist state needs to be applied *after* the checklist is populated

### BUG-3: Cleared output repopulates on refresh

- **Observed:** After manually clearing output, page refresh repopulates all cleared entries
- **Expected:** Manual clear should persist; only live-running output should resume on refresh
- **Files:** `frontend/templates/advanced_ops.html` (hydration logic, `sessionStorage`, `hydrateFromBackend`)
- **Likely fix:** When output is cleared, store a "cleared" flag or update the sync cursor to the current server buffer length so `hydrateFromBackend()` doesn't re-fetch old entries

### BUG-4: Mode toggle resets to One-Shot on refresh

- **Observed:** When Step-by-Step is selected then page refreshed, it switches back to One-Shot
- **Expected:** Persistence recalls last mode state
- **Files:** `frontend/templates/advanced_ops.html` (`applySavedUIState`, `hydrateFromBackend`)
- **Likely fix:** `hydrateFromBackend()` may be forcibly switching to one-shot mode in certain code paths, or the mode restoration order conflicts with initialization

### BUG-5: Generated As-Built reports filter incorrectly in Validation Results

- **Observed:** Many reports generated for saved clusters appear under "Unsaved Cluster Results"
- **Expected:** Reports match to the correct cluster profile
- **Files:** `src/result_scanner.py` (cluster IP extraction from PDF filenames), `src/app.py` (Validation Results API)
- **Likely fix:** PDF filenames use cluster *name* (e.g., `vast_asbuilt_report_mycluster_...pdf`) not cluster *IP*; the scanner needs to cross-reference cluster names from saved profiles to resolve the IP

### BUG-6: One-Shot default credentials use single user for all operations

- **Observed:** With default PW enabled, admin/<default-password> is used for all operations; Report Generator and Health Checks require support/654321
- **Expected:** When default PW enabled, logic should use admin user for vperfsanity and support user for Report Generator and Health Checks
- **Files:** `src/oneshot_runner.py` (`_run_report`, `_run_health_checks`, `_run_operations`), `frontend/templates/advanced_ops.html` (default creds toggle)
- **Likely fix:** `OneShotRunner` needs credential-per-phase logic: detect when default creds are in use, swap API username/password to `support`/`654321` for report and health check phases, and use `admin`/`<default-password>` for vperfsanity

## Changes to Make

### [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md)

- Add new **"Known Issues — State Persistence and One-Shot"** section after "In progress"
- Add BUG-1 through BUG-6 as tracked items with status "Open" and priority
- Update AO-19 notes to reference these bugs found during validation
- Update "Last updated" date
- Update "Next steps" to include bug fixes

### [CHANGELOG.md](CHANGELOG.md)

- Add a **"Known Issues"** subsection under `[Unreleased]` listing the 6 bugs

### [docs/ADVANCED-OPERATIONS.md](docs/ADVANCED-OPERATIONS.md)

- Add a **"Known Limitations"** subsection noting the current state persistence gaps and the credential routing issue
