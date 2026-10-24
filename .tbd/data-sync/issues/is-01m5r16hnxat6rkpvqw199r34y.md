---
type: is
id: is-01m5r16hnxat6rkpvqw199r34y
title: "PR #11 A1: reject contextual spaced email addresses"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:41:13.916Z
updated_at: 2026-10-24T23:20:49.861Z
started_at: 2026-10-24T22:41:28.822Z
closed_at: 2026-10-24T23:20:49.861Z
close_reason: Implemented, reviewed and merged in Paraverse PR11 at main35218bb. Final head628ec8e passed44tests plus lint/format/type and header-only list checks. Independent securityB5640549894 and follow-upC5640555080 clear the fixes; full Qodo/reviewA disposition6390779837. User explicitly approved local checks in lieu of absent CI. Populated intake remains futureu26-p69k; nonpressing relative-path edge remains openpv-wmef.
resolution: null
duplicate_of: null
---
Strong review A1 (Medium), curation/src/paraverse_curation/people.py has_email: Email: example @ example.org and Email: example @ example pass contact screening. Detect contextual obfuscation without rejecting professional role affiliations. Formal review URL pending coordinator publication.

## Notes

Local fix 26adb35d1d405a157de830d2f954b24b2a552d2e adds contextual email-label detection with spaced/dotless address regressions, preserving Engineer at/@ Example.com affiliations. Full42tests/lint/types/listcheck PASS; RED35fail/7pass. Coordinator owns cherry-pick/push and strong review disposition; leave open pending publication.
