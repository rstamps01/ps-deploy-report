# Screenshots

Images for the marketing site (`../index.html`, `../quick-start-guide.html`,
`../se-one-pager.html`) and the repository README. Every page references these
by path, so replacing a file in place updates every page that uses it.

## Capture settings

- Browser window at **1440 x 900**, cropped to the viewport (no address bar).
- PNG, for crisp text.
- Use a connected cluster where the screen has data to show.
- For header and dropdown captures, crop tight to the relevant region — a
  full-width capture leaves the subject too small to read.

macOS: Cmd+Shift+4 then Space captures a single window.
Windows: Win+Shift+S for a region capture.

## The numbered macOS upgrade sequence

`1-` through `8-` are the ordered steps in the Quick Start guide's **Upgrade
from Earlier Version** path. The number is the step number shown in that path.

| File | Step |
|---|---|
| `1-Upgrade-Download.png` | `UPDATE AVAILABLE` pill with the Download dropdown open |
| `2-Upgrade-Only-Exit-App-Mac.png` | Exit button in the navbar |
| `3-Upgrade-Install-Mac.png` | Mounted DMG, app beside the Applications shortcut |
| `4-Upgrade-Only-Replace-Mac.png` | macOS "replace existing item" dialog |
| `5-Upgrade-Install-Done-Mac.png` | Gatekeeper "Not Opened" warning |
| `6-Upgrade-Install-Privacy-Security-OpenAnyway-Mac.png` | Privacy & Security, Open Anyway |
| `7-Upgrade-Install-Open-Anyway-Mac.png` | Open Anyway confirmation |
| `8-Upgrade-Install-Use-Password-Mac.png` | Touch ID / password prompt |

**Inserting a step** means renaming every file after it, and the `<img src>` in
`quick-start-guide.html` along with them. Rename in descending order (8 before
7, and so on) or `git mv` will overwrite a file that has not moved yet.

The **New Installation** path reuses the same images and shows a subset of these
steps, so its numbering does not match these filenames. That is expected: the
guide assigns step numbers at runtime based on which steps are visible.

## The Field Procedure sequence

`Procedure-NN-*.png` are the annotated captures (green callouts) for the
**Field Procedure** section of `quick-start-guide.html`. `NN` is the procedure
step the image belongs to; steps without a capture are text-only by design.

| File | Step |
|---|---|
| `Procedure-03-Update-Tools.png` | Header Update Tools dropdown, Update Tools button |
| `Procedure-06-Cluster-Profile.png` | Connection Settings: IP field, VMS Mgmt Mode, Save |
| `Procedure-07-Discovery.png` | Switch Placement Editor: Discovery, then Run Discovery |
| `Procedure-08-Test-Suite.png` | Test Suite tab with all operations selected, Run |
| `Procedure-10-Results-Bundles.png` | Results page, Bundles tab, newest bundle |

These are 2x retina captures (2878 x 1870) from a `v1.6.0` build, so they show
the `UPDATE AVAILABLE` pill. The procedure text refers to steps by number, so
renumbering a step means renaming its file and the `<img src>` together.

## Feature screenshots

`Dash.png`, `Reporter.png`, `Results.png`, `Library.png`, `Adv-Config.png`,
`Test-Suite.png`, `Update-Tools.png`, `Report-Rack-Diagram.png`,
`Logical-Network-Diagram.png`.

These show product UI and go stale when the interface changes. Re-capture from a
current build rather than adding a second copy — the filename is the reference
used across the site.

## Version numbers are visible in captures

Most of these include the app header, which carries the version and the update
pill. Two consequences worth planning around:

- A capture showing `UPDATE AVAILABLE` requires running a build *older* than the
  latest release, so it will also show that older build's UI.
- A capture showing `LATEST VERSION` should be taken from a current build.

Pick the build to match what the surrounding text describes.

`Adv-Config.png` is the outlier: it came from a `v1.5.0` build and is the only
capture showing the orange `PRE-RELEASE` badge rather than the green
`LATEST VERSION` one. It is also a 2x retina capture (2584 x 1900) where the
rest of the feature set is 1024 wide. Worth re-taking next time that page
changes.
