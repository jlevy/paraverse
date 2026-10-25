---
type: is
id: is-01m5rag33gb4s13g52j3fsfbzq
title: "PTC followup: include nested manifest filenames in raw provenance inventory"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:23:43.855Z
updated_at: 2026-10-25T01:23:43.855Z
---
Qodo PR1 review5640916085 inline4369217571 atb90efb0. Current inventory excludes every basename manifest.json rather than only the root raw manifest. Require nested files to carry provenance and hash records. Current trusted snapshot has no nested manifest payload; deferred bounded validator followup.
