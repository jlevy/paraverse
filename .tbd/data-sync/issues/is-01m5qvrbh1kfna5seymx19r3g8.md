---
type: is
id: is-01m5qvrbh1kfna5seymx19r3g8
title: "PR #6 qodo-5639989300 #4: large rooms fail the placeholder check (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
created_at: 2026-10-24T21:06:05.983Z
updated_at: 2026-10-24T21:06:05.983Z
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488655. Location: db/src/paraverse_graph/review.py:150-155 (placeholder_capacity). placeholder_capacity flags every room with capacity of at least 5,000, although the check describes catalog placeholders as capacities of 9,999 or more, so a legitimate large room is reported as a high-severity review finding. Suggested fix: use the documented 9,999 threshold, with boundary tests.
