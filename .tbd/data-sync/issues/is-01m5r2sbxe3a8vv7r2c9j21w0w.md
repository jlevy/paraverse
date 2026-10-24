---
type: is
id: is-01m5r2sbxe3a8vv7r2c9j21w0w
title: "PR #13 Qodo r4368861819: Logging out exposes the previous profile"
kind: bug
status: open
priority: 1
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:08:59.181Z
updated_at: 2026-10-24T23:08:59.181Z
---
High. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861819. Location: native/Sources/CommonGround/Onboarding.swift:102. 1\. Logging out exposes the previous profile 🐞 Bug ⛨ Security


ProfileStore.logOut() clears the workspace but immediately saves the departing user&#x27;s profile as
the onboarding draft, while startNewProfile() also retains a restorable copy of that workspace.
After logout, the next person can see the prior profile by starting onboarding or restore its saved
workspace from the Profile menu.

Awaiting coordinator security/correctness triage; no deferral, rebuttal or decline decided by administrative agent.
