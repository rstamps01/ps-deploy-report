---
name: Analyzer Gitignore + UI Overhaul
overview: "Add four `.gitignore` entries so the analyzer web files stay off GitHub, then overhaul the UI with a modern dark dashboard aesthetic: improved event cards, animated network topology map, live stats bar, credential toggles, and smoother overall visual design."
todos:
  - id: gitignore
    content: Add 4 entries to .gitignore for analyzer web files (analyzer_web.py, static/analyzer/, templates/analyzer/, alert_engine.py)
    status: completed
  - id: css-overhaul
    content: "Rewrite analyzer.css: card-style events, slide-in animation, alert pulse glow, stats strip, traffic particle styles, node hover glow, collapsible sidebar sections, credential eye-toggle"
    status: completed
  - id: base-template
    content: "Update base.html: add live stats strip (events, rate, connections, commands), update header poller to feed strip every 1s"
    status: completed
  - id: index-template
    content: "Update index.html: collapsible sidebar sections with details/summary, password eye-toggle buttons, events/sec pill in tab bar, Export CSV button, map legend strip, taller map panel"
    status: completed
  - id: live-js-overhaul
    content: "Update analyzer-live.js: two-line card renderer with slide-in animation, event rate tracker, node-click host filter, traffic particle animation on edges, Export CSV, connection counter"
    status: completed
  - id: replay-js-update
    content: "Update analyzer-replay.js: use shared two-line card renderer, add speed slider (1x-50x)"
    status: completed
isProject: false
---

# asbuilt-analyzer — Gitignore + UI Overhaul

## Part 1 — .gitignore isolation

Add to `.gitignore` (four entries under a new `# asbuilt-analyzer` section):

```
# asbuilt-analyzer web frontend (local only — not published to GitHub)
tools/analyzer_web.py
tools/static/analyzer/
tools/templates/analyzer/
tools/tracer/alert_engine.py
```

This keeps the shared tracer library (`tools/tracer/`, `tools/op_tracer.py`, `tools/requirements-tracer.txt`) tracked, while the web app and its dedicated alert engine stay local only.

---

## Part 2 — UI Overhaul

### Visual design direction

Dark dashboard aesthetic inspired by security monitoring tools. Three pillars:

- **Depth** — layered panels with subtle shadows, frosted borders
- **Motion** — events slide in, alerts pulse, traffic animates on the map
- **Clarity** — tight information hierarchy; the most important data is biggest and closest to the left edge

### Files changed

#### `[tools/static/analyzer/css/analyzer.css](tools/static/analyzer/css/analyzer.css)` — full rewrite

Key additions vs current:

- `--shadow-sm / --shadow-md` CSS vars for consistent depth
- Card-style event rows with left color border (`border-left: 3px solid <category-color>`) instead of flat rows
- `.event-card` replaces `.event-row` — two-line layout:
  - Line 1: badge + host(s) + direction arrow + detail (bold)
  - Line 2: timestamp + source adapter + duration (muted, smaller)
- Slide-in keyframe: `@keyframes slideIn` for new live events
- Pulsing glow on critical alerts: `@keyframes alertPulse`
- Glassmorphism sidebar header: `backdrop-filter: blur(8px)`
- Stats bar below the main header: thin strip with animated counters
- Node hover glow on SVG map nodes
- Password field with eye-toggle button style
- Collapsible sidebar sections (CSS `details/summary` or JS toggle)
- `.event-rate-badge` — events/sec pill in the tab bar area

#### `[tools/templates/analyzer/base.html](tools/templates/analyzer/base.html)` — enhancements

- Add **live stats strip** between header and body:

```html
  <div class="stats-strip">
    <span id="ss-total">0 events</span>
    <span id="ss-rate">—/s</span>
    <span id="ss-conns">0 connections</span>
    <span id="ss-cmds">0 commands</span>
  </div>


```

- Update header poller to populate stats strip every second
- Add `data-page` attribute on body for page-specific JS

#### `[tools/templates/analyzer/index.html](tools/templates/analyzer/index.html)` — enhancements

- **Sidebar**: add `details`/`summary` collapsible sections, credential `show/hide` eye button on password fields, field icons (unicode), `Test Connection` button that calls `/session/status` to verify the entry host is reachable
- **Tab bar**: add `events/sec` pill that updates live: `↑ 3.2/s`
- **Toolbar**: add `Export CSV` button (downloads visible filtered events)
- **Right column map panel**: make it taller (260px), add legend strip below SVG (four colored dots: Local / Entry / Secondary / External)

#### `[tools/static/analyzer/js/analyzer-live.js](tools/static/analyzer/js/analyzer-live.js)` — enhancements

- **Event rendering**: replace single-line row with two-line card
- **Slide-in animation**: add CSS class `new-event` on insert, remove after 800ms
- **Event rate tracker**: rolling 5s window → update `ss-rate` element
- **Node click → host filter**: SVG node `click` sets `_hostFilter` and calls `applyFilters()`
- **Traffic particle animation**: on every `socket.`*or `ssh.`* event, animate a small dot along the matching edge for 600ms using `requestAnimationFrame`
- **Export CSV**: `exportCSV()` serializes filtered events to CSV blob and triggers download
- **Connection counter**: track unique active `socket.open` hosts → feed `ss-conns`

#### `[tools/static/analyzer/js/analyzer-replay.js](tools/static/analyzer/js/analyzer-replay.js)` — enhancements

- Shared `_renderCard()` function (same two-line layout as live)
- Replay speed slider in addition to buttons (1×–50× range)

### Layout diagram

```
┌─ Header (48px): brand · nav · [stats strip: 0 events · —/s · 0 conns] · status dot · alert badge ─┐
├─ Sidebar (260px) ──────────┬─ Timeline ──────────────────────────┬─ Right (300px) ──────────────────┤
│ [▼ Target]                 │ [All 0][SSH][API][Transfer][Sock]   │ ┌─ Network Map (260px SVG) ──┐   │
│   Entry host  ___          │  ↑ 2.1/s    🔍 filter  host ▾  ↓  │ │  ◉ local                   │   │
│   SSH user    ___          │ ╔══════════════════════════════════╗ │ │    │                       │   │
│   SSH pass  🔒 ___         │ ║ [SSH] <ip> → <ip>  ║ │ │  ◉ entry                  │   │
│                            │ ║ auth [password]     09:16:58.112║ │ │   / \                      │   │
│ [▼ API Credentials]        │ ╠══════════════════════════════════╣ │ │  ◉   ◉ secondary          │   │
│ [▼ App Monitoring]         │ ║ [APP] <ip>              ║ │ └────────────────────────────┘   │
│ [▼ Options]                │ ║ $ cat /etc/clustershell...      ║ │  ● local  ● entry  ◉ 2nd  ● ext  │
│                            │ ╠══════════════════════════════════╣ │ ┌─ Alerts ─────────────────────┐ │
│ [▶ Start] [■ Stop]         │ ║ [⚠] ALERT.WARN                 ║ │ │ ⚠ unknown_ip                  │ │
│                            │ ║ Connection to <ip>:443  ║ │ │   → <ip>             │ │
│ SSH   API  Xfer  Sock      │ ╚══════════════════════════════════╝ │ │ ⚠ suspicious_port            │ │
│  12    8    3    89        │                                      │ └──────────────────────────────┘ │
│ ⚠ 2  🔴 0                  │                                      │                                  │
└────────────────────────────┴──────────────────────────────────────┴──────────────────────────────────┘
```
