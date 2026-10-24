---
type: is
id: is-01m5qvrcx5mbd7tg1s131zwxg4
title: "PR #6 qodo-5639989300 #7: schema, rows and single-check endpoints can serve the old build (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: in_progress
priority: 3
version: 2
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:07.396Z
updated_at: 2026-10-24T21:23:17.211Z
started_at: 2026-10-24T21:23:17.211Z
---
Severity: Low (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488664. Location: db/src/paraverse_graph/browser.py:317-330, 488-505, 670-674. GraphCatalog.revalidate runs only in the /api/meta and /api/review handlers; schema, rows, card and review_check read the cached schemas, meta and review directly, so a missed graph.loaded event leaves them on the previous build until something calls /api/meta. Suggested fix: revalidate in those handlers, or rate-limit revalidation inside the cached accessors.
