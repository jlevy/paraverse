---
type: is
id: is-01m5r9fk75k2fck16gbef7mmeh
title: "PTC PR1: preserve repository fork truth and unavailable metadata"
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
created_at: 2026-10-25T01:05:59.012Z
updated_at: 2026-10-25T01:44:08.153Z
started_at: 2026-10-25T01:06:11.042Z
closed_at: 2026-10-25T01:44:08.152Z
close_reason: "Fixed in PTC PR1 feature180815d15134ac2ebb41f95812eba3e5719143db and verified merged as64e3c0e7c5923baf74c88e408e642837da1bc54f. Final D/E clean;29tests and both CI pass;132artifacts valid. Public PR: https://github.com/jlevy/ptc2026-md/pull/1"
resolution: null
duplicate_of: null
---
Correctness review found absent sparse repository fields default to stars=0,forks=0,fork=false and create an unsupported maintains edge for an actual fork. Preserve unavailable fields as unknown/omitted and only claim original-repository maintenance when evidence explicitly supports non-fork ownership.
