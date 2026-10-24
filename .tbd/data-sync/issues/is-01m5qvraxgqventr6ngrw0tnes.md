---
type: is
id: is-01m5qvraxgqventr6ngrw0tnes
title: "PR #6 qodo-5639989300 #3: session time sorting can be out of order (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:05.358Z
updated_at: 2026-10-24T21:29:47.278Z
started_at: 2026-10-24T21:23:17.191Z
closed_at: 2026-10-24T21:29:47.278Z
close_reason: "Fixed in 7bc4f4c42ce928a67d74d26b27c6c3a369715b48 (fix(db): finish graph browser review corrections). New regression tests failed before the corresponding fixes; make lint now passes with 0 errors/warnings and make test passes all 89 tests. Retry/backoff, KB mutation guards, epoch sorting, capacity threshold, sponsor aggregation, missed-event cache refresh and dataset collisions are covered."
resolution: null
duplicate_of: null
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488653. Location: db/src/paraverse_graph/browser.py:884-902 (_sort_key), mapping.py:203-212. _sort_key orders the session start and end columns as offset-bearing timestamp strings rather than by their stored epoch values, so sessions with different UTC offsets sort out of chronological order. Suggested fix: sort start and end by start_epoch and end_epoch, with a test across differing offsets.
