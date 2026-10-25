---
type: is
id: is-01m5ra11pj9en2q97n3mqf6sre
title: "PR13 Qodo r4369199211: minimize bundled public attendee export"
kind: bug
status: closed
priority: 1
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:15:30.886Z
updated_at: 2026-10-25T01:28:38.850Z
started_at: 2026-10-25T01:15:50.230Z
closed_at: 2026-10-25T01:28:38.840Z
close_reason: Fixed in clean published PR13 8cf5b0454470d46c3f5dc2f331046103244cee98, soleparent mainf041; finalsource matches3758+040c90e pluscanonicalvenuefix.12rows retain11supportedfields inclall12exactoriginalIDs/status/avatars;112unsupportedfieldoccurrences removed.0contacts/sensitivequotemarkers;52backend+focusednativeIDdecoder pass. Combinedfinal13backend61pass andTOP15backend81pass; fullreleaseSwift gatepending atclosure. Old0333 and6originalappimports excluded; oldhistory privateexternalbundle. Evidence scratchpad/review/public-attendees-evidence.json and forthcomingprimary-safe13-evidence.json.
resolution: null
duplicate_of: null
---
High review5640894815 https://github.com/jlevy/paraverse/pull/13#discussion_r4369199211. Remove unsupported generated titles and enrichment/scraper bookkeeping from all legacy attendee records; bundle only reviewed attendance/UI fields. Verify all rows and native Codable compatibility. Work isolated from0333a174; no primary refs or pushes.

## Notes

Final correction040c90ed9ac6d710d82e76644485d0e773d563b1 atop3758; apply both or use finaltree. All12original stableIDs restored from0333 EXACT, all11retainedfields/132occurrences EXACT inclattendance_status,sourcequotes,dates,avatars.112unsupportedoccurrences removed from244. Exporter requires nonemptystringid. ID regression RED4failures→52backendPASS0.069s; focusednativeID+decoder1PASS0.003s.0contacts0sensitivequotemarkers; realCLIroundtrip. Previous120fieldcount superseded. Evidence scratchpad/review/public-attendees-evidence.json. Await clean-history reconstruction; no primarywrites/push. Venuecachephone was livepage-only falsealarm; committedcache unchanged.
