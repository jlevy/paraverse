---
type: is
id: is-01m5qz9jfh1nfsy2x6fbsv00z1
title: "PR #8 Qodo 5640168732 #1: validate graph-referenced artifacts of every extension"
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvkvm4t4kd9pjkwvhdbbs8
hold: null
hold_until: null
created_at: 2026-10-24T22:07:55.888Z
updated_at: 2026-10-24T22:08:34.507Z
started_at: 2026-10-24T22:08:34.506Z
---
High finding https://github.com/jlevy/paraverse/pull/8#discussion_r4368644160. artifact_paths currently ignores .yml and arbitrary graph-referenced paths although loader accepts them; discover all referenced artifacts and unreferenced .yml, choose Markdown/YAML reader by content, add invalid.yml beside valid.md regression.
