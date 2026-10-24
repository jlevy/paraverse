---
type: is
id: is-01m5r0byfzk7t1f1c3dz33vec3
title: Publish native app data and embedded KB browser on upstream stack
kind: task
status: in_progress
priority: 2
version: 3
delegate: codex@tinas-macbook-pro.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T22:26:42.302Z
updated_at: 2026-10-24T22:50:35.322Z
started_at: 2026-10-24T22:27:27.678Z
---
Verify jlevy/paraverse provenance, include current upstream DB stack and PR 11, refresh native data from validated dataset snapshots, rebuild and document FalkorDB/softschema/native wiring.

## Notes

Prepared clean native app import and KB integration as two layers above PR 11 on upstream stack 5. Universe dataset c6b4faa and PTC afa82b5 are pinned with full schema validation. Independent review A1-A4 and B1-B2 addressed: contact redaction, clean-clone profile retention, synthetic fixture, generated-text provenance, conference recommendation isolation, and owned-server close/reopen lifecycle. Native 44 and backend 56 tests pass; final graph suite after upstream payload loader changes is running. Live embedded browser verified: 5651 nodes and 25802 relationships. App and backend are running from Paraverse-review for parallel user testing. Original checkout and local private research retained.
