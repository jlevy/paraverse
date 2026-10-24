---
type: is
id: is-01m5qwr1fm58a58924w1kmxfk5
title: Port closed enforced v2 contracts to verified Universe KB
kind: task
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwpf7egtr4snchk904vy3s
hold: null
hold_until: null
created_at: 2026-10-24T21:23:24.275Z
updated_at: 2026-10-24T22:23:26.804Z
started_at: 2026-10-24T21:23:41.121Z
---
Apply the saved adapted contracts-v2 port on kb/contracts-v2. Rebase onto final privacy-verified kb/data; regenerate 18 schemas and KB from target pipeline; prove payload/search/graph equality; run make check and softschema repair; publish after dependency confirmation.

## Notes

Published https://github.com/jlevy/universe2026-md/pull/12 on codex/contracts-v2 at a8cebdad8d09ad10398878841f2553705d946a42, based directly on final safe KB c6b4faa9a6df7e176bd265f3c3f706d31ec3c3ef. No original unsafe import ancestors. make check: 5092 valid, 0 invalid; 152 tests passed in 78.69s; Ruff clean; BasedPyright 0 errors/warnings. Full dry-run repair: 5092 checked, zero repairs. All payloads, Markdown bodies, file inventory, graph/search exports and KB README byte-identical to safe base; only envelope and schema fields changed. No hosted CI checks or Actions runs are configured. Coordinator owns formal stack 11 linkage, independent review, and merge; leave open until those finish.
