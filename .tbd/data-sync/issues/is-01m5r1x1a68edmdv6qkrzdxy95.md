---
type: is
id: is-01m5r1x1a68edmdv6qkrzdxy95
title: "PR #11 Qodo r4368798006: reject unconfigured dataset build commands"
kind: bug
status: in_progress
priority: 3
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:53:30.821Z
updated_at: 2026-10-24T22:55:31.128Z
started_at: 2026-10-24T22:54:05.872Z
---
Low https://github.com/jlevy/paraverse/pull/11#discussion_r4368798006 cli.py always invokes universe-kb for any dataset. Configure supported dataset commands and reject unsupported datasets before subprocess execution.

## Notes

Fixed locally in d4d4cec4095e9e714fd691704c13b52f597557f0, following 26adb35. Explicit supported command mapping contains universe2026-md; unconfigured dataset names fail clearly before any subprocess. RED showed unsupported ptc handoff succeeded; GREEN rejects it without running pipeline. Full curation make lint-check test check PASS,44tests,0typeserrors. Root now owns native stack integration/publication and bead closure.
