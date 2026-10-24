---
type: is
id: is-01m5r19bn29t0d6sgwb5c5prtk
title: "PR #11 Qodo r4368786522: detect encoded URL email contacts"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:42:46.049Z
updated_at: 2026-10-24T22:46:23.704Z
started_at: 2026-10-24T22:42:52.739Z
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368786522 at people.py check_row: percent-encoded URL email addresses evade raw checks. Check safely decoded URL components without echoing values.

## Notes

Local fix 26adb35d1d405a157de830d2f954b24b2a552d2e scans percent-decoded URLs for email contacts; diagnostics retain column/message only. Source/attendance/website path/query regressions pass. Full42tests/lint/types/listcheck PASS; RED35fail/7pass. Coordinator owns cherry-pick/push/disposition; leave open pending publication.
