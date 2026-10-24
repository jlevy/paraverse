---
type: is
id: is-01m5r3vqecr96ybjb6aq9mwxbt
title: "PR #13 E1: bind plans to ranking profile and generation"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.099Z
updated_at: 2026-10-24T23:35:19.603Z
started_at: 2026-10-24T23:28:00.530Z
---
Review5640567860 E1 and Qodo r4368919499/r4368861855. Include title/background in normalized ranking fingerprint; invalidate stale visible plans and reject in-flight responses after profile changes; preserve new request loading ownership. Add edit/restore and edit-across-await regressions.

## Notes

Own commit161cf5d on isolated17388 base. RED5 assertions reproduced ranking-edit restoration/current-plan staleness and old task clearing new loading; GREEN full39Swift release18.583s. Captured generation rejects stale async results, title/background/identity/interests fingerprint invalidates visible plan. Parent integrates; no push.
