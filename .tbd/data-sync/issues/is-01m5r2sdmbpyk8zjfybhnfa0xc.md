---
type: is
id: is-01m5r2sdmbpyk8zjfybhnfa0xc
title: "PR #13 Qodo r4368861855: A cancelled plan can unlock the ui mid-request"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:00.938Z
updated_at: 2026-10-24T23:09:00.938Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861855. Location: native/Sources/CommonGround/Plan.swift:149. 8\. A cancelled plan can unlock the ui mid-request 🐞 Bug ☼ Reliability


At the end of the generate() task, generatingRecommendations and busy are set to false
unconditionally, even if the task was cancelled. reset(), which start(for:) also calls, cancels
work and clears busy right away, so a new generate() or send() can begin while the old task
is still finishing. When the old task exits, it clears busy for the new request, which lets the
user start overlapping requests and leaves the loading state wrong.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
