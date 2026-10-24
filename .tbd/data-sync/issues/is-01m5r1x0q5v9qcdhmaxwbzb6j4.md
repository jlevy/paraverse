---
type: is
id: is-01m5r1x0q5v9qcdhmaxwbzb6j4
title: "PR #11 Qodo r4368798002: pass dataset names safely through make"
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
created_at: 2026-10-24T22:53:30.212Z
updated_at: 2026-10-24T22:54:05.696Z
started_at: 2026-10-24T22:54:05.694Z
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368798002 curation/Makefile interpolates DATASET into single-quoted shell syntax. Export and read the shell environment instead; regression must prove quote payload cannot execute a command.
