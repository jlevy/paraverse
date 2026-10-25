---
type: is
id: is-01m5rag235nsfb54camdnad1tq
title: "PTC followup: coalesce duplicate affiliation evidence"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:23:42.806Z
updated_at: 2026-10-25T01:23:42.806Z
---
Qodo PR1 review5640916085 inline4369217558 atb90efb0. Organizer affiliation and same curated organization/title can become duplicate relationships because full Affiliation objects differ only in evidence. Preserve and union attributed evidence while coalescing identical relationship facts. Explicitly deferred as nonpressing after current privacy gate.
