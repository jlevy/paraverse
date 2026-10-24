---
type: is
id: is-01m5r3jrj71xrwk6bbpbm14h86
title: "PR #16 Qodo 4368912107: normalize non-string exported event names before menu labels"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r0kn8j674bah26ks0c8tws
hold: null
hold_until: null
created_at: 2026-10-24T23:22:51.333Z
updated_at: 2026-10-24T23:22:56.430Z
started_at: 2026-10-24T23:22:56.429Z
---
Medium. PR #16 Qodo review https://github.com/jlevy/paraverse/pull/16#pullrequestreview-5640566774 at aaba9c3e6d93edcca20310f4e4e0a24df2a26788. Finding https://github.com/jlevy/paraverse/pull/16#discussion_r4368912107. db/src/paraverse_graph/selection.py: raw exported event names may be non-string values and raise TypeError during label normalization. Normalize supported names or use safe fallback before deriving committed menu labels; root is implementing the bounded fix and regression. Pending new head and verification; do not close before publication and review.
