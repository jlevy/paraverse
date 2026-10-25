---
type: is
id: is-01m5r9d8z11zqajn5xr0g5sv0j
title: Investigate stale Knowledge Base overview endpoints
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:04:42.977Z
updated_at: 2026-10-25T04:41:27.713Z
started_at: 2026-10-25T01:51:14.028Z
closed_at: 2026-10-25T04:41:27.712Z
close_reason: Diagnosed the unrelated older 8766 service missing newer routes; verified current 8879 overview and dataset endpoints after owned runtime recovery. 8766 was not changed.
resolution: null
duplicate_of: null
---
Observed while verifying slash search in Paraverse Final: existing browser service on port 8766 returns Not Found for overview sections, while metadata, entity pages, and search work. Overview source changes are present, so check whether a reused older browser process needs a controlled refresh before changing code. Separate from fixed slash-search layout pv-2d1y.

## Notes

Reconciled against Universe main a82367923bee34147da575dbd0cef17b5bc285a8, Paraverse PR16 merge 83784693e74e18a725156584a578590134cf41dd and current native stack b33f9fb98a97fd177729edc81743ad05b5b3edef. Diagnosis complete: the existing 8766 listener is the older common-ground cg-graph process (PID10874, created 2026-10-24 11:50:14 local). Read-only HTTP confirms /api/meta=200 but /api/overview=404 and /api/datasets=404. Current browser source contains both routes; the root-owned 8879 runtime serves them. Port8766 was neither stopped nor refreshed, and no native8766 refresh is claimed. A separate external-volume disconnect later killed the private Redis behind 8879 and caused 503 responses; after the parent remounted the volume, the exact owned Python14337 was stopped gracefully and the fixed cleanup wrapper restarted with a fresh private DB. Recovered 8879 /api/meta, /api/datasets, /api/overview all return200, both final datasets selected, digest9baef37f427f91a6, 5,536 nodes/25,564 edges; Python51307/Redis51317, exec session38433. Unrelated 8766 PID10874 and18866 PID69761 retain their original creation times. No source fix was needed for this stale-route investigation. Recovery evidence: /private/tmp/claude-502/-Users-levy-wrk-github-paraverse/d31a7712-52d0-48af-a28f-fa903f3a5198/scratchpad/review/dataset-readiness-8879-recovered.json
