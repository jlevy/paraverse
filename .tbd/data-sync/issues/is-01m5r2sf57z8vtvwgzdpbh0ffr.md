---
type: is
id: is-01m5r2sf57z8vtvwgzdpbh0ffr
title: "PR #14 Qodo r4368869162: Attendee recommendations lose their proof"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:09:02.502Z
updated_at: 2026-10-24T23:37:17.655Z
started_at: 2026-10-24T23:15:30.673Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869162. Location: backend/chat_service.py:17. 2\. Attendee recommendations lose their proof 🐞 Bug ≡ Correctness


recommendation_people() sets each chat person&#x27;s evidence to biographyProvenance instead of the
attendee&#x27;s participation quote, while reading only the people asset. For the self-reported attendee
whose biography and biography provenance are absent, chat receives neither public attendance quote
retained in the separate attendee export, despite requiring explicit statements to ground attendance
reasons.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.

## Notes

Fixed1382a6b: join kb-attendees by kbID or id, supply own attendance quote/source_url/evidence_sources separately from biography_provenance. Empty biography remains empty. Targeted22backendPASS; full62backendPASS13.120s. Parent integrates; no push.
