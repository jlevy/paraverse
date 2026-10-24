---
type: is
id: is-01m5r3vr8txvmqfkfde5crbb5b
title: "PR #14 B1: require owned self-report for attendance export"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:27:45.944Z
updated_at: 2026-10-24T23:37:18.227Z
started_at: 2026-10-24T23:28:01.120Z
---
Security review5640564360 B1: schema-valid confirmed attendee with no owned account or own attendance self-report emits attendee=true. Export only attendance claims backed by validated owned account and explicit self-report evidence; synthetic negative regression; preserve official roles.

## Notes

Fixed1382a6b: attendee role/flag only with owned HTTPS profile post, explicit first-person event attendance quote, self_reported status; reject third-party/negated/non-attendance mentions, omit unsupported attendee role while retaining speaker/judge/host. Synthetic RED/GREEN; bundled existing self-report1/1 retained. Full62backendPASS. Parent integrates; no push.
