---
type: is
id: is-01m5r19c7qzcagtnqgzf98374e
title: "PR #11 Qodo r4368786531: detect slash-separated phone contacts"
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
created_at: 2026-10-24T22:42:46.646Z
updated_at: 2026-10-24T22:42:52.750Z
started_at: 2026-10-24T22:42:52.750Z
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368786531 at people.py _PHONE_RES: slash grouping such as synthetic 020/7946/0000 evades checks. Extend grouped form detection and add regression.
