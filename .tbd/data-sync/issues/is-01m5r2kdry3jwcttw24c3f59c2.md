---
type: is
id: is-01m5r2kdry3jwcttw24c3f59c2
title: "PR #13 A3: carry late-arrival constraint into external recommendation selection"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:05:44.477Z
updated_at: 2026-10-24T23:05:44.477Z
---
PR #13 senior review A3 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. Medium. backend/session_service.py:84-86 replaces initially constrained output with select_external(ranked, rows, busy), whose schedule calls default late=False. Reviewer mocked external=True, late=True, after 3 pm and obtained 09:00 event. Pass effective late through every external candidate while preserving day diversity. Deferred under user merge-first authorization; waits on current native stack landing before scheduling constraint follow-up.
