---
type: is
id: is-01m5r2fmy9nzty2wyf76hjscy8
title: Align Overview date parsing with graph timestamp promotion
kind: bug
status: in_progress
priority: 2
version: 2
delegate: codex@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T23:03:40.743Z
updated_at: 2026-10-24T23:03:56.364Z
started_at: 2026-10-24T23:03:56.364Z
---
PR12 Qodo finding r4368848492/comment6390627388: Overview _instant rejects date-only and naive ISO dates while mapping._epoch accepts them as UTC, causing availability statistics and event dates to disagree. Align supported date parsing and add focused regressions; no change to provenance exposure or load identity.
