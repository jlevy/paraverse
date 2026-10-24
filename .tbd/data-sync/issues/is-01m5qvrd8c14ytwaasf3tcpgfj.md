---
type: is
id: is-01m5qvrd8c14ytwaasf3tcpgfj
title: "PR #6 qodo-5639989300 #8: two dataset names can map to one graph and overwrite each other (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 3
version: 3
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:07.755Z
updated_at: 2026-10-24T21:29:47.299Z
started_at: 2026-10-24T21:23:17.219Z
closed_at: 2026-10-24T21:29:47.299Z
close_reason: "Fixed in 7bc4f4c42ce928a67d74d26b27c6c3a369715b48 (fix(db): finish graph browser review corrections). New regression tests failed before the corresponding fixes; make lint now passes with 0 errors/warnings and make test passes all 89 tests. Retry/backoff, KB mutation guards, epoch sorting, capacity threshold, sponsor aggregation, missed-event cache refresh and dataset collisions are covered."
resolution: null
duplicate_of: null
---
Severity: Low (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488667. Location: db/src/paraverse_graph/datasets.py:22-23, 99-105; cli.py:156-161; loader.py:101-180. graph_name lowercases a dataset name and replaces characters outside [a-z0-9_], so names such as foo-bar and foo_bar, or Foo and foo, share a default graph, and loading one replaces the other's live graph without warning. Suggested fix: refuse to replace a live graph whose GraphMeta.dataset differs unless --graph was given, and warn in list_datasets when two datasets map to one graph.
