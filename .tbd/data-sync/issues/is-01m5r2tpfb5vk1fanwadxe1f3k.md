---
type: is
id: is-01m5r2tpfb5vk1fanwadxe1f3k
title: "PR #10 D1: index account evidence once per source before composing people"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:42.750Z
updated_at: 2026-10-24T23:09:42.750Z
---
Low, https://github.com/jlevy/paraverse/pull/10#pullrequestreview-5640524616. composition._verified_accounts rescans nodes and edges twice per shared person, yielding O(P*(V+E)). Synthetic3000sharedpeople helper probe5.48s; current PTC overlap bounded at ten people, so safely deferred. Build per-source corroboration index in composition scalability follow-up after this stack lands.
