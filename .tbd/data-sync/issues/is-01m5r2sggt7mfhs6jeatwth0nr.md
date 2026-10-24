---
type: is
id: is-01m5r2sggt7mfhs6jeatwth0nr
title: "PR #14 Qodo r4368869190: Recommended people's cards lose their avatars"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:03.897Z
updated_at: 2026-10-24T23:09:03.897Z
---
Low. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869190. Location: backend/chat_service.py:17. 6\. Recommended people's cards lose their avatars 🐞 Bug ≡ Correctness


The new recommendation_people records never set avatar_asset, even though exported people carry
avatarAsset (copied from the legacy attendee assets). hydrate_recommendations reads
p.get(&#x27;avatar_asset&#x27;), so every recommendation card now gets avatarAsset: nil and
MeetPersonCard falls back to initials.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
