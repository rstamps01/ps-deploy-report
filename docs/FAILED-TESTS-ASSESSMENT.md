# Failed Tests Assessment — Functional Impact

**Date:** 2026-03-10  
**Scope:** The two unit tests that were failing in `tests/test_ssh_adapter.py` (TestSubprocessSSH).

---

## Summary

| Test | Root cause | Functional impact? | Resolution |
|------|------------|--------------------|------------|
| `test_successful_command` | Test bug: wrong mocks | **None** | Fixed |
| `test_os_error_returns_error` | Test bug: wrong mocks | **None** | Fixed |

**Conclusion:** The failures were due to **test implementation errors**, not product bugs. The SSH adapter behavior is correct; the tests were not exercising the code path they intended to test. **No user-facing or functional impact.**

---

## 1. What was failing

- **test_successful_command**: `AssertionError: 1 != 0` (expected returncode 0, got 1).
- **test_os_error_returns_error**: `AssertionError: 'no such file' not found in 'timed out'` (expected error message "no such file", got "timed out").

---

## 2. Root cause (test bugs)

In `src/utils/ssh_adapter.py`, `_subprocess_ssh` behaves as follows:

- If `shutil.which("sshpass", path=...)` returns a path → use **subprocess** (sshpass + ssh) and call `subprocess.run(...)`.
- If it returns falsy (e.g. `None`) → **fall back** to `_paramiko_exec(...)` and never call `subprocess.run`.

The tests:

- Patched `shutil.which` to return **`None`**.
- Patched `subprocess.run` to return success or raise an exception.

Because `which` was `None`, the implementation **always took the paramiko fallback**. So:

- **test_successful_command**: Intended to test the subprocess success path, but the code path used was paramiko. Paramiko (real or partially mocked) returned failure or timeout → rc=1.
- **test_os_error_returns_error**: Intended to test subprocess raising `OSError("no such file")`, but the code path used was paramiko. Paramiko produced a different error (e.g. "timed out") → wrong message.

Additionally, `subprocess.run` was patched as `"subprocess.run"` (global) instead of where it is used. The code runs in `utils.ssh_adapter`, which has its own reference to `subprocess`. Patching at the use site (`utils.ssh_adapter.subprocess.run`) is more reliable.

So:

- **Functional impact:** None. Production code was correct; only the tests were wrong.
- **Cause:** Tests targeted the subprocess path but, by mocking `which` to `None`, forced the paramiko path and wrong assertions.

---

## 3. Fix applied

In `tests/test_ssh_adapter.py` (TestSubprocessSSH):

1. **Patch subprocess where it’s used:** `@patch("subprocess.run")` → `@patch("utils.ssh_adapter.subprocess.run")` so the adapter’s `subprocess.run` is mocked.
2. **Exercise the subprocess path:** For all four subprocess tests, `@patch("shutil.which", return_value=None)` was changed to `return_value="/usr/bin/sshpass"` so the implementation enters the block that calls `subprocess.run`.

With this:

- The subprocess path is actually run under test.
- Success, timeout, and OSError behavior are asserted correctly.

All four `TestSubprocessSSH` tests now pass.

---

## 4. Other “failures” (lint / format / coverage)

These are not test logic failures and are pre-existing:

- **flake8**: Many style/issues (unused imports, line length, etc.). No impact on runtime behavior.
- **black**: Files would be reformatted. No impact on behavior.
- **mypy**: Not run in the environment used; type-check only. No direct runtime impact.
- **Coverage below 80%**: CI gate; does not indicate broken functionality.

---

## 5. Recommendation

- Treat the two former test failures as **resolved** and **non-functional** (test-only).
- No change to SSH adapter behavior or to report/API/EBox features is required for these failures.
- Optional: run full unit + integration suite to confirm nothing else regressed:  
  `pytest tests/ --ignore=tests/test_ui.py -v --no-cov`
