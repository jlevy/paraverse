---
type: is
id: is-01m5r1x0q5v9qcdhmaxwbzb6j4
title: "PR #11 Qodo r4368798002: pass dataset names safely through make"
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
created_at: 2026-10-24T22:53:30.212Z
updated_at: 2026-10-24T22:55:30.267Z
started_at: 2026-10-24T22:54:05.694Z
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368798002 curation/Makefile interpolates DATASET into single-quoted shell syntax. Export and read the shell environment instead; regression must prove quote payload cannot execute a command.

## Notes

Fixed locally in d4d4cec4095e9e714fd691704c13b52f597557f0, following 26adb35. DATASET is exported and read as one quoted shell environment argument; Makefile never interpolates its value into shell syntax. RED regression created a confined marker before fix; GREEN proves marker absent and exact argv retained. Full curation make lint-check test check PASS,44tests,0typeserrors. Root now owns native stack integration/publication and bead closure.
