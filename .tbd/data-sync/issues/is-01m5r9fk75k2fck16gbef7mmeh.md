---
type: is
id: is-01m5r9fk75k2fck16gbef7mmeh
title: "PTC PR1: preserve repository fork truth and unavailable metadata"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:59.012Z
updated_at: 2026-10-25T01:06:11.042Z
started_at: 2026-10-25T01:06:11.042Z
---
Correctness review found absent sparse repository fields default to stars=0,forks=0,fork=false and create an unsupported maintains edge for an actual fork. Preserve unavailable fields as unknown/omitted and only claim original-repository maintenance when evidence explicitly supports non-fork ownership.
