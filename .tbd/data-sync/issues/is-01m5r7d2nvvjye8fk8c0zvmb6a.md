---
type: is
id: is-01m5r7d2nvvjye8fk8c0zvmb6a
title: "PR13 Qodo r4369000083: recover malformed profile cache"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T00:29:39.386Z
updated_at: 2026-10-25T00:29:39.386Z
---
Verified Medium at13748: profile_service.py:145 writes final cache directly; read_cache:150-152 decodes/indexes before expiry/recovery, repeatedly failing after interrupted publication. refresh=true bypass exists. Atomically publish this derived cache and treat malformed JSON/shape as a miss; separate from already-addressed chat cache. Follow-up after native stack. Original https://github.com/jlevy/paraverse/pull/13#discussion_r4369000083.
