---
type: is
id: is-01m5r3880aqp4vd0z5nqek7mjy
title: "PR13 C1: render event-session answers in sidebar chat"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
hold: null
hold_until: null
created_at: 2026-10-24T23:17:06.696Z
updated_at: 2026-10-25T04:45:10.467Z
started_at: 2026-10-25T04:45:10.467Z
---
Medium finding C1 from https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640541744 at7f9d33b. native/Sources/CommonGround/App.swift:275–285 ignores Message.eventSessions, although Plan.swift populates them and backend returns only an intro when cards are present. Render the same session cards/calendar actions in the sidebar as the world planner; verify both presentation paths. Addressing owner should triage priority versus a separate follow-up PR.
