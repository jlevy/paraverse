---
type: is
id: is-01m5r2e8v5ewhnaqec11dhc5k4
title: "PR #10 Qodo r4368843931: deduplicate merged nested day and term records"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:02:55.589Z
updated_at: 2026-10-24T23:02:55.589Z
---
Composition merges parent list values but may retain duplicate nested day/term records whose independent nodes were merged. Medium; validate parent payloads against source provenance and preserve ordered semantics. Follow-up after current stack lands; reviewer classified as deferrable. Original review: https://github.com/jlevy/paraverse/pull/10#discussion_r4368843931. User requested merge-first followups linked to PR review comments.
