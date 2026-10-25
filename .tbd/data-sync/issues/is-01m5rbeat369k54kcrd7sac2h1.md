---
type: is
id: is-01m5rbeat369k54kcrd7sac2h1
title: "PR13 r4369238733: preserve meetup recipient context in chat cards"
kind: bug
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:40:14.786Z
updated_at: 2026-10-25T01:45:49.761Z
started_at: 2026-10-25T01:40:30.940Z
---
High in review5640939881: https://github.com/jlevy/paraverse/pull/13#discussion_r4369238733 . ContentView builds LumaEventCard without recipients; capture recommendations with draft/follow-up messages and pass to both card surfaces. Preserve profile-generation ownership and explicit reviewed invitations. Mocked Swift regression only.

## Notes

Fixed in isolated commitb12d4acb34adb01ada52340fe74b3879ed31c350 atop transport0a3bde7/base8cf5b045. Message.eventPeople captures latest recommendation context before await; follow-up invite messages retain that exact snapshot. Shared Message.meetupCard passes recipients in App and WorldPlannerPanel; default-empty card initializer removed. Generation guard remains; showing follow-up does not send any invitation. BehavioralRED3missingrecipientassertions -> GREEN15focusedSwiftrelease tests16.677s (productioncompile44.48s). Tests cover empty recommendations on draft replies, latest chat recommendations without mutating savedplan, changes duringawait, followup noextraHTTP, and profile-change cancellation. Synthetic fixtures only, no live provider operations. Sourceclean; no push/primary changes. Root/privacywriter ownsintegration/finalfullgate/dispositions/beadclosure.
