---
type: is
id: is-01m5r2kdfxm7ajwp7e9vt148hd
title: "PR #13 A2: preserve people recommendations across profile restore"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:05:44.188Z
updated_at: 2026-10-24T23:05:44.188Z
---
PR #13 senior review A2 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. Medium. native/Sources/CommonGround/Onboarding.swift:82 omits lastPlanPeople from workspaceKeys, while Plan.swift:86 writes and Plan.swift:261 restores it. Profile A -> B -> restore A retains B people recommendations. Add lastPlanPeople to snapshot/clear/restore lifecycle and verify a two-profile round trip. Deferred under user merge-first authorization; waits on current native stack landing before the profile workspace follow-up.
