---
type: is
id: is-01m5r3vr8txvmqfkfde5crbb5b
title: "PR #14 B1: require owned self-report for attendance export"
kind: bug
status: closed
priority: 2
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.944Z
updated_at: 2026-10-25T04:46:17.266Z
started_at: 2026-10-24T23:28:01.120Z
closed_at: 2026-10-25T04:46:17.266Z
close_reason: Completed in merged Paraverse PR14, merge 01cae9f21e5f3d0f5c95b52027bfa223959ab457. Final safe merged dataset pins a823679/64e3c0e match manifest; 4977+132 artifacts valid, deterministic native assets, owned explicit attendance proof and expected browser identity gates verified. Independent F/G/H carry exact source; final upper-stack 96 backend/64 release Swift tests pass. Both safe datasets run in browser8879 (5536 entities/25564 relationships); all nonpressing findings remain separate open beads.
resolution: null
duplicate_of: null
---
Security review5640564360 B1: schema-valid confirmed attendee with no owned account or own attendance self-report emits attendee=true. Export only attendance claims backed by validated owned account and explicit self-report evidence; synthetic negative regression; preserve official roles.

## Notes

Fixed1382a6b +ea00e26: attendee role/flag requires owned HTTPS post, self_reported status, explicit first-person attendance verb and event reference; third-party, negated, non-attendance, and I-am-following-colleagues-at-event mentions rejected. Unsupported attendee role removed while preserving speaker/judge/host. SyntheticRED/GREEN; knownbundledselfreport1/1retained. Full62backend at517292fPASS13.120s; final22chat/exporter at ea00PASS0.103s. Parent integrates; no push.
