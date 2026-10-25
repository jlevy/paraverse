---
type: is
id: is-01m5r9fjxm1zdg5ppdazgczm6n
title: "PTC PR1: confine artifact paths to the output root"
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:58.707Z
updated_at: 2026-10-25T01:06:11.034Z
started_at: 2026-10-25T01:06:11.034Z
---
Security C3 repro: Website id with traversal components accepted via raw bio_links can lead artifact writer outside KB root. Enforce path confinement before any write, including symlinks and absolute/parent paths. Add confined synthetic regression.
