---
type: is
id: is-01m5r2kdfxm7ajwp7e9vt148hd
title: "PR #13 A2: preserve people recommendations across profile restore"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:05:44.188Z
updated_at: 2026-10-25T04:45:22.964Z
started_at: 2026-10-25T04:45:10.444Z
closed_at: 2026-10-25T04:45:22.958Z
close_reason: Fixed in merged Paraverse PR13, merge b9d1815d27aae9fbe0919a4ed78b94ce61d1d80a. Independent F/G/H verify workspace people, generation ownership, sidebar cards, canonical venue, MCP lifecycle and captured recipients; final combined 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/13#issuecomment-6393516949; duplicate C1 beads share one implemented fix.
resolution: null
duplicate_of: null
---
PR #13 senior review A2 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. Medium. native/Sources/CommonGround/Onboarding.swift:82 omits lastPlanPeople from workspaceKeys, while Plan.swift:86 writes and Plan.swift:261 restores it. Profile A -> B -> restore A retains B people recommendations. Add lastPlanPeople to snapshot/clear/restore lifecycle and verify a two-profile round trip. Deferred under user merge-first authorization; waits on current native stack landing before the profile workspace follow-up.
