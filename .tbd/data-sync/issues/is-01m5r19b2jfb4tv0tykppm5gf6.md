---
type: is
id: is-01m5r19b2jfb4tv0tykppm5gf6
title: "PR #11 Qodo r4368786517: prevent header diagnostic data leakage"
kind: bug
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:42:45.447Z
updated_at: 2026-10-24T22:46:23.150Z
started_at: 2026-10-24T22:42:52.713Z
---
High https://github.com/jlevy/paraverse/pull/11#discussion_r4368786517 at curation/src/paraverse_curation/people.py _header_message: unexpected header values leak into CLI diagnostics. Replace unexpected cell contents with positions/counts and prove CLI does not echo synthetic sensitive input.

## Notes

Local fix 26adb35d1d405a157de830d2f954b24b2a552d2e reports unexpected header positions, never header contents. CLI regression proves synthetic email/phone/private text absent from stdout/stderr. Full42tests/lint/types/listcheck PASS; RED35fail/7pass. Coordinator owns cherry-pick/push/disposition; leave open pending publication.
