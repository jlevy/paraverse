---
type: is
id: is-01m5r2sfgvhy19s7xfw6h8br6s
title: "PR #14 Qodo r4368869170: Builds can silently use unpinned data"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:02.873Z
updated_at: 2026-10-24T23:09:02.873Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869170. Location: native/build-app.sh:9. 3\. Builds can silently use unpinned data 🐞 Bug ≡ Correctness


build-app.sh runs the exporter against the currently checked-out vendor submodules without
checking their commits against the parent repository&#x27;s gitlinks. If a developer checks out another
clean, valid KB commit in either submodule, the build succeeds and bundles that commit&#x27;s data rather
than the snapshot selected by the parent checkout.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
