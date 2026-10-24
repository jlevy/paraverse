---
type: is
id: is-01m5qvkwrwt2hsmxfbpsn0jcbs
title: "PR #8 qodo-5639990820 #3: null contracts pass routine loads (https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820)"
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
created_at: 2026-10-24T21:03:39.804Z
updated_at: 2026-10-24T21:29:48.035Z
started_at: 2026-10-24T21:23:17.238Z
closed_at: 2026-10-24T21:29:48.034Z
close_reason: "Fixed in 5d1b0d047eb843b98f4460dfee28fe999321d921: only a nonblank string names a contract. test_an_ordinary_load_needs_a_contract_name covers null, blank and non-string values; make lint-check and all 95 tests pass."
resolution: null
duplicate_of: null
---
Severity: Medium (Qodo). PR #8. Review: https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820. Inline comment: https://github.com/jlevy/paraverse/pull/8#discussion_r4368490033. Location: db/src/paraverse_graph/kb.py:120-127 (read_artifact) and kb.py:191-199 (_check_envelopes). read_artifact stores str(block.get('contract', '')), so an explicit 'contract: null' becomes the truthy string 'None' and passes the new contract check on loads without --validate. Suggested fix: accept only a nonempty string contract; reject null and whitespace-only values; add an ordinary-load test with contract: null.
