---
type: is
id: is-01m5qvmcs0qx8ctmfabkhkpbbs
title: "PR #4 Qodo 3 (https://github.com/jlevy/paraverse/pull/4#pullrequestreview-5639977244): compliance rules miss generated-text provenance"
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
created_at: 2026-10-24T21:03:56.191Z
updated_at: 2026-10-24T21:05:40.382Z
started_at: 2026-10-24T21:04:42.379Z
closed_at: 2026-10-24T21:05:40.381Z
close_reason: "fixed in 'chore: check generated text in the Qodo compliance rules': rule 7 checks citations, fidelity to cited sources, professional facts without speculation, and model plus input-hash recording; confirmed by scratch check_pr_agent.py finding 3 (fails at 92db3e1, passes after)"
resolution: null
duplicate_of: null
---
Severity: High (Action required). PR #4, review https://github.com/jlevy/paraverse/pull/4#pullrequestreview-5639977244, inline comment https://github.com/jlevy/paraverse/pull/4#discussion_r4368483027.
File: .pr_agent.toml:20-22, 25-31 ([review_agent] compliance_user_guidelines).
Finding: generated bios and summaries appear only as a trigger for the checklist rule. Nothing checks the docs/data-policy.md Generated Text requirements: stay within and cite sources, keep to professional facts without speculation, and record the model and a hash of the inputs.
Suggested fix: add a rule covering each Generated Text requirement.
