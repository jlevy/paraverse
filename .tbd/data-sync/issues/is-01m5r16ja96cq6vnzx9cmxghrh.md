---
type: is
id: is-01m5r16ja96cq6vnzx9cmxghrh
title: "PR #11 A3: preserve website URL identity components"
kind: bug
status: in_progress
priority: 3
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:41:14.568Z
updated_at: 2026-10-24T22:41:28.855Z
started_at: 2026-10-24T22:41:28.855Z
---
Strong review A3 (Low), curation/src/paraverse_curation/people.py https_url lowercases paths and drops ports/query, falsely matching distinct website accounts. Normalize scheme/host while preserving meaningful URL components; retain platform account normalization. Formal review URL pending coordinator publication.
