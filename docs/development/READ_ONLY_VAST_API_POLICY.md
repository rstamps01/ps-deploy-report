# Read-Only VAST API Policy

**Applies to:** All API usage, tests, validation, and development for the VAST As-Built Report Generator.

## Policy

This application is **exclusively a report-generation tool**. It must:

- **Only gather and report data** about VAST Data clusters.
- **Never use VAST API calls that create, update, or delete** cluster configuration, settings, or resources.

## Allowed

- **Read-only (GET) requests** for cluster data: clusters, cnodes, dnodes, cboxes, dboxes, eboxes, racks, network settings, tenants, views, security config, monitoring config, etc.
- **Authentication** that is required to establish read-only access:
  - Using a **pre-provided API token** (preferred).
  - **Basic auth** (username/password) for session establishment.
  - **Session / JWT login** (POST to sessions or jwt only to obtain a session or token for subsequent GETs).
  - **Creating an API token** via POST to `apitokens/` only when no valid token exists, solely to perform read-only data collection. Prefer providing a token or using basic auth to avoid creating tokens.

## Not allowed

- Any VAST API call that **creates, updates, or deletes** cluster configuration, resources, or settings (e.g. creating tenants, modifying network config, changing views, deleting resources).
- Using **PUT, PATCH, or DELETE** in the data-collection path. The generic `_make_api_request()` in `api_handler` is restricted to **GET only** for all data collection.

## Enforcement

- In `src/api_handler.py`, `_make_api_request()` accepts **only GET**. Any other method raises `ValueError`.
- All data-collection methods use `_make_api_request(endpoint)` (default GET). Authentication may use direct `session.post()` only for login/token endpoints.
- Tests and validation must mock only read operations or auth; no tests should trigger cluster-modifying VAST API calls.

## References

- `.cursor/rules/api-handler-05.mdc` — API handler conventions and read-only policy.
- `src/api_handler.py` — implementation; all `_make_api_request` call sites use GET.
