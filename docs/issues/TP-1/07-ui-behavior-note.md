# UI-Behavior Side Note (separate from TP-1 root cause)

While reproducing TP-1 through the cursor-ide-browser MCP against the live Dev
server, two independent UI-quality issues were observed in the Reporter
Connection Settings form. Tester also took manual control mid-run to populate
Node User ("vastdata") and Node Password ("whenever crispy pod tofu") because
the form did not visibly reflect the programmatic fills.

These are NOT the TP-1 parser bug. The /api/discover request that reached the
backend ultimately carried correct credentials (paramiko authenticated twice
in `05-server-log.txt`), so the TP-1 reproduction itself is valid. But these
are real UI defects that should be filed separately.

## Observation 1 — Programmatic `value` set does not render until an input event

| Step | Aria/DOM snapshot | Rendered screenshot |
|---|---|---|
| MCP `browser_fill` on Node User (`e12`) with "vastdata" | `value: vastdata` | field appears empty |
| User clicks into the field / focus event fires | `value: vastdata` | field renders "vastdata" |

Likely cause: the input's underlying React/vanilla handler binds rendered
state to a JS `change`/`input` event. Programmatic `.value =` assignment
without a `dispatchEvent(new Event('input', {bubbles: true}))` updates the
DOM property but not the React-managed render. The MCP fill helper appears
to set the property without dispatching the event for this particular field.

Impact: a field that *looks* empty actually has a value, and vice versa.
A real user racing the MCP — or copy/pasting into the field while
focus is elsewhere — can be confused about state. Most importantly, the
test reproduction is harder to verify visually unless you re-focus every field.

## Observation 2 — Re-filling Node User clears Node Password

| t | Action | Node Password rendered as |
|---|---|---|
| t1 | After parallel fill of all 7 fields | 24 dots (correct, matches "whenever crispy pod tofu") |
| t2 | After `browser_fill(e12, "vastdata")` to fix Observation-1 visual | empty |
| t3 | After `browser_fill(e15, "whenever crispy pod tofu")` again | 24 dots |

Likely cause: a `change` listener on Node User in the form's autofill
plumbing — see `frontend/templates/reporter.html` around lines 985-987:

```javascript
['username','password','node_user','node_password','switch_user','switch_password'].forEach(function(k) {
    var el = document.getElementById(profileFieldMap[k] || k);
    ...
});
```

When `node_user` changes and Autofill is OFF, the handler appears to
clear the matching password field. Equivalent surfaces likely exist for
`username`/`password` (VMS) and `switch_user`/`switch_password` pairs but
were not exercised in this run.

Impact: a field a user just typed into gets silently cleared if they
later edit the user-name in the same group. There is no visible
indicator and no toast.

## How TP-1 reproduction stayed valid despite these

- Final pre-click form state (captured in `01-pre-click.png`): all 7
  fields populated correctly after the second Node Password refill.
- `/api/discover` POST body contained `cluster_ip=192.168.2.2`,
  `tech_port=true`, `node_user=vastdata`, `node_password="whenever
  crispy pod tofu"`. Two successful paramiko authentications in
  `05-server-log.txt` confirm the password reached the cluster.
- The failure (`VMSDiscoveryError: Could not parse management IP from
  ip addr output: ''`) happened in `parse_management_ip`, AFTER auth
  succeeded — entirely independent of any front-end value-handling.

## Suggested next steps

1. Open separate ticket **RPT-VALIDATION-1** ("Reporter form: programmatic
   field-value set does not render until input/focus event").
2. Open separate ticket **RPT-VALIDATION-2** ("Reporter form: changing user
   field clears matching password field with Autofill off"). Probably one
   listener fix in `frontend/templates/reporter.html` ~L985.
3. Add a Playwright UI test in `tests/test_ui.py` that programmatically
   fills the seven fields and asserts each rendered value, to catch
   regressions of either symptom.

These are independently fixable from TP-1 and should NOT block the v1.5.7
patch.
