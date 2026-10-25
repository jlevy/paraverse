---
type: is
id: is-01m5r9fja4vd1d52a54rx3f31t
title: "PTC PR1: remove non-bio family and third-party detail before publishing"
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:58.070Z
updated_at: 2026-10-25T01:06:11.015Z
started_at: 2026-10-25T01:06:11.013Z
---
Dedicated privacy review atafa82b5 found non-biographical family/named-third-party content copied from raw LinkedIn project text into a generated profile. Remove the irrelevant project detail from preserved inputs, refresh manifest hashes, rebuild/validate and reconstruct final feature history from actual main so unsafe intermediate payloads are not introduced into default ancestry. Never quote the sensitive value in a public issue or review.
