---
type: is
id: is-01m5r08p8fsv9p1fxx2z8fycxc
title: "PR #6 Qodo r4368735626: reject graph nodes without matching artifact IDs"
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T22:24:55.551Z
updated_at: 2026-10-24T22:25:17.593Z
started_at: 2026-10-24T22:25:17.584Z
---
High finding https://github.com/jlevy/paraverse/pull/6#discussion_r4368735626. payload_for returns None when the graph ID is absent from the root or nested artifact payload; node_properties silently accepts it and counts pass. Reject unresolved IDs before publishing staging graph and prove the live graph stays unchanged.
