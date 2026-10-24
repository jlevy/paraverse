---
type: is
id: is-01m5r2ea29g49x45edvmfkxnj9
title: "PR #12 Qodo r4368848492: align overview date parsing with loader UTC behavior"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:02:56.840Z
updated_at: 2026-10-24T23:02:56.840Z
---
Overview _instant drops date-only or offset-free timestamps although loader mapping._epoch interprets them as UTC. Medium; preserve event calendar strings and align parsing, with event/session/retrieval regressions. Follow-up after overview lands unless fixed during integration. Original review: https://github.com/jlevy/paraverse/pull/12#discussion_r4368848492. User requested merge-first followups linked to PR review comments.
