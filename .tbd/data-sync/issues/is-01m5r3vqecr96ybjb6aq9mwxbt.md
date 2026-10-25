---
type: is
id: is-01m5r3vqecr96ybjb6aq9mwxbt
title: "PR #13 E1: bind plans to ranking profile and generation"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.099Z
updated_at: 2026-10-25T04:45:23.055Z
started_at: 2026-10-24T23:28:00.530Z
closed_at: 2026-10-25T04:45:23.055Z
close_reason: Fixed in merged Paraverse PR13, merge b9d1815d27aae9fbe0919a4ed78b94ce61d1d80a. Independent F/G/H verify workspace people, generation ownership, sidebar cards, canonical venue, MCP lifecycle and captured recipients; final combined 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/13#issuecomment-6393516949; duplicate C1 beads share one implemented fix.
resolution: null
duplicate_of: null
---
Review5640567860 E1 and Qodo r4368919499/r4368861855. Include title/background in normalized ranking fingerprint; invalidate stale visible plans and reject in-flight responses after profile changes; preserve new request loading ownership. Add edit/restore and edit-across-await regressions.

## Notes

Own commit161cf5d on isolated17388 base. RED5 assertions reproduced ranking-edit restoration/current-plan staleness and old task clearing new loading; GREEN full39Swift release18.583s. Captured generation rejects stale async results, title/background/identity/interests fingerprint invalidates visible plan. Parent integrates; no push.
