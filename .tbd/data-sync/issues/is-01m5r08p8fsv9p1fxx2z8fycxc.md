---
type: is
id: is-01m5r08p8fsv9p1fxx2z8fycxc
title: "PR #6 Qodo r4368735626: reject graph nodes without matching artifact IDs"
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
created_at: 2026-10-24T22:24:55.551Z
updated_at: 2026-10-24T22:24:55.551Z
---
High finding https://github.com/jlevy/paraverse/pull/6#discussion_r4368735626. payload_for returns None when the graph ID is absent from the root or nested artifact payload; node_properties silently accepts it and counts pass. Reject unresolved IDs before publishing staging graph and prove the live graph stays unchanged.
