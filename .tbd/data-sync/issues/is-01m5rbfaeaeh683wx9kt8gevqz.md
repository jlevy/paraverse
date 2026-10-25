---
type: is
id: is-01m5rbfaeaeh683wx9kt8gevqz
title: "PR15 Qodo r4369243668: show personalized chat people reasons"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:40:47.176Z
updated_at: 2026-10-25T04:36:42.514Z
started_at: 2026-10-25T01:40:57.449Z
closed_at: 2026-10-25T04:36:42.514Z
close_reason: Published and verified PR13 5d2b1a78 (DNS pinning) and PR15 b33f9fb9 (person reasons). Final combined96backend and64releaseSwift tests pass; source and asset continuity verified. Evidence primary-qodo3 logs copied to internal S/review before external volume disconnected.
resolution: null
duplicate_of: null
---
High https://github.com/jlevy/paraverse/pull/15#discussion_r4369243668. WorldPlannerPanel suppresses every personalized person recommendation reason even though assistant text only introduces the cards. Restore showReason:true for person cards only; keep catalog session reason suppression. Coordinator authorized one-flag fix, combined release gate after current High bundle; no unrelated tests.
