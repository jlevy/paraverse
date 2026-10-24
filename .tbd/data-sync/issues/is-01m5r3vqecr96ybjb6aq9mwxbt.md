---
type: is
id: is-01m5r3vqecr96ybjb6aq9mwxbt
title: "PR #13 E1: bind plans to ranking profile and generation"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.099Z
updated_at: 2026-10-24T23:28:00.532Z
started_at: 2026-10-24T23:28:00.530Z
---
Review5640567860 E1 and Qodo r4368919499/r4368861855. Include title/background in normalized ranking fingerprint; invalidate stale visible plans and reject in-flight responses after profile changes; preserve new request loading ownership. Add edit/restore and edit-across-await regressions.
