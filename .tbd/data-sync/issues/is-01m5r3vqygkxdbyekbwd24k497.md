---
type: is
id: is-01m5r3vqygkxdbyekbwd24k497
title: "PR #13 E3: recover malformed chat cache and publish atomically"
kind: bug
status: closed
priority: 2
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.615Z
updated_at: 2026-10-25T01:09:24.716Z
started_at: 2026-10-24T23:28:00.833Z
closed_at: 2026-10-25T01:09:24.715Z
close_reason: "Fixed at PR13 head0333a174: action type guard precedes set membership; required and optional recommendation fields reject incompatible cache payloads and regenerate atomically. RED5 failures for numeric optional fields; GREEN8chat,49 PR13 backend tests; combined top69 backend and60 release Swift tests pass."
resolution: null
duplicate_of: null
---
Review5640567860 E3. Derived chat responses use truncating writes and trust malformed existing JSON, making identical retries permanently fail. Use unique atomic publication and treat malformed JSON/shape as a cache miss; interrupted-write/concurrent-reader regressions.

## Notes

Fixeddb13046 +6ac5a6b on isolated13 base; unique temp/flush/fsync/replace publication and malformed JSON/shape cache miss. Recovery regression includes interrupted prefix, [], and incomplete recommendation identity; concurrent60writers/readers see only complete documents. Final8chatPASS0.058s, full46backend atdb130460.056s; parent integrates and closes, no push.
