---
type: is
id: is-01m5r2h98qm4fmpck5dt4d76kj
title: "PR #10 Qodo follow-up: Preserve unconstrained source schema alternatives"
kind: bug
status: open
priority: 2
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r0kn8j674bah26ks0c8tws
hold: null
hold_until: null
created_at: 2026-10-24T23:04:34.326Z
updated_at: 2026-10-25T00:16:58.546Z
started_at: 2026-10-24T23:05:58.390Z
---
Medium. https://github.com/jlevy/paraverse/pull/10#discussion_r4368843935. Unsolicited Qodo review5640459673 at4d14. User authorized addressing all review items and merging PR10.

## Notes

Deferred implementation is now preserved in draft PR18 https://github.com/jlevy/paraverse/pull/18 at8519cb506e0f18970ea05ae870f96d5096c4a6ad. Restored only test_schema_union_accepts_sources_that_omit_constraints from backup38c19ad; older production fixes are merged via10/16. Ruff check/format pass. Focused regression1failed1passed17deselected; expected length failure with restrictive source first. Draft intentionally not merge-ready, no schema implementation claimed. Original Qodo5640459673 inline4368843935, duplicatepv-hc8f. Validation/display union design and passing regression remain required before closure.
