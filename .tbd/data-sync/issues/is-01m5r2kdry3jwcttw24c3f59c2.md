---
type: is
id: is-01m5r2kdry3jwcttw24c3f59c2
title: "PR #13 A3: carry late-arrival constraint into external recommendation selection"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:05:44.477Z
updated_at: 2026-10-25T01:09:24.978Z
started_at: 2026-10-25T00:21:09.214Z
closed_at: 2026-10-25T01:09:24.978Z
close_reason: "Fixed in5a1a3e9 on published PR13 head0333a174: logout clears draft, restorable workspace and cached plan people; late-arrival state reaches external refresh and backend selection. Meaningful RED/GREEN profile/plan and morning-versus-afternoon regressions.49 PR13 backend and40 release Swift tests pass; combined top69backend60Swift pass."
resolution: null
duplicate_of: null
---
PR #13 senior review A3 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. Medium. backend/session_service.py:84-86 replaces initially constrained output with select_external(ranked, rows, busy), whose schedule calls default late=False. Reviewer mocked external=True, late=True, after 3 pm and obtained 09:00 event. Pass effective late through every external candidate while preserving day diversity. Deferred under user merge-first authorization; waits on current native stack landing before scheduling constraint follow-up.
