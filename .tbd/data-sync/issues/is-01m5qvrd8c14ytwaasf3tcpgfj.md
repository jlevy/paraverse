---
type: is
id: is-01m5qvrd8c14ytwaasf3tcpgfj
title: "PR #6 qodo-5639989300 #8: two dataset names can map to one graph and overwrite each other (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: in_progress
priority: 3
version: 2
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:07.755Z
updated_at: 2026-10-24T21:23:17.219Z
started_at: 2026-10-24T21:23:17.219Z
---
Severity: Low (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488667. Location: db/src/paraverse_graph/datasets.py:22-23, 99-105; cli.py:156-161; loader.py:101-180. graph_name lowercases a dataset name and replaces characters outside [a-z0-9_], so names such as foo-bar and foo_bar, or Foo and foo, share a default graph, and loading one replaces the other's live graph without warning. Suggested fix: refuse to replace a live graph whose GraphMeta.dataset differs unless --graph was given, and warn in list_datasets when two datasets map to one graph.
