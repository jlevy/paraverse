---
type: is
id: is-01m5r1x1a68edmdv6qkrzdxy95
title: "PR #11 Qodo r4368798006: reject unconfigured dataset build commands"
kind: bug
status: in_progress
priority: 3
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:53:30.821Z
updated_at: 2026-10-24T22:54:05.872Z
started_at: 2026-10-24T22:54:05.872Z
---
Low https://github.com/jlevy/paraverse/pull/11#discussion_r4368798006 cli.py always invokes universe-kb for any dataset. Configure supported dataset commands and reject unsupported datasets before subprocess execution.
