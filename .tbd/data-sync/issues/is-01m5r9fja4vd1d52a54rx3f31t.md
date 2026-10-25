---
type: is
id: is-01m5r9fja4vd1d52a54rx3f31t
title: "PTC PR1: remove non-bio family and third-party detail before publishing"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:58.070Z
updated_at: 2026-10-25T01:44:08.173Z
started_at: 2026-10-25T01:06:11.013Z
closed_at: 2026-10-25T01:44:08.173Z
close_reason: "Fixed in PTC PR1 feature180815d15134ac2ebb41f95812eba3e5719143db and verified merged as64e3c0e7c5923baf74c88e408e642837da1bc54f. Final D/E clean;29tests and both CI pass;132artifacts valid. Public PR: https://github.com/jlevy/ptc2026-md/pull/1"
resolution: null
duplicate_of: null
---
Dedicated privacy review atafa82b5 found non-biographical family/named-third-party content copied from raw LinkedIn project text into a generated profile. Remove the irrelevant project detail from preserved inputs, refresh manifest hashes, rebuild/validate and reconstruct final feature history from actual main so unsafe intermediate payloads are not introduced into default ancestry. Never quote the sensitive value in a public issue or review.
