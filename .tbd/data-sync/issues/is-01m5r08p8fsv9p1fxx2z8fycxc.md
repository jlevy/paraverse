---
type: is
id: is-01m5r08p8fsv9p1fxx2z8fycxc
title: "PR #6 Qodo r4368735626: reject graph nodes without matching artifact IDs"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T22:24:55.551Z
updated_at: 2026-10-24T22:50:38.653Z
started_at: 2026-10-24T22:25:17.584Z
closed_at: 2026-10-24T22:50:38.653Z
close_reason: "Fixed and landed in Paraverse PRs #6–#8, merged 2026-10-24 at main beabb16f0332ce6afcdb047b12cdb04b4dc59025. Combined owning-layer suite: 143 passed, clean exit; lint/format/type checks passed. Final independent reviews PV6F (5640363560) and PV8E (5640363811) report no findings. Qodo dispositions: PR6 comments 6390252206, 6390447043; PR8 comments 6390252630, 6390447546. User explicitly approved merging with local checks because neither repo has CI configured."
resolution: null
duplicate_of: null
---
High finding https://github.com/jlevy/paraverse/pull/6#discussion_r4368735626. payload_for returns None when the graph ID is absent from the root or nested artifact payload; node_properties silently accepts it and counts pass. Reject unresolved IDs before publishing staging graph and prove the live graph stays unchanged.
