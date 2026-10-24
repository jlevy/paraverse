---
type: is
id: is-01m5qvra36nc04tfrgxjyhst92
title: "PR #6 qodo-5639989300 #1: a failed reload leaves the graph stale (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 1
version: 5
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:04.516Z
updated_at: 2026-10-24T21:29:47.263Z
started_at: 2026-10-24T21:06:12.353Z
closed_at: 2026-10-24T21:29:47.261Z
close_reason: "Fixed in 7bc4f4c42ce928a67d74d26b27c6c3a369715b48 (fix(db): finish graph browser review corrections). New regression tests failed before the corresponding fixes; make lint now passes with 0 errors/warnings and make test passes all 89 tests. Retry/backoff, KB mutation guards, epoch sorting, capacity threshold, sponsor aggregation, missed-event cache refresh and dataset collisions are covered."
resolution: null
duplicate_of: null
---
Severity: High, Action required (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488645. Location: db/src/paraverse_graph/cli.py:355-367 (watch_kb). watch_kb assigns the new stats.json signature to seen before calling reload() and keeps it when the load fails, so a reload that read an incomplete rebuild is never retried and the live graph stays on the previous build. Suggested fix: track the last successfully loaded signature separately and retry a failed one after a delay, without a busy loop for a persistently invalid build.
