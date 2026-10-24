---
type: is
id: is-01m5r16ja96cq6vnzx9cmxghrh
title: "PR #11 A3: preserve website URL identity components"
kind: bug
status: closed
priority: 3
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:41:14.568Z
updated_at: 2026-10-24T23:20:49.841Z
started_at: 2026-10-24T22:41:28.855Z
closed_at: 2026-10-24T23:20:49.841Z
close_reason: Implemented, reviewed and merged in Paraverse PR11 at main35218bb. Final head628ec8e passed44tests plus lint/format/type and header-only list checks. Independent securityB5640549894 and follow-upC5640555080 clear the fixes; full Qodo/reviewA disposition6390779837. User explicitly approved local checks in lieu of absent CI. Populated intake remains futureu26-p69k; nonpressing relative-path edge remains openpv-wmef.
resolution: null
duplicate_of: null
---
Strong review A3 (Low), curation/src/paraverse_curation/people.py https_url lowercases paths and drops ports/query, falsely matching distinct website accounts. Normalize scheme/host while preserving meaningful URL components; retain platform account normalization. Formal review URL pending coordinator publication.

## Notes

Local fix 26adb35d1d405a157de830d2f954b24b2a552d2e preserves website/target URL path case, ports, queries, fragments and trailing slash while normalizing scheme/host. Also addresses Qodo https://github.com/jlevy/paraverse/pull/11#discussion_r4368786525. Full42tests/lint/types/listcheck PASS; RED35fail/7pass. Coordinator owns cherry-pick/push/disposition; leave open pending publication.
