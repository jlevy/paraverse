---
type: is
id: is-01m5r2fmy9nzty2wyf76hjscy8
title: Align Overview date parsing with graph timestamp promotion
kind: bug
status: closed
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T23:03:40.743Z
updated_at: 2026-10-24T23:26:10.736Z
started_at: 2026-10-24T23:03:56.364Z
closed_at: 2026-10-24T23:26:10.723Z
close_reason: Fixed in99cea256; genuine regression RED then focused20pass and full make check196passed/no skips/exit0; independent strong senior A and correctness B passed at exact head; Qodo disposition published6390849852. PR12 merged d8eaf6555648460e8a9210cb8291fe449f5f1344.
resolution: null
duplicate_of: null
---
PR12 Qodo finding r4368848492/comment6390627388: Overview _instant rejects date-only and naive ISO dates while mapping._epoch accepts them as UTC, causing availability statistics and event dates to disagree. Align supported date parsing and add focused regressions; no change to provenance exposure or load identity.
