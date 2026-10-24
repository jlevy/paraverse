---
type: is
id: is-01m5r463z806xhyd5e0zt4sv8v
title: "PR13 D1: bound crowd route computation per frame"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
created_at: 2026-10-24T23:33:25.594Z
updated_at: 2026-10-24T23:33:25.594Z
---
Review5640551147 D1 Medium: rare synchronous route computation takes63–72ms CPU at twelve walkers. Deferred per user merge-soon instruction; add a bounded route work budget or off-main snapshot computation and representative tail benchmark.
