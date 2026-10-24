---
type: is
id: is-01m5r2ea29g49x45edvmfkxnj9
title: "PR #12 Qodo r4368848492: align overview date parsing with loader UTC behavior"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex-resume
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:02:56.840Z
updated_at: 2026-10-24T23:34:09.347Z
started_at: 2026-10-24T23:34:01.566Z
closed_at: 2026-10-24T23:34:09.344Z
close_reason: Fixed and merged in Paraverse PR12. Finalhead99cea256 normalizes date-only/naive timestamps consistently with loader UTC handling; regression tests verify both plus malformed dates. Full196tests/no skips/exit0+lint/types, independent11focusedpass/exit0, strong seniorA5640576255 and correctnessB5640576309 report no findings. Merge d8eaf6555648460e8a9210cb8291fe449f5f1344; implementationbeadpv-7nqo closed by owner. Qodo superseding fixed disposition6390849852, reply4368923517.
resolution: null
duplicate_of: null
---
Overview _instant drops date-only or offset-free timestamps although loader mapping._epoch interprets them as UTC. Medium; preserve event calendar strings and align parsing, with event/session/retrieval regressions. Follow-up after overview lands unless fixed during integration. Original review: https://github.com/jlevy/paraverse/pull/12#discussion_r4368848492. User requested merge-first followups linked to PR review comments.
