# Concrete mypy and Black Fix Suggestions

## Black (done)

Black has been applied to `src/main.py` and `src/app.py`. CI `black --check` should pass.

---

## mypy: Quick wins

### 1. Install Paramiko stubs (CI + local)

Add to `requirements-dev.txt`:

```
types-paramiko>=3.0.0
```

Then:

```bash
pip install types-paramiko
```

Fixes: `src/utils/ssh_adapter.py:172` — "Library stubs not installed for paramiko".

### 2. `src/utils/__init__.py` — `_MEIPASS` (PyInstaller-only attribute)

mypy doesn't know `sys._MEIPASS` exists (it's set by PyInstaller at runtime).

**Option A (recommended):** Use `getattr` so mypy sees a string type:

```python
# Line 21-22, replace:
if getattr(sys, "frozen", False):
    return Path(sys._MEIPASS)
# with:
if getattr(sys, "frozen", False):
    return Path(getattr(sys, "_MEIPASS", ""))
```

**Option B:** Suppress only on that line:

```python
return Path(sys._MEIPASS)  # type: ignore[attr-defined]
```

---

## mypy: Variable annotations (var-annotated)

Add explicit types so mypy can check assignments. Use `from typing import Any` where needed.

| File | Line | Variable | Suggested annotation |
|------|------|----------|----------------------|
| `src/vnetmap_parser.py` | 23–25 | `raw_data`, `topology_data`, `cross_connections` | `list[Any]` (or more specific if you have a type for parsed items) |
| `src/vnetmap_parser.py` | 136 | `connections_by_switch` | `dict[str, Any]` |
| `src/vnetmap_parser.py` | 157 | `connections_by_node` | `dict[str, Any]` |
| `src/enhanced_report_builder.py` | 268 | `rack_groups` | `dict[str, Any]` |
| `src/enhanced_report_builder.py` | 291 | `drack_groups` | `dict[str, Any]` (or fix typo to `dbox_groups` if intended) |
| `src/comprehensive_report_template.py` | 1017 | `rack_groups` | `dict[str, Any]` |
| `src/comprehensive_report_template.py` | 1036 | `drack_groups` | `dict[str, Any]` |
| `src/port_mapper.py` | 42–43 | `cnode_to_cbox`, `dnode_to_dbox` | `dict[str, str]` or `dict[str, Any]` |
| `src/enhanced_port_mapper.py` | 375 | `ipl_connections` | `list[Any]` |
| `src/data_extractor.py` | 563 | `rack_layout` | `dict[str, Any]` |
| `src/report_builder.py` | 182 | `switch_positions` | `dict[str, Any]` |
| `src/report_builder.py` | 639, 913, 1124 | `toc_table_data` | `list[Any]` |
| `src/report_builder.py` | 1442 | `cbox_to_cnode_names` | `dict[str, list[str]]` or `dict[str, Any]` |
| `src/report_builder.py` | 1500 | `dbox_to_dnode_names` | same as above |
| `src/report_builder.py` | 2117 | `racks_data` | `dict[str, Any]` |
| `src/report_builder.py` | 3561 | `ports_by_switch` | `dict[str, Any]` |
| `src/report_builder.py` | 3894 | `port_summary` | `dict[str, Any]` |
| `src/external_port_mapper.py` | 301–302 | `switch_os_map`, `switch_credentials` | `dict[str, Any]` (or more specific) |
| `src/external_port_mapper.py` | 940 | `node_macs` | `dict[str, str]` or `dict[str, Any]` |
| `src/api_handler.py` | 231 | `supported_features` | `set[str]` |
| `src/api_handler.py` | 777 | `headers` | `dict[str, str]` |

Example for `api_handler.py`:

```python
self.supported_features: set[str] = set()
```

Example for a dict:

```python
rack_groups: dict[str, Any] = {}
```

---

## mypy: Return type fixes (no-any-return, return-value)

When a function is declared to return `list[Any]`, `dict[str, Any]`, `str`, etc., but the implementation returns a value mypy infers as `Any` or a broader type, use an explicit cast or fix the type.

**Option A — `typing.cast` (minimal code change):**

```python
from typing import cast

# In the return statement, e.g.:
return cast(list[Any], some_expression)
```

Apply this at:

- `src/enhanced_report_builder.py`: 384, 405, 409, 413, 532, 603, 607, 611
- `src/rack_diagram.py`: 42, 233, 292
- `src/network_diagram.py`: 39 (return `dict[str, Any]`)
- `src/data_extractor.py`: 1852 (return `bool`)
- `src/report_builder.py`: 1667
- `src/api_handler.py`: 813, 2199, 2232

**Option B — Fix the value type:** e.g. in `enhanced_port_mapper.py` (297, 299, 306) the return type is `str` but the code can return `int | Any | str`. Ensure a string is always returned (e.g. `return str(...)` or narrow the branches so only `str` is returned).

---

## mypy: `api_handler.py` — `self.session` and related (None has no attribute "…")

`self.session` is initialized as `None` and later set to a `requests.Session`. mypy doesn't narrow the type after `if not self.session: self.session = ...`.

**Approach 1 — Assert after assignment (minimal change):**

After the block that sets `self.session`, add:

```python
assert self.session is not None
```

Then use `self.session` in the rest of the method. Repeat in every method that uses `self.session` after ensuring it's set.

**Approach 2 — Type and narrow at use (clearer long-term):**

- Keep `self.session: Optional[requests.Session] = None` (or `Session | None`).
- In each method that uses `self.session`, narrow at the top:

  ```python
  if self.session is None:
      return False  # or raise, or set it first
  # use self.session here
  ```

**Approach 3 — Use a local variable:**

```python
session = self.session
if session is None:
    session = self._setup_session()
    self.session = session
# use session (mypy knows it's Session here)
```

Same idea applies to `self.base_url`, `self.api_token`, etc.: either give them optional types and narrow before use, or set them in `__init__` to a sentinel and assert/narrow where needed.

---

## mypy: `api_handler.py` — Incompatible assignments

- **330–332, 352, 423, etc.** — Variables are inferred as `None` (e.g. from `self.base_url = None`). When you assign a string or `Session`, mypy complains. Fix by declaring the attribute with a union type in `__init__`:

  ```python
  self.base_url: str | None = None
  self.session: requests.Session | None = None
  self.api_token: str | None = None
  # ...
  ```

  Then narrow with `if self.session is None: ...` or assert before use.

- **1810, 1827, 1864** — Variable typed as `dict[str, Any]` but assigned a `VastClusterInfo`. Either change the variable type to `VastClusterInfo | dict[str, Any]` or store the dataclass and build the dict only where needed.

- **1962–1968** — "List item has incompatible type dict[str, str]; expected str". The list is typed as `list[str]` but you're appending dicts. Change the list type to e.g. `list[dict[str, str]]` or `list[Any]` at the point of definition.

---

## mypy: `network_diagram.py` — int/float and Path/str

- **211–213** — Variables used as dimensions are assigned floats (e.g. `device_width = min(40, ...)`). Either:
  - Declare them as `float` and use `int()` only where an int is required (e.g. for font size), or
  - Use `int()` at assignment: `device_width = int(min(40, ...))` if they are always used as integers.

- **481–489, 525** — Parameter `output_path` is typed as `str`, but the code does `output_path = Path(output_path)` and then uses `.parent`, `.with_suffix`, `.name`. Fix by using a separate variable:

  ```python
  output_path_p = Path(output_path)
  output_path_p.parent.mkdir(parents=True, exist_ok=True)
  # ...
  png_path = output_path_p.with_suffix(".png")
  # and later: str(png_path.parent), str(png_path.name), etc.
  ```

  Or change the parameter type to `str | Path` and keep a single variable.

---

## mypy: `report_builder.py` — int/float and tuple length

- **960, 1167** — "expression has type float, variable has type int". Either change the variable type to `float` or wrap in `int()` when the value is used as an integer.

- **1560, 1564** — In the "no dnodes" branch, `dbox_rows` is a list of 3-tuples `(rack_name, dbox_id, row)`, but elsewhere (when dnodes exist) you use 4-tuples `(rack_name, dbox_id, dnode_name, row)`. So `all_rows` is inferred from the 4-tuple branch. Make the fallback branch use the same shape:

  ```python
  # Line 1559: keep 3-tuple for sorting but use 4-tuple for extend
  dbox_rows.append((rack_name, dbox_id, "N/A", row))
  # Line 1561: same unpacking as the other branch
  all_rows.extend([row for _, _, _, row in dbox_rows])
  ```

  Then the 4-tuple branch and the 3-tuple branch both become 4-tuples; use `row for _, _, _, row in dbox_rows` in both places so the list type is consistent.

---

## Suggested order of work

1. **Already done:** Black on `src/main.py` and `src/app.py`.
2. Add `types-paramiko` to `requirements-dev.txt` and install; fix `utils/__init__.py` `_MEIPASS` (quick wins).
3. Add variable annotations (var-annotated) in small batches by file; run mypy after each batch.
4. Fix return types (no-any-return) with `cast` or by returning the correct type.
5. Fix `api_handler.py` session/optional attributes (type declarations + narrowing).
6. Fix `network_diagram.py` (Path vs str, int vs float).
7. Fix `report_builder.py` (tuple consistency, int/float, annotations).

If you want to get CI green quickly without fixing every mypy error, you can temporarily relax mypy in `pyproject.toml` (e.g. add `[[tool.mypy.overrides]]` to exclude certain files or turn off specific error codes), but the above gives a clear path to fixing the 97 errors properly.
