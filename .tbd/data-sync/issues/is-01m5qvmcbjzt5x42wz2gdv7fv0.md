---
type: is
id: is-01m5qvmcbjzt5x42wz2gdv7fv0
title: "PR #4 Qodo 2 (https://github.com/jlevy/paraverse/pull/4#pullrequestreview-5639977244): compliance rules miss personal accounts"
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
created_at: 2026-10-24T21:03:55.761Z
updated_at: 2026-10-24T21:05:40.042Z
started_at: 2026-10-24T21:04:41.392Z
closed_at: 2026-10-24T21:05:40.041Z
close_reason: "fixed in 'chore: flag personal accounts in the Qodo compliance rules': rule 6 flags accounts or pages unrelated to professional work and names the allowed work accounts; confirmed by scratch check_pr_agent.py finding 2 (fails at 92db3e1, passes after)"
resolution: null
duplicate_of: null
---
Severity: High (Action required). PR #4, review https://github.com/jlevy/paraverse/pull/4#pullrequestreview-5639977244, inline comment https://github.com/jlevy/paraverse/pull/4#discussion_r4368483025.
File: .pr_agent.toml:20-25 ([review_agent] compliance_user_guidelines).
Finding: the compliance rules do not check that collected accounts and pages relate to the person's professional work, so personal-account data could pass review. docs/data-policy.md (What Must Not Be Included, Personal accounts) forbids it.
Suggested fix: add a rule that flags accounts or pages unrelated to the person's professional work.
