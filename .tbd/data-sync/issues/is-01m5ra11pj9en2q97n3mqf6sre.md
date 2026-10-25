---
type: is
id: is-01m5ra11pj9en2q97n3mqf6sre
title: "PR13 Qodo r4369199211: minimize bundled public attendee export"
kind: bug
status: in_progress
priority: 1
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:15:30.886Z
updated_at: 2026-10-25T01:21:30.987Z
started_at: 2026-10-25T01:15:50.230Z
---
High review5640894815 https://github.com/jlevy/paraverse/pull/13#discussion_r4369199211. Remove unsupported generated titles and enrichment/scraper bookkeeping from all legacy attendee records; bundle only reviewed attendance/UI fields. Verify all rows and native Codable compatibility. Work isolated from0333a174; no primary refs or pushes.

## Notes

Final correction040c90ed9ac6d710d82e76644485d0e773d563b1 atop3758; apply both or use finaltree. All12original stableIDs restored from0333 EXACT, all11retainedfields/132occurrences EXACT inclattendance_status,sourcequotes,dates,avatars.112unsupportedoccurrences removed from244. Exporter requires nonemptystringid. ID regression RED4failures→52backendPASS0.069s; focusednativeID+decoder1PASS0.003s.0contacts0sensitivequotemarkers; realCLIroundtrip. Previous120fieldcount superseded. Evidence scratchpad/review/public-attendees-evidence.json. Await clean-history reconstruction; no primarywrites/push. Venuecachephone was livepage-only falsealarm; committedcache unchanged.
