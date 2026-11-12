# TP-3 — Tech Port discovery reports `management=192.168.2.2`

**Type:** Bug (investigate) · **Priority:** P3 · **Size:** S · **Target:** v1.6.3 · **Status:** Planned; needs a
repro.

## Observed

A field ops log shows `Tech Port: VMS discovered (internal=..., management=192.168.2.2)`. The tunnel still
worked, but anything that uses the management IP got the Tech Port address, and Network Extraction counted the
gateway twice.

## Where

`discover_vms_management_ip` (`src/utils/vms_tunnel.py` L267+): `/etc/motd` or `clush`, then the 443
short-circuit (L330–347), then the `ip addr` hop. Callers log and use the result: `oneshot_runner.py` L673, L686–697
and L1313; `app.py` L1813 and L2656–2660; `main.py` L190–194.

## Hypotheses (confirm against the field ops log and a lab Tech Port session first)

1. The 443 short-circuit accepts an internal IP that answers on 443 only through the Tech Port forwarding, so
   the internal IP equals the entry host.
2. The `ip addr` parser picks the Tech Port interface (`192.168.2.x`) because RFC1918 /16 addresses are allowed
   since TP-1.

## Change (once the cause is confirmed)

- The management IP is never the entry host or a Tech Port link address. When it can't be resolved, it is
  `None`, the log says "management IP not resolved", and callers fall back as they do today without treating
  the Tech Port address as management.
- Network Extraction de-duplicates the gateway.

## Acceptance

- Failing-first: a fixture of the field `ip addr` / motd output (scrubbed) reproduces `management=192.168.2.2`;
  after the fix it is the real management IP or `None`.
- If no repro is possible before the release cut, TP-3 moves to v1.7.0 with the reason recorded, and the
  release is not held for it.
