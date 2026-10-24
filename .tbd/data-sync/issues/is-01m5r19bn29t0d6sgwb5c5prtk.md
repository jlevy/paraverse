---
type: is
id: is-01m5r19bn29t0d6sgwb5c5prtk
title: "PR #11 Qodo r4368786522: detect encoded URL email contacts"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:42:46.049Z
updated_at: 2026-10-24T22:42:52.739Z
started_at: 2026-10-24T22:42:52.739Z
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368786522 at people.py check_row: percent-encoded URL email addresses evade raw checks. Check safely decoded URL components without echoing values.
