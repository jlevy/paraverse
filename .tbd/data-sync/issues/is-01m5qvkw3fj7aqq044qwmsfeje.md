---
type: is
id: is-01m5qvkw3fj7aqq044qwmsfeje
title: "PR #8 qodo-5639990820 #1: broken YAML aborts validation with a traceback (https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820)"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvkvm4t4kd9pjkwvhdbbs8
hold: null
hold_until: null
created_at: 2026-10-24T21:03:39.118Z
updated_at: 2026-10-24T21:23:17.225Z
started_at: 2026-10-24T21:23:17.225Z
---
Severity: Medium (Qodo). PR #8. Review: https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820. Inline comment: https://github.com/jlevy/paraverse/pull/8#discussion_r4368490030. Location: db/src/paraverse_graph/validation.py:70-71 (validate_artifacts). validate_artifacts catches only OSError and ValueError; a YAML syntax error from the softschema readers escapes the per-artifact loop and the CLI's error handler, so load --validate stops with a traceback instead of listing the artifact as a failure. Suggested fix: catch the YAML parser exception per artifact, record it as an ArtifactProblem, add a malformed-YAML test.
