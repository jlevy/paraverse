---
type: is
id: is-01m5r16hzs22abh5j98a2dgrn9
title: "PR #11 A2: reject reserved private host suffixes"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:41:14.232Z
updated_at: 2026-10-24T22:41:28.842Z
started_at: 2026-10-24T22:41:28.842Z
---
Strong review A2 (Medium), curation/src/paraverse_curation/people.py https_url: server.local and app.localhost pass despite public-host requirement. Apply consistent reserved/private hostname rejection across source, target and account forms. Formal review URL pending coordinator publication.
