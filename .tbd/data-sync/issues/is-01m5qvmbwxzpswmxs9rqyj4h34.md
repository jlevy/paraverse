---
type: is
id: is-01m5qvmbwxzpswmxs9rqyj4h34
title: "PR #4 Qodo 1 (https://github.com/jlevy/paraverse/pull/4#pullrequestreview-5639977244): compliance rules miss unstated attendance"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvm0mfhgvfeh98jk49thpk
hold: null
hold_until: null
created_at: 2026-10-24T21:03:55.291Z
updated_at: 2026-10-24T21:05:39.701Z
started_at: 2026-10-24T21:04:40.196Z
closed_at: 2026-10-24T21:05:39.699Z
close_reason: "fixed in 'chore: flag unstated attendance in the Qodo compliance rules': rule 5 flags attendance the person did not state publicly (likes, follows, others' posts are not enough); confirmed by scratch check_pr_agent.py finding 1 (fails at 92db3e1, passes after)"
resolution: null
duplicate_of: null
---
Severity: High (Action required). PR #4, review https://github.com/jlevy/paraverse/pull/4#pullrequestreview-5639977244, inline comment https://github.com/jlevy/paraverse/pull/4#discussion_r4368483023.
File: .pr_agent.toml:20-25 ([review_agent] compliance_user_guidelines).
Finding: the compliance rules never check that an attendance claim is backed by the person's own public statement, so attendance inferred from a like, a follow or another person's post could pass review. docs/data-policy.md (What Must Not Be Included, Unstated attendance) forbids it.
Suggested fix: add a rule that flags attendance the person did not state publicly.
