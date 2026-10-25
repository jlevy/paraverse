---
type: is
id: is-01m5r2sf57z8vtvwgzdpbh0ffr
title: "PR #14 Qodo r4368869162: Attendee recommendations lose their proof"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:09:02.502Z
updated_at: 2026-10-25T04:46:17.245Z
started_at: 2026-10-24T23:15:30.673Z
closed_at: 2026-10-25T04:46:17.245Z
close_reason: Completed in merged Paraverse PR14, merge 01cae9f21e5f3d0f5c95b52027bfa223959ab457. Final safe merged dataset pins a823679/64e3c0e match manifest; 4977+132 artifacts valid, deterministic native assets, owned explicit attendance proof and expected browser identity gates verified. Independent F/G/H carry exact source; final upper-stack 96 backend/64 release Swift tests pass. Both safe datasets run in browser8879 (5536 entities/25564 relationships); all nonpressing findings remain separate open beads.
resolution: null
duplicate_of: null
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
