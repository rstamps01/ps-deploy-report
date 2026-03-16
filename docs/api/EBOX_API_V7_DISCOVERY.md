# EBox-Related Data Gathering — VAST API v7

EBox (Enclosure Box) is an optional VAST infrastructure component. This document lists **all ebox-related API v7 endpoints and response fields** for integration into the As-Built Report Generator.

---

## 1. API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/v7/eboxes/` | GET | List EBox enclosures (id, name, state, rack, etc.). May return 404 if cluster has no EBoxes. |
| `GET /api/v7/clusters/` | GET | Cluster-level flag `ebox` (boolean) indicates EBox presence. |
| `GET /api/v7/cnodes/` | GET | Each CNode can have `ebox_id` linking to an EBox. |
| `GET /api/v7/dnodes/` | GET | Each DNode can have `ebox_id` linking to an EBox. |

---

## 2. Response Fields

### 2.1 Cluster — `GET /api/v7/clusters/`

| Field | Type | Description |
|-------|------|-------------|
| `ebox` | boolean | Whether the cluster has EBox enclosures. |

### 2.2 CNodes — `GET /api/v7/cnodes/`

| Field | Type | Description |
|-------|------|-------------|
| `ebox_id` | int or null | ID of the EBox this CNode belongs to, if any. |

### 2.3 DNodes — `GET /api/v7/dnodes/`

| Field | Type | Description |
|-------|------|-------------|
| `ebox_id` | int or null | ID of the EBox this DNode belongs to, if any. |

### 2.4 EBoxes — `GET /api/v7/eboxes/`

Expected shape (to be confirmed by probing a cluster with EBoxes): list of objects with fields such as:

- `id` — EBox ID
- `name` — EBox name
- `guid` — GUID
- `state` — Operational state
- `cluster`, `cluster_id` — Cluster reference
- `rack_id`, `rack_name`, `rack_unit`, `index_in_rack` — Rack positioning (if supported)

The exact schema can be discovered by running `export_swagger.py` against a cluster that has EBoxes, or by inspecting Swagger at `https://<management-vip>/api`.

---

## 3. Data Gathering Strategy

1. **Cluster flag**: Read `cluster_info.ebox` from `clusters/` to know if EBoxes are in use.
2. **EBox list**: Call `GET /api/v7/eboxes/`. On 200, parse list and key by name (same pattern as cboxes/dboxes). On 404 or empty, treat as no EBoxes.
3. **Node association**: When processing cnodes/dnodes, include `ebox_id` so the report can show which nodes belong to which EBox.
4. **Report**: Add EBox count to hardware overview; optionally add an EBox inventory table and node-to-ebox mapping.

---

## 4. References

- VAST CLI: `ebox add`, `ebox modify`, `ebox replace` (see [ebox create](https://kb.vastdata.com/documentation/docs/ebox-create)).
- Cluster export catalog: `docs/api/swagger_selab-var-202_v7_20260310.json` — contains `ebox` (clusters), `ebox_id` (cnodes, dnodes). The `eboxes/` endpoint is not in the current probe list; add it to `scripts/export_swagger.py` to discover fields on clusters with EBoxes.
