---
type: is
id: is-01m5ra13s2j4kscp87k9sze6zd
title: "PR13 Qodo r4369199215: bind meetup location to canonical venue"
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
created_at: 2026-10-25T01:15:33.025Z
updated_at: 2026-10-25T01:18:17.977Z
started_at: 2026-10-25T01:18:17.965Z
---
High review5640894815 at0333a174: draft source URL and venue-name substring do not bind address; arbitrary model address reaches Luma. https://github.com/jlevy/paraverse/pull/13#discussion_r4369199215. Select fixed trusted venue ID or unambiguous verified source and derive canonical name/address/source/hours; reject mismatch before save and revalidate legacy create. Onlyluma_service andsynthetic tests, no liveLuma/invites; root owns integration/push/merge.
