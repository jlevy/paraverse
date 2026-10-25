---
type: is
id: is-01m5r9fkg971fjtmbhs20ret9q
title: "PTC PR1: retain account identity confidence and evidence"
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
created_at: 2026-10-25T01:05:59.304Z
updated_at: 2026-10-25T01:06:11.051Z
started_at: 2026-10-25T01:06:11.051Z
---
Correctness review found a medium-confidence GitHub profile link from curation loses identity_confidence and identity_evidence in emitted account artifacts. Preserve recorded uncertainty and its source; do not promote an unresolved identity through export.
