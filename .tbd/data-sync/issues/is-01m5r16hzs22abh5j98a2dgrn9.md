---
type: is
id: is-01m5r16hzs22abh5j98a2dgrn9
title: "PR #11 A2: reject reserved private host suffixes"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:41:14.232Z
updated_at: 2026-10-24T23:20:49.868Z
started_at: 2026-10-24T22:41:28.842Z
closed_at: 2026-10-24T23:20:49.868Z
close_reason: Implemented, reviewed and merged in Paraverse PR11 at main35218bb. Final head628ec8e passed44tests plus lint/format/type and header-only list checks. Independent securityB5640549894 and follow-upC5640555080 clear the fixes; full Qodo/reviewA disposition6390779837. User explicitly approved local checks in lieu of absent CI. Populated intake remains futureu26-p69k; nonpressing relative-path edge remains openpv-wmef.
resolution: null
duplicate_of: null
---
Strong review A2 (Medium), curation/src/paraverse_curation/people.py https_url: server.local and app.localhost pass despite public-host requirement. Apply consistent reserved/private hostname rejection across source, target and account forms. Formal review URL pending coordinator publication.

## Notes

Local fix 26adb35d1d405a157de830d2f954b24b2a552d2e rejects suffixes local/localhost/localdomain/internal/home.arpa/test/invalid consistently across source, attendance, target, website, Bluesky and Mastodon. Full42tests/lint/types/listcheck PASS; RED35fail/7pass. Coordinator owns cherry-pick/push and strong review disposition; leave open pending publication.
