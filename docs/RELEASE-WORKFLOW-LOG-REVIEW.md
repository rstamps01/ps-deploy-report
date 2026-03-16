# Release Workflow Log Review (run 60715772501)

**Date:** 2026-03-16  
**Source:** `logs_60715772501.zip`

## Summary

| Job           | Result   | Notes |
|---------------|----------|--------|
| quality-gate  | (run)    | continue-on-error; does not block |
| test          | (run)    | continue-on-error; does not block |
| **build (macOS)**  | **Success** | PyInstaller + create-dmg ran; artifact VAST-Reporter-mac uploaded (858 files, ~134 MB) |
| **build (Windows)**| **Failed**  | PowerShell error in `packaging/build-windows.ps1` at zip step |
| **release**   | **Skipped** | `needs: build` → build failed (Windows), so release did not run; no .dmg/.zip on GitHub Release |

## Root cause: Windows build failure

**Error:**
```text
Join-Path : A positional parameter cannot be found that accepts argument 'app.py'.
At packaging\build-windows.ps1:42 char:10
+ $AppPy = Join-Path $ProjectRoot "src" "app.py"
```

**Cause:** In PowerShell, `Join-Path` only accepts two parameters in this context. The script used `Join-Path $ProjectRoot "src" "app.py"` (three arguments), which is invalid.

**Fix applied:** Use nested `Join-Path` so it works on all PowerShell versions:
```powershell
$AppPy = Join-Path (Join-Path $ProjectRoot "src") "app.py"
```

## Other observations

- **Node.js 20 deprecation:** Warning still appears in some steps; `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` is set at workflow level but may not apply to all runners or action versions.
- **fail-fast: false:** macOS and Windows builds ran independently; Windows failure did not cancel the macOS job (macOS artifact was uploaded).
- **Release:** Because the overall `build` job is considered failed when any matrix job fails, the `release` job was skipped and no assets were attached to the GitHub Release.

## After the fix

Once the Join-Path fix is committed and the workflow re-run (e.g. by re-pushing the tag), the Windows build should complete, both artifacts will be uploaded, and the release job will attach `VAST-Reporter-v1.4.2-mac.dmg` and `VAST-Reporter-v1.4.2-win.zip` to the GitHub Release.
