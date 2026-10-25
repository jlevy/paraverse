---
type: is
id: is-01m5r4z53kdqqt700hay6f5nh7
title: Ensure PTC and chat-research work has PR coverage
kind: task
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T23:47:05.938Z
updated_at: 2026-10-25T00:16:59.112Z
started_at: 2026-10-24T23:47:19.845Z
closed_at: 2026-10-25T00:16:59.111Z
close_reason: "All substantive branches from this chat now have PR coverage: new researchPR17, preserved unfinished regressiondraftPR18, existing PTCdatasetPR1, and merged browserPR10/16. Historical backups/restacks map to those PRs; no unique unpublished production changes found. Schema implementation remains open as pv-eu5d."
resolution: null
duplicate_of: null
---
User requests every branch from this chat to have PR coverage. Audit historical PTC snapshots against merged PR10 and PR16, publish chat-over-graph/source-files research with its Mermaid diagram, verify PTC dataset PR1, and preserve any unique deferred schema regression in an explicitly draft followup rather than duplicating merged code.

## Notes

Coverage audit complete: research codex/falkor-chat-research published as ready PR17 https://github.com/jlevy/paraverse/pull/17 headbfd34ca; unique deferred WIP schema reproduction published separately as draftPR18 head8519cb5. PTC dataset branchcodex/ptc-knowledge-base is clean, fully pushed atafa82b5, and covered by open draftptc2026-mdPR1 withbothdatasetchecksSUCCESS. PTC restack/backuprefs f4dc5aa,69ba517,d2b9a58,cd5cd49,b8dd895,861d474,4c31b9a are superseded or patch-equivalent to mergedPR10;138da52 is mergedPR16. Backup38c19ad has no other unique production fix; its sole unique test is nowPR18. No native13/14/15 branches changed. ResearchFlowmark,19relative links,footers,anddiffcheckpass. Paraverse has no configured GitHub CI checks; draftPR18 explicitly documents1expectedfailure1pass.
