---
type: is
id: is-01m5r9fjxm1zdg5ppdazgczm6n
title: "PTC PR1: confine artifact paths to the output root"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:58.707Z
updated_at: 2026-10-25T01:44:08.187Z
started_at: 2026-10-25T01:06:11.034Z
closed_at: 2026-10-25T01:44:08.187Z
close_reason: "Fixed in PTC PR1 feature180815d15134ac2ebb41f95812eba3e5719143db and verified merged as64e3c0e7c5923baf74c88e408e642837da1bc54f. Final D/E clean;29tests and both CI pass;132artifacts valid. Public PR: https://github.com/jlevy/ptc2026-md/pull/1"
resolution: null
duplicate_of: null
---
Security C3 repro: Website id with traversal components accepted via raw bio_links can lead artifact writer outside KB root. Enforce path confinement before any write, including symlinks and absolute/parent paths. Add confined synthetic regression.
