---
type: is
id: is-01m5qwr1fm58a58924w1kmxfk5
title: Port closed enforced v2 contracts to verified Universe KB
kind: task
status: in_progress
priority: 1
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwpf7egtr4snchk904vy3s
hold: null
hold_until: null
created_at: 2026-10-24T21:23:24.275Z
updated_at: 2026-10-24T23:30:17.884Z
started_at: 2026-10-24T21:23:41.121Z
---
Apply the saved adapted contracts-v2 port on kb/contracts-v2. Rebase onto final privacy-verified kb/data; regenerate 18 schemas and KB from target pipeline; prove payload/search/graph equality; run make check and softschema repair; publish after dependency confirmation.

## Notes

Previous old-import validation/publication claim is superseded. Current isolated own-v2 port starts ONLY at final corrected data71193ec773f1e523f8f3ff0a5198c81d2e1c9209; all7 older unsafe/intermediate ancestors absent. Fresh18schemas and external KB rebuild:5001file inventory equal,4977parsed payloads identical, Markdown bodies/frontmatter-exceptmetadata/graph/search/other bytes0diff, schema changes onlyclosure+v2 metadata. makecheck passed4977valid/0invalid,210tests81.30s,Ruffclean,types0errors0warnings. Full stock4977repairdryrun still running. Root has newly reported source High fixes in flight; publication stays held. Replay ONLY own migration onto replacement parent; carry artifact proof only if exactKBbytes unchanged. No PR push from this worker.
