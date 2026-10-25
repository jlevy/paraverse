---
type: is
id: is-01m5qxs5bxx90pbm5ahcbv951s
title: Fix per-slot end times for repeated sessions
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T21:41:29.596Z
updated_at: 2026-10-25T01:51:13.900Z
started_at: 2026-10-25T01:51:13.900Z
---
At audited 6fc8c39, queries.py:180 returns Session.end, but mapping.py:205-212 sets it to latest end across all slots. Seven original sessions repeat; earlier slots may end the next day. Export slot end/end_epoch on SCHEDULED_ON/HELD_IN and query per-slot end. Add focused multi-slot coverage. Source exporter is in Universe pipeline; coordinate there. Parent audit pv-67zv.
