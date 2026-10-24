---
type: is
id: is-01m5r2sc7ffx0pnhjswcrrx6w8
title: "PR #13 Qodo r4368861827: Local clients can send luma invitations"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:08:59.502Z
updated_at: 2026-10-24T23:08:59.502Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861827. Location: backend/profile_service.py:261. 3\. Local clients can send luma invitations 🐞 Bug ⛨ Security


Handler.do_POST() treats a missing Origin header as sufficient to dispatch /luma requests,
without authenticating the caller. Any process able to connect to the localhost service can request
the demo recipient mapping and, when Luma is connected, create an event or submit invitations using
its saved authorization.

Awaiting coordinator security/correctness triage; no deferral, rebuttal or decline decided by administrative agent.
