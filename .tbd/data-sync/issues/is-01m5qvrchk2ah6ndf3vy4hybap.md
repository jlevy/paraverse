---
type: is
id: is-01m5qvrchk2ah6ndf3vy4hybap
title: "PR #6 qodo-5639989300 #6: each failed watch reload leaves a full graph copy behind (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
created_at: 2026-10-24T21:06:07.026Z
updated_at: 2026-10-24T21:06:07.026Z
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488660. Location: db/src/paraverse_graph/loader.py:101-187 (load_graph). load_graph keeps its uniquely named staging graph when a later step raises, and serve --watch catches the reload error and keeps running, so every broken KB build adds another full graph copy to the persistent store. Suggested fix: delete this load's own staging graph on failure, with keeping it for inspection opt-in.
