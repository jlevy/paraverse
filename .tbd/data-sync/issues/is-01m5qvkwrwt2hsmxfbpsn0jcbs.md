---
type: is
id: is-01m5qvkwrwt2hsmxfbpsn0jcbs
title: "PR #8 qodo-5639990820 #3: null contracts pass routine loads (https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820)"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvkvm4t4kd9pjkwvhdbbs8
created_at: 2026-10-24T21:03:39.804Z
updated_at: 2026-10-24T21:03:39.804Z
---
Severity: Medium (Qodo). PR #8. Review: https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820. Inline comment: https://github.com/jlevy/paraverse/pull/8#discussion_r4368490033. Location: db/src/paraverse_graph/kb.py:120-127 (read_artifact) and kb.py:191-199 (_check_envelopes). read_artifact stores str(block.get('contract', '')), so an explicit 'contract: null' becomes the truthy string 'None' and passes the new contract check on loads without --validate. Suggested fix: accept only a nonempty string contract; reject null and whitespace-only values; add an ordinary-load test with contract: null.
