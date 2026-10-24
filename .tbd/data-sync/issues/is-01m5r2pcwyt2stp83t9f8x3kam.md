---
type: is
id: is-01m5r2pcwyt2stp83t9f8x3kam
title: "PR #10 Qodo r4368858700: stop retrying deterministic content LoadError failures"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:07:21.885Z
updated_at: 2026-10-24T23:07:21.885Z
---
Low reliability. Original finding: https://github.com/jlevy/paraverse/pull/10#discussion_r4368858700; Qodo UUID 870743bd-4ff8-4000-8874-72b72c5cc74c. selection.py:113-120 treats all LoadError causes as transient; loader.py:184-189 also uses LoadError for deterministic stats/duplicate-ID content failures, so these retry forever with backoff. Distinguish deterministic mismatch errors from IO/database failures; wait for a changed source signature for deterministic failures while preserving transient retry recovery. Deferred under user merge-first authorization; waits on current stack landing before failure classification follow-up.
