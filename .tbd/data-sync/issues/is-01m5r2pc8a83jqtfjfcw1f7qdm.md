---
type: is
id: is-01m5r2pc8a83jqtfjfcw1f7qdm
title: "PR #10 B2: update architecture for local source reads and shared selection POST"
kind: bug
status: open
priority: 3
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:07:21.225Z
updated_at: 2026-10-24T23:17:31.258Z
started_at: 2026-10-24T23:16:55.968Z
---
Low. Original review B2: https://github.com/jlevy/paraverse/pull/10#pullrequestreview-5640502579. docs/project/architecture/arch-2026-10-24-kb-browser.md:76,98 says no local KB reads and all endpoints read-only GET, but selection reads local sources and rebuilds a shared separate browser graph through POST. Align data path, API table and shared selection contract with README. Deferred under user merge-first authorization; waits on current stack landing before architecture documentation reconciliation.

## Notes

Deferred: wait for a focused architecture-document reconciliation followup after the bounded review fixes land. Update local source reads, shared selection graph contract and POST endpoint documentation to match implementation and README. Referenced by pv-5jjg; original parent and review evidence retained.
