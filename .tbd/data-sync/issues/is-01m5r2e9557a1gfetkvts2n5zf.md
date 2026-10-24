---
type: is
id: is-01m5r2e9557a1gfetkvts2n5zf
title: "PR #10 Qodo r4368843935: reconcile constraints in combined schemas"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:02:55.908Z
updated_at: 2026-10-24T23:02:55.908Z
---
Merged fields retain some source-local constraints that can reject valid combined values. Medium; reconcile source constraints with combined record semantics and add schema regression coverage. Follow-up after current stack lands. Original review: https://github.com/jlevy/paraverse/pull/10#discussion_r4368843935. User requested merge-first followups linked to PR review comments.
