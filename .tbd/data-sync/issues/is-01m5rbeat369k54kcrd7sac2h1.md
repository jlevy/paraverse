---
type: is
id: is-01m5rbeat369k54kcrd7sac2h1
title: "PR13 r4369238733: preserve meetup recipient context in chat cards"
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:40:14.786Z
updated_at: 2026-10-25T01:40:30.941Z
started_at: 2026-10-25T01:40:30.940Z
---
High in review5640939881: https://github.com/jlevy/paraverse/pull/13#discussion_r4369238733 . ContentView builds LumaEventCard without recipients; capture recommendations with draft/follow-up messages and pass to both card surfaces. Preserve profile-generation ownership and explicit reviewed invitations. Mocked Swift regression only.
