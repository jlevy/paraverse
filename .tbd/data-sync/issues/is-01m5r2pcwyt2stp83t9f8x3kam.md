---
type: is
id: is-01m5r2pcwyt2stp83t9f8x3kam
title: "PR #10 Qodo r4368858700: stop retrying deterministic content LoadError failures"
kind: bug
status: closed
priority: 3
version: 5
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:07:21.885Z
updated_at: 2026-10-24T23:33:29.457Z
started_at: 2026-10-24T23:16:55.938Z
closed_at: 2026-10-24T23:33:29.457Z
close_reason: "Fixed in PR16, final head 138da52f17a795d1d7e02288b250b35c163651d5, merged at 83784693e74e18a725156584a578590134cf41dd. Final integration gate: 208 passed, zero skips, explicit exit0; validation https://github.com/jlevy/paraverse/pull/16#issuecomment-6390899962. Independent senior/correctness/security/performance reviews A-D have zero new findings; current-head Qodo has no findings."
resolution: null
duplicate_of: null
---
Low reliability. Original finding: https://github.com/jlevy/paraverse/pull/10#discussion_r4368858700; Qodo UUID 870743bd-4ff8-4000-8874-72b72c5cc74c. selection.py:113-120 treats all LoadError causes as transient; loader.py:184-189 also uses LoadError for deterministic stats/duplicate-ID content failures, so these retry forever with backoff. Distinguish deterministic mismatch errors from IO/database failures; wait for a changed source signature for deterministic failures while preserving transient retry recovery. Deferred under user merge-first authorization; waits on current stack landing before failure classification follow-up.

## Notes

Supersedes original deferral: implemented deterministic direct LoadError suppression while Redis/OSError cause chains retain transient retry. Coordination reference pv-5jjg; existing foreign parent and original description/history retained. Published as https://github.com/jlevy/paraverse/pull/16 at head aaba9c3e6d93edcca20310f4e4e0a24df2a26788. Coordinator reports lint passed, type checks 0 errors, and 148 tests passed with 56 inherited Universe-fixture skips. Pending independent review and central-owner merge; retain in_progress until merge verified. PR #10 complete disposition: https://github.com/jlevy/paraverse/pull/10#issuecomment-6390806471.
