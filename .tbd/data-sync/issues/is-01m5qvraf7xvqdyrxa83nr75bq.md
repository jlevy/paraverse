---
type: is
id: is-01m5qvraf7xvqdyrxa83nr75bq
title: "PR #6 qodo-5639989300 #2: a reload can publish mixed-build data (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
created_at: 2026-10-24T21:06:04.902Z
updated_at: 2026-10-24T21:06:04.902Z
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488650. Location: db/src/paraverse_graph/kb.py:131-174, loader.py:149-181, schemas.py:37-53. load_kb reads the export files and artifacts, and load_graph later reads the schemas, in separate operations without checking they belong to one build, so a KB replaced during a load can mix builds and pass the count checks. Suggested fix: verify the build generation before committing the staging graph, covering artifacts and schemas, and retry if the source changed.
