---
type: is
id: is-01m5qxs5bxx90pbm5ahcbv951s
title: Fix per-slot end times for repeated sessions
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
created_at: 2026-10-24T21:41:29.596Z
updated_at: 2026-10-24T21:41:29.596Z
---
At audited 6fc8c39, queries.py:180 returns Session.end, but mapping.py:205-212 sets it to latest end across all slots. Seven original sessions repeat; earlier slots may end the next day. Export slot end/end_epoch on SCHEDULED_ON/HELD_IN and query per-slot end. Add focused multi-slot coverage. Source exporter is in Universe pipeline; coordinate there. Parent audit pv-67zv.
