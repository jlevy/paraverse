---
type: is
id: is-01m5r464z3qktjxnp1h1dhyhgm
title: "PR13 Qodo r4368919496: retain late arrival on external refresh"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:33:26.626Z
updated_at: 2026-10-25T01:09:24.985Z
started_at: 2026-10-25T00:21:09.226Z
closed_at: 2026-10-25T01:09:24.985Z
close_reason: "Fixed in5a1a3e9 on published PR13 head0333a174: logout clears draft, restorable workspace and cached plan people; late-arrival state reaches external refresh and backend selection. Meaningful RED/GREEN profile/plan and morning-versus-afternoon regressions.49 PR13 backend and40 release Swift tests pass; combined top69backend60Swift pass."
resolution: null
duplicate_of: null
---
Review5640576707 r4368919496 Medium: external refresh omits saved late flag. Deferred per user merge-soon instruction; send late value and test retry after late-arrival. Related existing A4 pv-6nme busy-period follow-up.
