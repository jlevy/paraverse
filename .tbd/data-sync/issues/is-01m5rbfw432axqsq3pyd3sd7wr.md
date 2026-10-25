---
type: is
id: is-01m5rbfw432axqsq3pyd3sd7wr
title: "PR15 Qodo r4369243674: Keep replies visible after unusually tall chat questions"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T01:41:05.282Z
updated_at: 2026-10-25T01:41:05.282Z
---
Review: https://github.com/jlevy/paraverse/pull/15#discussion_r4369243674 (Qodo5640945499). Bounded independent triage at918bf3f/base49bee partially confirms: WorldPlannerPanel153-160 intentionally anchors the newest user question at the top; long prior history alone does not hide the next reply. A question taller than the viewport can leave its reply below the fold, and busy-only updates no longer trigger scrolling. Recoverable viewport issue rated Low/P3, separate from pv-jxra eager-layout performance. Preserve intentional question anchoring while handling oversized questions and loading/reply visibility. Accepted nonpressing later-PR deferral; keep OPEN during this merge.
