---
type: is
id: is-01m5r3vr8txvmqfkfde5crbb5b
title: "PR #14 B1: require owned self-report for attendance export"
kind: bug
status: in_progress
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.944Z
updated_at: 2026-10-24T23:39:30.169Z
started_at: 2026-10-24T23:28:01.120Z
---
Security review5640564360 B1: schema-valid confirmed attendee with no owned account or own attendance self-report emits attendee=true. Export only attendance claims backed by validated owned account and explicit self-report evidence; synthetic negative regression; preserve official roles.

## Notes

Fixed1382a6b +ea00e26: attendee role/flag requires owned HTTPS post, self_reported status, explicit first-person attendance verb and event reference; third-party, negated, non-attendance, and I-am-following-colleagues-at-event mentions rejected. Unsupported attendee role removed while preserving speaker/judge/host. SyntheticRED/GREEN; knownbundledselfreport1/1retained. Full62backend at517292fPASS13.120s; final22chat/exporter at ea00PASS0.103s. Parent integrates; no push.
