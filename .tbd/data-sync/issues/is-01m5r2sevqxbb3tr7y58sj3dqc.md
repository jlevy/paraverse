---
type: is
id: is-01m5r2sevqxbb3tr7y58sj3dqc
title: "PR #14 Qodo r4368869156: Judge roster tests fail on a missing judge"
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:02.198Z
updated_at: 2026-10-24T23:09:02.198Z
---
High. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869156. Location: native/Assets/WorldArt/characters.json:330. 1\. Judge roster tests fail on a missing judge 🐞 Bug ≡ Correctness


characters.json adds a character for Husan Mavlonov, but the generated judge roster has no
corresponding person. The roster therefore has eight judges and one host, while the new tests
require nine judges and ten people.

Awaiting coordinator security/correctness triage; no deferral, rebuttal or decline decided by administrative agent.
