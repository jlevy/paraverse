---
type: is
id: is-01m5rag2t84v7ayynmn5hexpvs
title: "PTC followup: report malformed artifact metadata without aborting validation"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:23:43.559Z
updated_at: 2026-10-25T01:23:43.559Z
---
Qodo PR1 review5640916085 inline4369217567 atb90efb0. Missing schema metadata or unknown envelope raises ValueError/KeyError outside validate_kb reporting loop. Record per-artifact invalidity and continue; no malformed artifacts in current validated snapshot.
