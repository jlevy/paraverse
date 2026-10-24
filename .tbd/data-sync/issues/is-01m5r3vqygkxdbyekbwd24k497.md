---
type: is
id: is-01m5r3vqygkxdbyekbwd24k497
title: "PR #13 E3: recover malformed chat cache and publish atomically"
kind: bug
status: in_progress
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.615Z
updated_at: 2026-10-24T23:39:29.882Z
started_at: 2026-10-24T23:28:00.833Z
---
Review5640567860 E3. Derived chat responses use truncating writes and trust malformed existing JSON, making identical retries permanently fail. Use unique atomic publication and treat malformed JSON/shape as a cache miss; interrupted-write/concurrent-reader regressions.

## Notes

Fixeddb13046 +6ac5a6b on isolated13 base; unique temp/flush/fsync/replace publication and malformed JSON/shape cache miss. Recovery regression includes interrupted prefix, [], and incomplete recommendation identity; concurrent60writers/readers see only complete documents. Final8chatPASS0.058s, full46backend atdb130460.056s; parent integrates and closes, no push.
