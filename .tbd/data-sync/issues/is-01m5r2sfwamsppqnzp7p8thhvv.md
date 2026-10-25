---
type: is
id: is-01m5r2sfwamsppqnzp7p8thhvv
title: "PR #14 Qodo r4368869178: The browser can show the wrong dataset"
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
created_at: 2026-10-24T23:09:03.241Z
updated_at: 2026-10-25T04:46:17.259Z
started_at: 2026-10-24T23:17:39.760Z
closed_at: 2026-10-25T04:46:17.259Z
close_reason: Completed in merged Paraverse PR14, merge 01cae9f21e5f3d0f5c95b52027bfa223959ab457. Final safe merged dataset pins a823679/64e3c0e match manifest; 4977+132 artifacts valid, deterministic native assets, owned explicit attendance proof and expected browser identity gates verified. Independent F/G/H carry exact source; final upper-stack 96 backend/64 release Swift tests pass. Both safe datasets run in browser8879 (5536 entities/25564 relationships); all nonpressing findings remain separate open beads.
resolution: null
duplicate_of: null
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869178. Location: native/Sources/CommonGround/KnowledgeBaseBrowser.swift:96. 4\. The browser can show the wrong dataset 🐞 Bug ≡ Correctness


probeServer() accepts any local browser whose /api/meta response has nonempty graph, dataset and
digest fields, and connect() immediately reuses it. If port 8766 already serves a valid
single-dataset or differently selected Paraverse browser, opening the app&#x27;s Knowledge Base window
displays that selection instead of starting or confirming the intended combined view.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.

## Notes

Fixed517292f: verify api/datasets selected set AND api/meta kb_digest against local compose_kbs identity via read-only runtime helper before reusing8766. Mismatch leaves other server untouched. Dataset set/digest negatives and existing-server no-launch tests pass in full49SwiftPASS12.744s. Parent integrates; no push.
