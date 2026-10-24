---
type: is
id: is-01m5qvmwanqtec607pwtmbk64b
title: "PR #3 qodo-5639984481 #1: data policy relies on a redaction test that does not exist (https://github.com/jlevy/paraverse/pull/3#pullrequestreview-5639984481)"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvmnvwcsnrwe45tndkdcnw
hold: null
hold_until: null
created_at: 2026-10-24T21:04:12.116Z
updated_at: 2026-10-24T21:05:46.215Z
started_at: 2026-10-24T21:04:19.764Z
closed_at: 2026-10-24T21:05:46.213Z
close_reason: "fixed in 'docs: say contact details are checked by hand, not by a redaction test' (5aab00f, pre-restack): docs/data-policy.md now says to remove contact details from free text and check by hand because nothing removes or detects them automatically yet; the checklist item reads 'No contact details appear, in structured fields or in free text.' Chose Qodo's reword option over adding a redaction step and test: this layer is docs-only and the repository has no build. The rule itself (no contact details) is unchanged. Confirmed: git grep -E 'redact|test fails if any remain|redaction test' over docs, README.md and AGENTS.md matched lines 50 and 104 before the fix and nothing after; flowmark adds no new formatting differences."
resolution: null
duplicate_of: null
---
Severity: Medium (Qodo: Remediation recommended). PR #3, review https://github.com/jlevy/paraverse/pull/3#pullrequestreview-5639984481, inline comment https://github.com/jlevy/paraverse/pull/3#discussion_r4368486296.

Files: docs/data-policy.md:48-51 (Contact details bullet: 'The build redacts them from free text, and a test fails if any remain.') and docs/data-policy.md:103-105 (checklist: 'No contact details appear, and the redaction test passes.').

Finding: the repository has no build or test that redacts contact details or fails when any remain, so the policy and checklist describe enforcement that does not exist.

Qodo's suggested fix (pick one): add the redaction build step and test, or reword the policy and checklist to say the check is manual until tooling exists.
