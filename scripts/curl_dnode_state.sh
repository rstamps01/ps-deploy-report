#!/usr/bin/env bash
# Fetch DNode(s) from VAST API v7 and print state (and optional full JSON).
# Usage: ./scripts/curl_dnode_state.sh [dnodes_url]
# Default: https://10.27.200.118/api/v7/dnodes/
# Set VAST_USER, VAST_PASS (or use support:654321) for Basic auth.

set -e
BASE="${1:-https://10.27.200.118/api/v7/dnodes}"
USER="${VAST_USER:-support}"
PASS="${VAST_PASS:-654321}"

RAW=$(curl -s -k -u "${USER}:${PASS}" "$BASE")

# Show first 500 chars of raw response (for debugging)
echo "=== Raw response (first 500 chars) ==="
echo "$RAW" | head -c 500
echo ""
echo "=== End raw ==="

# Parse: single JSON (object or array), or dict keyed by name
echo ""
echo "=== Parsed DNode state (id 2 or name dnode-128-104-4000) ==="
echo "$RAW" | python3 -c "
import sys, json

raw = sys.stdin.read()
# Strip BOM and outer whitespace
raw = raw.lstrip('\ufeff').strip()
if not raw:
    print('Empty response')
    sys.exit(1)

# Decode first JSON value; if null/empty and there is more, try the rest (some APIs send null then payload)
decoder = json.JSONDecoder()
try:
    data, idx = decoder.raw_decode(raw)
    rest = raw[idx:].strip()
    if (data is None or (isinstance(data, list) and len(data) == 0)) and rest:
        try:
            data, _ = decoder.raw_decode(rest)
        except json.JSONDecodeError:
            pass
except json.JSONDecodeError as e:
    print('JSON error:', e, file=sys.stderr)
    print('First 300 chars:', repr(raw[:300]))
    sys.exit(1)

# Normalize to list (VAST can return list, or dict keyed by name)
if isinstance(data, list):
    items = data
elif isinstance(data, dict):
    items = data.get('results') or data.get('data') or data.get('dnodes')
    if items is None:
        # Dict of dnodes keyed by name: { 'dnode-1-0': {...}, ... }
        first = next(iter(data.values()), None)
        if isinstance(first, dict) and ('id' in first or 'name' in first):
            items = list(data.values())
        elif 'id' in data or 'name' in data:
            items = [data]
        else:
            items = []
    elif not isinstance(items, list):
        items = []
else:
    items = []

for d in items:
    if d is None or not isinstance(d, dict):
        continue
    if d.get('id') == 2 or d.get('name') == 'dnode-128-104-4000':
        print('id:', d.get('id'), '| name:', d.get('name'), '| state:', d.get('state'))
        break
else:
    print('DNode id=2 or name=dnode-128-104-4000 not found. Total items:', len(items))
    for d in items[:3]:
        if isinstance(d, dict):
            print('  Sample:', d.get('id'), d.get('name'), d.get('state'))
"
