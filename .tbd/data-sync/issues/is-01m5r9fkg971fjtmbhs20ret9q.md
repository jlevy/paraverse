---
type: is
id: is-01m5r9fkg971fjtmbhs20ret9q
title: "PTC PR1: retain account identity confidence and evidence"
kind: bug
status: closed
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:59.304Z
updated_at: 2026-10-25T01:44:08.165Z
started_at: 2026-10-25T01:06:11.051Z
closed_at: 2026-10-25T01:44:08.165Z
close_reason: "Fixed in PTC PR1 feature180815d15134ac2ebb41f95812eba3e5719143db and verified merged as64e3c0e7c5923baf74c88e408e642837da1bc54f. Final D/E clean;29tests and both CI pass;132artifacts valid. Public PR: https://github.com/jlevy/ptc2026-md/pull/1"
resolution: null
duplicate_of: null
---
Correctness review found a medium-confidence GitHub profile link from curation loses identity_confidence and identity_evidence in emitted account artifacts. Preserve recorded uncertainty and its source; do not promote an unresolved identity through export.
