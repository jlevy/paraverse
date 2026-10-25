---
type: is
id: is-01m5ra11pj9en2q97n3mqf6sre
title: "PR13 Qodo r4369199211: minimize bundled public attendee export"
kind: bug
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:15:30.886Z
updated_at: 2026-10-25T01:19:08.245Z
started_at: 2026-10-25T01:15:50.230Z
---
High review5640894815 https://github.com/jlevy/paraverse/pull/13#discussion_r4369199211. Remove unsupported generated titles and enrichment/scraper bookkeeping from all legacy attendee records; bundle only reviewed attendance/UI fields. Verify all rows and native Codable compatibility. Work isolated from0333a174; no primary refs or pushes.

## Notes

Source fix3758c73a57a0a5be06b206199452e3bfa68bc1aa ready on isolated codex/fix-public-attendee-export, parent0333a174; no push/primary mutation. All12rows reduced244→120field occurrences, preserving each retained value and attendance source/quote/date;0contact findings,0sensitive quote markers,0unsupportedkeys. Bundling invokes allowlist exporter. Python all-row RED1failure→GREEN3focused;52backendPASS0.065s; native release decoder1PASS0.002s; CLI roundtrip12row identity. Evidence scratchpad/review/public-attendees-evidence.json. Await coordinator clean-history reconstruction/integration before closure/publication. Venue cache phone report was corrected by venue owner as live-page-only; committed cache unchanged.
