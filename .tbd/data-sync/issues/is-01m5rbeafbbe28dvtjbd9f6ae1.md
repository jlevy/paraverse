---
type: is
id: is-01m5rbeafbbe28dvtjbd9f6ae1
title: "PR13 r4369238731: initialize authenticated MCP sessions before tools"
kind: bug
status: closed
priority: 1
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:40:14.440Z
updated_at: 2026-10-25T04:45:23.083Z
started_at: 2026-10-25T01:40:30.314Z
closed_at: 2026-10-25T04:45:23.083Z
close_reason: Fixed in merged Paraverse PR13, merge b9d1815d27aae9fbe0919a4ed78b94ce61d1d80a. Independent F/G/H verify workspace people, generation ownership, sidebar cards, canonical venue, MCP lifecycle and captured recipients; final combined 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/13#issuecomment-6393516949; duplicate C1 beads share one implemented fix.
resolution: null
duplicate_of: null
---
High in review5640939881: https://github.com/jlevy/paraverse/pull/13#discussion_r4369238731 . backend/luma_mcp.py lacks required initialize/initialized lifecycle. Implement official2025-03-26 lifecycle, session binding and explicit-expiry recovery without replaying mutating tools. Fully mocked transport tests only.

## Notes

Fixed in isolated commit0a3bde7d44ef6e384bc63b5b79817aa6262de4c1 (base8cf5b045). Official Luma https://help.luma.com/p/mcp documents Streamable HTTP; MCP2025-03-26 lifecycle/transports require initialize then initialized even without assigned sessionID. Implemented token-bound serialized lifecycle, optional sessionID retention, correlated JSON/SSE results and one read-only expiry recovery. create_event/invite_guests never replayed after404/timeout/503. Eight mocked transport tests RED10failures+2errors -> GREEN8; full69backendtestsPASS0.219s; focused Ruff/diffcheckPASS. No live provider calls or push; root owns integration/closure/dispositions.
