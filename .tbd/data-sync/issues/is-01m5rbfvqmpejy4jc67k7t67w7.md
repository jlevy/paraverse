---
type: is
id: is-01m5rbfvqmpejy4jc67k7t67w7
title: "PR15 Qodo r4369243679: Retry failed invitation-recipient lookups"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T01:41:04.882Z
updated_at: 2026-10-25T01:41:04.882Z
---
Review: https://github.com/jlevy/paraverse/pull/15#discussion_r4369243679 (Qodo5640945499). Independently confirmed at918bf3f/base49bee: Luma.swift111 guards selectionLoaded, then catch122 sets it true after a failed recipient lookup; later attempts cannot retry and run(status) clears the notice. Card state persists while scrolling. Distinct from pv-qtym backend creating/needs_review commit-state recovery. Follow up with explicit failed state, retained error and a retry action that does not create or invite anything. Accepted nonpressing Low/P3 deferral for a later PR; keep OPEN during this merge.
