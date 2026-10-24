---
type: is
id: is-01m5qvraxgqventr6ngrw0tnes
title: "PR #6 qodo-5639989300 #3: session time sorting can be out of order (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
created_at: 2026-10-24T21:06:05.358Z
updated_at: 2026-10-24T21:06:05.358Z
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488653. Location: db/src/paraverse_graph/browser.py:884-902 (_sort_key), mapping.py:203-212. _sort_key orders the session start and end columns as offset-bearing timestamp strings rather than by their stored epoch values, so sessions with different UTC offsets sort out of chronological order. Suggested fix: sort start and end by start_epoch and end_epoch, with a test across differing offsets.
