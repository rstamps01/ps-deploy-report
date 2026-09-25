---
name: Reorder sections fix config
overview: Reorder Advanced Config sections (Report Formatting first, then renamed Data Collection), and wire SSH/Health Check/Advanced Operations/Security config values into the Reporter page so they take effect.
todos:
  - id: reorder-sections
    content: Move Report Formatting to top, rename and move Data Collection to 2nd position in advanced_config.html
    status: completed
  - id: wire-reporter-backend
    content: Pass config values from app.py reporter_page() to the reporter.html template
    status: completed
  - id: wire-reporter-frontend
    content: Use Jinja variables in reporter.html to set initial defaults for proxy_jump, mode, switch_placement, autofill, vperfsanity
    status: completed
  - id: verify-all
    content: Run tests and lint
    status: completed
isProject: false
---

# Reorder Advanced Config Sections and Wire Config into Reporter

## Part 1: Reorder and Rename Sections

In `[frontend/templates/advanced_config.html](frontend/templates/advanced_config.html)`, reorder the accordion sections so:

1. **Report Formatting** (currently 3rd) moves to position 1 (right after the Tune Bar)
2. **Report Data Collection** (currently "Data Collection", 5th) moves to position 2, renamed from "Data Collection" to "Report Data Collection"
3. Remaining sections follow: API Settings, Logging, Output, SSH, Health Check, Advanced Operations, Security

This is purely a cut/paste reorder of the `<div class="cfg-section">` blocks plus renaming the `<h3>` from "Data Collection" to "Report Data Collection".

## Part 2: Wire Config into Reporter UI

The Reporter page (`[frontend/templates/reporter.html](frontend/templates/reporter.html)`) has hardcoded defaults for settings that should come from `config.yaml`. The following config keys have no effect because they're never passed to the template:

| Config Key                                         | Reporter UI Element          | Current Default                 |
| -------------------------------------------------- | ---------------------------- | ------------------------------- |
| `ssh.proxy_jump`                                   | `#proxyJumpToggle` checkbox  | Hardcoded `checked`             |
| `advanced_operations.default_mode`                 | `oneShotMode` init           | Hardcoded `"reporter"`          |
| `advanced_operations.default_switch_placement`     | `#rptSwitchPlacementToggle`  | Hardcoded `manual` (`checked`)  |
| `advanced_operations.autofill_default_passwords`   | `#useDefaultCreds` checkbox  | Hardcoded `checked`             |
| `advanced_operations.vperfsanity_default_selected` | `isChecked` in workflow list | Hardcoded `false`               |
| `health_check.include_in_report`                   | Not wired                    | N/A (backend reads at job time) |

**Note**: `ssh.timeout`, `ssh.ping_timeout`, and all `security.`* settings are already read at job execution time from `config.yaml` by the backend (`_load_yaml(config_path)` in the generate/health-check routes). They don't need Reporter UI changes -- they work correctly, but have no visible UI indicator. The `health_check.include_in_report` and tier settings are also read at job time.

### Changes needed

1. `**[src/app.py](src/app.py)`** -- In `reporter_page()`, load config and pass relevant values to the template:

```python
@app.route("/reporter")
def reporter_page():
    config = _load_yaml(app.config["CONFIG_PATH"])
    adv = config.get("advanced_operations", {})
    ssh = config.get("ssh", {})
    return render_template(
        "reporter.html",
        version=APP_VERSION,
        cfg_proxy_jump=ssh.get("proxy_jump", True),
        cfg_default_mode=adv.get("default_mode", "reporter"),
        cfg_switch_placement=adv.get("default_switch_placement", "manual"),
        cfg_autofill_passwords=adv.get("autofill_default_passwords", True),
        cfg_vperfsanity_default=adv.get("vperfsanity_default_selected", False),
    )
```

1. `**[frontend/templates/reporter.html](frontend/templates/reporter.html)**` -- Use Jinja variables to set initial state:

- Line 74: `proxyJumpToggle` -- use `{{ 'checked' if cfg_proxy_jump else '' }}`
- Line 89: `useDefaultCreds` -- use `{{ 'checked' if cfg_autofill_passwords else '' }}`
- Line 131: `rptSwitchPlacementToggle` -- use `{{ 'checked' if cfg_switch_placement == 'manual' else '' }}`
- Line 136: hidden input `rptSwitchPlacement` -- use `value="{{ cfg_switch_placement }}"`
- Line 1878: vperfsanity `isChecked` -- use Jinja variable to control default
- Lines 2195-2198: Init block -- use `cfg_default_mode` to set initial mode
