---
type: is
id: is-01m5qvrc4tcke3jprb2avh93qj
title: "PR #6 qodo-5639989300 #5: sponsors can show inflated session counts (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex-db-reviews
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:06.616Z
updated_at: 2026-10-24T21:29:47.289Z
started_at: 2026-10-24T21:23:17.205Z
closed_at: 2026-10-24T21:29:47.289Z
close_reason: "Fixed in 7bc4f4c42ce928a67d74d26b27c6c3a369715b48 (fix(db): finish graph browser review corrections). New regression tests failed before the corresponding fixes; make lint now passes with 0 errors/warnings and make test passes all 89 tests. Retry/backoff, KB mutation guards, epoch sorting, capacity threshold, sponsor aggregation, missed-event cache refresh and dataset collisions are covered."
resolution: null
duplicate_of: null
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488658. Location: db/src/paraverse_graph/queries.py:263-273 (sponsors). The sponsors query matches one row per sponsorship edge before counting hosted sessions and groups by organization and tier, so an organization sponsoring several events at one tier has its hosted sessions counted once per sponsorship, and differing tiers produce several rows. Suggested fix: count distinct hosted sessions independently of sponsorship edges, and test a sponsor linked to two events.
