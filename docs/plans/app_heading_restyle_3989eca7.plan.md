---
name: App heading restyle
overview: Restyle the navbar heading to match the "asbuilt-analyzer" screenshot style (lowercase, accent-colored suffix), and assess LOE for renaming "As-Built Reporter" to "ASBuilt-Reporter" project-wide.
todos:
  - id: heading-restyle
    content: Restyle navbar heading in base.html and app.css to match screenshot (asbuilt in white, -reporter in accent cyan)
    status: completed
isProject: false
---

# Application Heading Restyle and Rename LOE Assessment

## Part 1: Navbar Heading Restyle (Quick Change)

The screenshot shows `asbuilt-analyzer` styled as:

- **"asbuilt"** in white (primary text color)
- **"-reporter"** in cyan/blue accent color (matches `--accent` / `#00d4ff`)
- All lowercase, clean sans-serif, no spaces

### Current code

In [frontend/templates/base.html](frontend/templates/base.html) line 17:

```html
<span class="nav-title">As-Built Reporter</span>
```

CSS in [frontend/static/css/app.css](frontend/static/css/app.css) lines 62-66:

```css
.nav-title {
    font-weight: 600;
    font-size: 1.1rem;
    letter-spacing: -0.01em;
    color: var(--text-primary);
}
```

### Proposed change

- Replace the single `<span class="nav-title">` with two spans to allow split coloring:

```html
<span class="nav-title">asbuilt<span class="nav-title-accent">-reporter</span></span>
```

- Add CSS for the accent portion:

```css
.nav-title-accent {
    color: var(--accent);
}
```

This produces the exact style from the screenshot: "asbuilt" in white, "-reporter" in cyan.

---

## Part 2: LOE Assessment for Full Rename ("As-Built Reporter" to "ASBuilt-Reporter")

### Scope Summary

| Pattern                                | Matches | Files | Category Breakdown                                                     |
| -------------------------------------- | ------- | ----- | ---------------------------------------------------------------------- |
| "As-Built Reporter"                    | 31      | 23    | Templates (9), Python (5), Packaging (2), Docs (1), Other (6)          |
| "VAST As-Built" (all forms)            | 125     | 73    | Docs (~~32), Python (~~22), Templates (11), Config (~~5), Other (~~15) |
| "As-Built Report Generator"            | 101     | 58    | Docs (~~35), Python (~~15), Config (~~6), Other (~~10)                 |
| "VAST Reporter"                        | 55      | 17    | Docs (~9), CI (2), Packaging (3), Templates (2)                        |
| "vast-asbuilt-reporter" (path/package) | 238     | 13    | Docs (9), Python (1), Other (3)                                        |
| Standalone "As-Built"                  | 224     | 96    | Across all categories                                                  |

### Affected areas by tier

**Tier 1 -- UI/User-Facing (low risk, ~15 files):**

- Navbar heading (`base.html`)
- Browser tab titles (`{% block title %}` in 11 templates)
- Footer text (`base.html`)
- CSS comment references (`app.css`)

**Tier 2 -- Application Code (medium risk, ~25 files):**

- `src/app.py` docstring and any display strings
- `src/main.py` argparse description and version string
- `src/__init__.py` package metadata
- Module docstrings in `api_handler.py`, `data_extractor.py`, `report_builder.py`, `health_checker.py`, `rack_diagram.py`, `hardware_library.py`, `result_bundler.py`, `utils/logger.py`
- Test files referencing the app name (~8 test files)

**Tier 3 -- Packaging and CI (high risk, ~8 files):**

- `packaging/vast-reporter.spec` -- APP_NAME, EXE name, BUNDLE name, bundle_identifier
- `packaging/build-mac.sh`, `packaging/build-windows.ps1`
- `.github/workflows/ci.yml`, `.github/workflows/build-release.yml`
- `Start Reporter.command`
- `scripts/check-version-sync.sh`

**Tier 4 -- Documentation (bulk, ~45 files):**

- `README.md`, `CHANGELOG.md`
- `docs/TODO-ROADMAP.md`, `docs/API-REFERENCE.md`, `docs/ADVANCED-OPERATIONS.md`, `docs/POST-INSTALL-VALIDATION.md`
- `docs/deployment/` (6 guides + 4 install/uninstall scripts)
- `docs/development/` (6+ implementation guides)
- `.cursor/rules/` (5 rule files)
- `config/config.yaml.template`, `config/test_config.yaml`
- `.archive/` release notes

**Tier 5 -- Repository name and paths (external, not code):**

- GitHub repo name `vast-asbuilt-reporter` (requires GitHub admin action, breaks all clone URLs)
- 238 path references in docs would need updating if repo is renamed
- Not recommended to change as part of this effort

### LOE Estimate

- **Part 1 (heading restyle only):** ~5 minutes, 2 files
- **Tier 1 (UI text):** ~15 minutes, ~15 files, low risk
- **Tier 2 (app code):** ~30 minutes, ~25 files, medium risk (requires full test suite pass)
- **Tier 3 (packaging/CI):** ~30 minutes, ~8 files, high risk (affects builds, must test .dmg/.zip)
- **Tier 4 (documentation):** ~60 minutes, ~45 files, low risk but tedious
- **Tier 5 (repo name):** Not recommended, external dependency

**Total for full rename (Tiers 1-4): ~2.5 hours across ~90 files, ~550 occurrences.**

### Recommendation

Execute Part 1 (heading restyle) immediately. For the full rename, execute in phases:

- Phase A: Tiers 1+2 together (UI + code) with test verification
- Phase B: Tier 3 (packaging/CI) separately with build verification
- Phase C: Tier 4 (docs) as a bulk pass using parallel subagents
