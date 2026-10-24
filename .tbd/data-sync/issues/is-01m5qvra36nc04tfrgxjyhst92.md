---
type: is
id: is-01m5qvra36nc04tfrgxjyhst92
title: "PR #6 qodo-5639989300 #1: a failed reload leaves the graph stale (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: in_progress
priority: 1
version: 4
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:04.516Z
updated_at: 2026-10-24T21:24:11.706Z
started_at: 2026-10-24T21:06:12.353Z
---
Severity: High, Action required (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488645. Location: db/src/paraverse_graph/cli.py:355-367 (watch_kb). watch_kb assigns the new stats.json signature to seen before calling reload() and keeps it when the load fails, so a reload that read an incomplete rebuild is never retried and the live graph stays on the previous build. Suggested fix: track the last successfully loaded signature separately and retry a failed one after a delay, without a busy loop for a persistently invalid build.
