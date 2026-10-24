---
type: is
id: is-01m5qvrchk2ah6ndf3vy4hybap
title: "PR #6 qodo-5639989300 #6: each failed watch reload leaves a full graph copy behind (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:07.026Z
updated_at: 2026-10-24T21:15:34.045Z
started_at: 2026-10-24T21:13:20.086Z
closed_at: 2026-10-24T21:15:34.033Z
close_reason: "fixed in 'fix(db): delete the staging graph of a failed watch reload' (89cc4fb before restack): load_graph takes keep_failed; the serve --watch reload passes False, so a failed attempt deletes only its own staging graph; manual loads still keep it for inspection, as documented. Confirmed by tests/test_graph.py::test_failed_watch_reloads_delete_their_staging_graphs (failed before the fix)."
resolution: null
duplicate_of: null
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488660. Location: db/src/paraverse_graph/loader.py:101-187 (load_graph). load_graph keeps its uniquely named staging graph when a later step raises, and serve --watch catches the reload error and keeps running, so every broken KB build adds another full graph copy to the persistent store. Suggested fix: delete this load's own staging graph on failure, with keeping it for inspection opt-in.
