---
type: is
id: is-01m5qz8mm5ckh86j34m7tsbky9
title: "PR #6 review 5640168733 finding 2: retain edited filter on live remount"
kind: bug
status: closed
priority: 2
version: 4
delegate: codex-resume
labels: []
dependencies: []
parent_id: is-01m5qz85zgjqrx5gww1hvfgd1d
hold: null
hold_until: null
created_at: 2026-10-24T22:07:25.317Z
updated_at: 2026-10-24T22:50:38.606Z
started_at: 2026-10-24T22:07:39.077Z
closed_at: 2026-10-24T22:50:38.606Z
close_reason: "Fixed and landed in Paraverse PRs #6–#8, merged 2026-10-24 at main beabb16f0332ce6afcdb047b12cdb04b4dc59025. Combined owning-layer suite: 143 passed, clean exit; lint/format/type checks passed. Final independent reviews PV6F (5640363560) and PV8E (5640363811) report no findings. Qodo dispositions: PR6 comments 6390252206, 6390447043; PR8 comments 6390252630, 6390447546. User explicitly approved merging with local checks because neither repo has CI configured."
resolution: null
duplicate_of: null
---

## Notes

Qodo review 5640168733 finding 2 and independent follow-up lifecycle findings: retain draft values, cancel removed-view debounce handlers, never reuse disposed views during concurrent navigation, and preserve pagination when the draft is unchanged. Fixed in 01c77b9; actual Node table/search lifecycle regression is RED before fixes and GREEN after, including navigation during awaited remount and unchanged offset=50. Full owning-layer suite 94 passed; lint and type checks clean.
