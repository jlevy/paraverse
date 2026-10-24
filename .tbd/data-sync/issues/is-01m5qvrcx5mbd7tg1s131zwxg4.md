---
type: is
id: is-01m5qvrcx5mbd7tg1s131zwxg4
title: "PR #6 qodo-5639989300 #7: schema, rows and single-check endpoints can serve the old build (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 3
version: 3
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:07.396Z
updated_at: 2026-10-24T21:29:47.294Z
started_at: 2026-10-24T21:23:17.211Z
closed_at: 2026-10-24T21:29:47.294Z
close_reason: "Fixed in 7bc4f4c42ce928a67d74d26b27c6c3a369715b48 (fix(db): finish graph browser review corrections). New regression tests failed before the corresponding fixes; make lint now passes with 0 errors/warnings and make test passes all 89 tests. Retry/backoff, KB mutation guards, epoch sorting, capacity threshold, sponsor aggregation, missed-event cache refresh and dataset collisions are covered."
resolution: null
duplicate_of: null
---
Severity: Low (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488664. Location: db/src/paraverse_graph/browser.py:317-330, 488-505, 670-674. GraphCatalog.revalidate runs only in the /api/meta and /api/review handlers; schema, rows, card and review_check read the cached schemas, meta and review directly, so a missed graph.loaded event leaves them on the previous build until something calls /api/meta. Suggested fix: revalidate in those handlers, or rate-limit revalidation inside the cached accessors.
