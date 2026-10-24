---
type: is
id: is-01m5qvkwec2caqzf3k1ddkdha6
title: "PR #8 qodo-5639990820 #2: validation hides failed file paths beyond the first five (https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820)"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvkvm4t4kd9pjkwvhdbbs8
hold: null
hold_until: null
created_at: 2026-10-24T21:03:39.467Z
updated_at: 2026-10-24T21:29:47.790Z
started_at: 2026-10-24T21:23:17.232Z
closed_at: 2026-10-24T21:29:47.790Z
close_reason: "Fixed in ded75fc9a47e0405b2919520550699df889634f6: every failed artifact path is printed on its own plain-text line; test_load_validate_lists_every_failed_artifact covers seven failures. make lint-check and all 95 tests pass."
resolution: null
duplicate_of: null
---
Severity: Medium (Qodo). PR #8. Review: https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820. Inline comment: https://github.com/jlevy/paraverse/pull/8#discussion_r4368490032. Location: db/src/paraverse_graph/cli.py:186-192 (_validate_kb). The error message includes only report.problems[:5]; with six or more failing artifacts the output gives the total but not the remaining paths. Suggested fix: output every failed path, one per line, keeping per-artifact error text bounded; test a report with more than five failures.
