---
type: is
id: is-01m5r3jrj71xrwk6bbpbm14h86
title: "PR #16 Qodo 4368912107: normalize non-string exported event names before menu labels"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r0kn8j674bah26ks0c8tws
hold: null
hold_until: null
created_at: 2026-10-24T23:22:51.333Z
updated_at: 2026-10-24T23:33:29.464Z
started_at: 2026-10-24T23:22:56.429Z
closed_at: 2026-10-24T23:33:29.464Z
close_reason: "Fixed in PR16, final head 138da52f17a795d1d7e02288b250b35c163651d5, merged at 83784693e74e18a725156584a578590134cf41dd. Final integration gate: 208 passed, zero skips, explicit exit0; validation https://github.com/jlevy/paraverse/pull/16#issuecomment-6390899962. Independent senior/correctness/security/performance reviews A-D have zero new findings; current-head Qodo has no findings."
resolution: null
duplicate_of: null
---
Medium. PR #16 Qodo review https://github.com/jlevy/paraverse/pull/16#pullrequestreview-5640566774 at aaba9c3e6d93edcca20310f4e4e0a24df2a26788. Finding https://github.com/jlevy/paraverse/pull/16#discussion_r4368912107. db/src/paraverse_graph/selection.py: raw exported event names may be non-string values and raise TypeError during label normalization. Normalize supported names or use safe fallback before deriving committed menu labels; root is implementing the bounded fix and regression. Pending new head and verification; do not close before publication and review.
