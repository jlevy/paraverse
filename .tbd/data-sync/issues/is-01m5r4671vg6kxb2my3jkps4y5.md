---
type: is
id: is-01m5r4671vg6kxb2my3jkps4y5
title: "PR13 Qodo r4368919513: return400 for malformed planning JSON"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
created_at: 2026-10-24T23:33:28.762Z
updated_at: 2026-10-24T23:33:28.762Z
---
Review5640576707 r4368919513 Low: non-object body or malformed busy interval produces503 instead400. Deferred per user merge-soon instruction; validate body/interval shapes and negative request regressions.
