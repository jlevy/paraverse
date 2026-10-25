---
type: is
id: is-01m5r2ke2037n1k33cvqmvh70n
title: "PR #13 A4: retain selected-calendar conflicts during external-event refresh"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:05:44.767Z
updated_at: 2026-10-25T00:19:55.511Z
started_at: 2026-10-25T00:19:55.510Z
---
PR #13 senior review A4 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. Medium. native/Sources/CommonGround/Plan.swift:222-223 refresh sends planned sessions as busy but omits selected-calendar appointments included during initial generation. Share occupied-time collection, calendar connection flag and timing constraints between both flows. Calendar writes already recheck conflicts. Deferred under user merge-first authorization; waits on current native stack landing before calendar availability follow-up.
