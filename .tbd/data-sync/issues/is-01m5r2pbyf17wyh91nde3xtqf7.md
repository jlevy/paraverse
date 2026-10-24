---
type: is
id: is-01m5r2pbyf17wyh91nde3xtqf7
title: "PR #10 B1: repair filters when reloaded scalar types change"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:07:20.909Z
updated_at: 2026-10-24T23:07:20.909Z
---
Medium. Original review B1: https://github.com/jlevy/paraverse/pull/10#pullrequestreview-5640502579 at 4c31b9a37a21838882ec527bc8737059d5c414d1. db/src/paraverse_graph/web/js/reconcile.js:73-78 retains a filter whose scalar field survives but changes type; score=unknown then fails HTTP 400 after string-to-integer schema change. Validate retained numeric/boolean values or clear filters when types change; reset offset and add schema-change regressions. Deferred under user merge-first authorization; waits on current stack landing before route-reconciliation follow-up.
