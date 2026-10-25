---
type: is
id: is-01m5r2sggt7mfhs6jeatwth0nr
title: "PR #14 Qodo r4368869190: Recommended people's cards lose their avatars"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:09:03.897Z
updated_at: 2026-10-25T04:45:23.568Z
started_at: 2026-10-25T04:45:10.486Z
closed_at: 2026-10-25T04:45:23.568Z
close_reason: "Rebutted by independent PR14 A/G/H and passing roster/avatar regressions: roster is nine judges plus one host, not ten judges; recommendation sprites resolve by stable person ID. No current bundled avatar regression was demonstrated. PR14 merged 01cae9f21e5f3d0f5c95b52027bfa223959ab457; dispositions https://github.com/jlevy/paraverse/pull/14#issuecomment-6393563619."
resolution: null
duplicate_of: null
---
Low. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869190. Location: backend/chat_service.py:17. 6\. Recommended people's cards lose their avatars 🐞 Bug ≡ Correctness


The new recommendation_people records never set avatar_asset, even though exported people carry
avatarAsset (copied from the legacy attendee assets). hydrate_recommendations reads
p.get(&#x27;avatar_asset&#x27;), so every recommendation card now gets avatarAsset: nil and
MeetPersonCard falls back to initials.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
