---
type: is
id: is-01m5r2e9r8kdx8gd0p12bp8egq
title: "PR #10 Qodo r4368843940: clean up retired per-port browser graphs"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:02:56.519Z
updated_at: 2026-10-24T23:02:56.519Z
---
Combined browser graphs keyed by listening port can remain after process termination. Medium; define owned graph cleanup/reuse policy without dropping source graphs or graphs used by another process. Follow-up after current stack lands. Original review: https://github.com/jlevy/paraverse/pull/10#discussion_r4368843940. User requested merge-first followups linked to PR review comments.
