---
type: is
id: is-01m5r397km3xbh1e06w9zcpwbg
title: "PR #13 C1: render event-answer cards in the sidebar assistant"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
created_at: 2026-10-24T23:17:39.059Z
updated_at: 2026-10-24T23:17:39.059Z
---
Medium strong review C1 https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640541744 App.swift275 omits Message.eventSessions although Planner populates them and world assistant renders them. Add sidebar event details/calendar controls and regression through known sessionIDs answer; own13commit based17388e5.
