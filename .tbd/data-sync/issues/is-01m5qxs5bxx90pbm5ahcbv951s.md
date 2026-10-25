---
type: is
id: is-01m5qxs5bxx90pbm5ahcbv951s
title: Fix per-slot end times for repeated sessions
kind: bug
status: open
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T21:41:29.596Z
updated_at: 2026-10-25T04:41:26.557Z
started_at: 2026-10-25T01:51:13.900Z
---
At audited 6fc8c39, queries.py:180 returns Session.end, but mapping.py:205-212 sets it to latest end across all slots. Seven original sessions repeat; earlier slots may end the next day. Export slot end/end_epoch on SCHEDULED_ON/HELD_IN and query per-slot end. Add focused multi-slot coverage. Source exporter is in Universe pipeline; coordinate there. Parent audit pv-67zv.

## Notes

Reconciled against Universe main a82367923bee34147da575dbd0cef17b5bc285a8, Paraverse PR16 merge 83784693e74e18a725156584a578590134cf41dd and current native stack b33f9fb98a97fd177729edc81743ad05b5b3edef. The defect remains valid: db/src/paraverse_graph/queries.py:180 returns s.end, and mapping.py _session_fields sets that to the latest end across all slots. Universe pipeline graph.py exports only each slot start on scheduled_on/held_in. Current final data has seven repeated sessions and eight earlier-slot ends that differ from the session-wide latest end: four sessions/five earlier slots in 2026 and three sessions/three earlier slots in 2024. Therefore this is not historical-only; browser named schedule queries can report wrong 2026 end times. Native planning is unaffected: backend/export_kb_native.py:177 uses each slot's own end, and all 161 current native session rows match their exact source slot end (zero mismatches). Keep OPEN P2 per parent-approved nonpressing follow-up, scoped to exporting per-slot end/end_epoch and querying them with multi-slot regression coverage. Coordinate the Universe graph export and Paraverse query layers; no code change made in this reconciliation. Related consumer-query follow-up u26-pw1e. Evidence: /private/tmp/claude-502/-Users-levy-wrk-github-paraverse/d31a7712-52d0-48af-a28f-fa903f3a5198/scratchpad/review/dataset-readiness-stale-bead-reconciliation.json
