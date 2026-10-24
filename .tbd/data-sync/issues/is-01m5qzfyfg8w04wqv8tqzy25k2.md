---
type: is
id: is-01m5qzfyfg8w04wqv8tqzy25k2
title: Integrate verified overview and hackathon docs after browser stack lands
kind: task
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T22:11:24.771Z
updated_at: 2026-10-24T22:24:55.649Z
started_at: 2026-10-24T22:19:08.364Z
---
Feature is published on codex/kb-browser-overview. Overview commit7f2bb0e adds default nav/welcome page, cached aggregate API, stable identity for quality, exact source/coverage metrics, tests and docs; prior hackathon/audit docs commit0855a1e is also on branch. Coordinate integration after current browser stack and PTC layer land; cherry-pick the relevant commits onto final base and resolve against latest review fixes rather than merging older stack history. Local original-KB preview runs on18866;119 tests/no skips and lint/types pass; strong review findings fixed; desktop/mobile/dark QA passed. Existing shared root and PRstack untouched by this feature.

## Notes

Integrating as standalone codex/kb-overview-pr after PRs6–8 land, excluding PR9 dataset-pin changes. Latest75f2771 destroy/disposed/draft lifecycle preserved; legacy frontend_reload mount stub updated and passing. User-requested shared title/row-count text-baseline styling fixed in818f6c6 and visually verified at preview18866. Final sanitizedKBc6b4faa frozen-source make check running on external scratch; PR creation next.
