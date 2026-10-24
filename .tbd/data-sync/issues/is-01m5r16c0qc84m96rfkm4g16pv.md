---
type: is
id: is-01m5r16c0qc84m96rfkm4g16pv
title: Document architecture, softschema sync and app access
kind: task
status: closed
priority: 2
version: 5
delegate: codex@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T22:41:08.103Z
updated_at: 2026-10-24T22:56:34.095Z
started_at: 2026-10-24T22:41:39.129Z
closed_at: 2026-10-24T22:56:34.094Z
close_reason: Requested architecture diagram, developer technology inventory and schema/sync/app documentation are published and verified in PR12.
resolution: null
duplicate_of: null
---
Explain the authoritative dataset vs FalkorDB projection; schema metadata and opt-in validation; pinned dataset updates, full staging reloads and watch limitations; recommended app API, load-aware caching and deployment boundary. Include in the Overview/docs PR requested by the user.

## Notes

Published in draft PR12 https://github.com/jlevy/paraverse/pull/12 at ee59b67: compact GitHub-native Mermaid highlights Bright Data and FalkorDB, with full per-layer technology inventory and Qodo/tbd/softschema developer table. Added docs/app-integration.md covering authoritative records vs projection, compiled schema metadata and opt-in validation, pinned updates, full staging reloads/watch limitations, HTTP API caching and hosting boundary. Flowmark and diff checks pass; native GitHub render visually verified. Full associated graph code check:148 tests passed/no skips plus lint/types. Automatic review blocked a separate integration-bead closure; this command changes only documentation bead pv-gzda.
