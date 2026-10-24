---
type: is
id: is-01m5r2sfwamsppqnzp7p8thhvv
title: "PR #14 Qodo r4368869178: The browser can show the wrong dataset"
kind: bug
status: in_progress
priority: 2
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:09:03.241Z
updated_at: 2026-10-24T23:17:39.761Z
started_at: 2026-10-24T23:17:39.760Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869178. Location: native/Sources/CommonGround/KnowledgeBaseBrowser.swift:96. 4\. The browser can show the wrong dataset 🐞 Bug ≡ Correctness


probeServer() accepts any local browser whose /api/meta response has nonempty graph, dataset and
digest fields, and connect() immediately reuses it. If port 8766 already serves a valid
single-dataset or differently selected Paraverse browser, opening the app&#x27;s Knowledge Base window
displays that selection instead of starting or confirming the intended combined view.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
