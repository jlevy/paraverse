---
type: is
id: is-01m5r2sfgvhy19s7xfw6h8br6s
title: "PR #14 Qodo r4368869170: Builds can silently use unpinned data"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:09:02.873Z
updated_at: 2026-10-25T04:46:17.252Z
started_at: 2026-10-24T23:15:30.686Z
closed_at: 2026-10-25T04:46:17.252Z
close_reason: Completed in merged Paraverse PR14, merge 01cae9f21e5f3d0f5c95b52027bfa223959ab457. Final safe merged dataset pins a823679/64e3c0e match manifest; 4977+132 artifacts valid, deterministic native assets, owned explicit attendance proof and expected browser identity gates verified. Independent F/G/H carry exact source; final upper-stack 96 backend/64 release Swift tests pass. Both safe datasets run in browser8879 (5536 entities/25564 relationships); all nonpressing findings remain separate open beads.
resolution: null
duplicate_of: null
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869170. Location: native/build-app.sh:9. 3\. Builds can silently use unpinned data 🐞 Bug ≡ Correctness


build-app.sh runs the exporter against the currently checked-out vendor submodules without
checking their commits against the parent repository&#x27;s gitlinks. If a developer checks out another
clean, valid KB commit in either submodule, the build succeeds and bundles that commit&#x27;s data rather
than the snapshot selected by the parent checkout.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.

## Notes

Fixed1382a6b: verify checkout HEAD equals parent HEAD gitlink and KB clean BEFORE read/export, recheck at publication. Clean unpinned and dirty KB regressions reject before load and preserve destination. Full62backendPASS. Parent integrates; no push.
