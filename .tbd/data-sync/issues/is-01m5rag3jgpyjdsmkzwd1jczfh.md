---
type: is
id: is-01m5rag3jgpyjdsmkzwd1jczfh
title: "PTC followup: confine manifest reads and reject raw symlink escapes"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:23:44.335Z
updated_at: 2026-10-25T01:23:44.335Z
---
Qodo PR1 review5640916085 inline4369217575 atb90efb0. Manifest keys/symlinks can cause validator reads outside raw directory before mismatch reporting. Confine resolved paths and reject symlinked raw entries. Current manifest is manually authored, captured files are regular and confined, and no file content is disclosed by validator; deferred hardening of a trusted local input boundary.
