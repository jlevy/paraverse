---
type: is
id: is-01m5r9d8z11zqajn5xr0g5sv0j
title: Investigate stale Knowledge Base overview endpoints
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:04:42.977Z
updated_at: 2026-10-25T01:04:42.977Z
---
Observed while verifying slash search in Paraverse Final: existing browser service on port 8766 returns Not Found for overview sections, while metadata, entity pages, and search work. Overview source changes are present, so check whether a reused older browser process needs a controlled refresh before changing code. Separate from fixed slash-search layout pv-2d1y.
