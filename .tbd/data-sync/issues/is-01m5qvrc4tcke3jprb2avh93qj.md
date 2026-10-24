---
type: is
id: is-01m5qvrc4tcke3jprb2avh93qj
title: "PR #6 qodo-5639989300 #5: sponsors can show inflated session counts (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
created_at: 2026-10-24T21:06:06.616Z
updated_at: 2026-10-24T21:06:06.616Z
---
Severity: Medium (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488658. Location: db/src/paraverse_graph/queries.py:263-273 (sponsors). The sponsors query matches one row per sponsorship edge before counting hosted sessions and groups by organization and tier, so an organization sponsoring several events at one tier has its hosted sessions counted once per sponsorship, and differing tiers produce several rows. Suggested fix: count distinct hosted sessions independently of sponsorship edges, and test a sponsor linked to two events.
