---
type: is
id: is-01m5qz8mm5ckh86j34m7tsbky9
title: "PR #6 review 5640168733 finding 2: retain edited filter on live remount"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: codex-resume
labels: []
dependencies: []
parent_id: is-01m5qz85zgjqrx5gww1hvfgd1d
hold: null
hold_until: null
created_at: 2026-10-24T22:07:25.317Z
updated_at: 2026-10-24T22:14:16.912Z
started_at: 2026-10-24T22:07:39.077Z
---

## Notes

Qodo review 5640168733 finding 2 and independent follow-up lifecycle findings: retain draft values, cancel removed-view debounce handlers, never reuse disposed views during concurrent navigation, and preserve pagination when the draft is unchanged. Fixed in 01c77b9; actual Node table/search lifecycle regression is RED before fixes and GREEN after, including navigation during awaited remount and unchanged offset=50. Full owning-layer suite 94 passed; lint and type checks clean.
