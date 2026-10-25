---
type: is
id: is-01m5qxs5yk9x3sfc4x30ab74hj
title: Reconcile migrated attendance evidence and profile freshness
kind: task
status: open
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T21:41:30.194Z
updated_at: 2026-10-25T04:41:25.267Z
started_at: 2026-10-25T01:51:13.552Z
---
Original common-ground 2d42d86 vs local Universe kb/data795a50a: all578 speaker IDs/all520 sessions preserved, but12 non-speaker IDs removed and1 account-linked identity reintroduced under different ID (11 people absent). All12 originals have public_self_report URL and quoted public evidence; cannot classify all removals as necessary privacy exclusions without reconciliation. Candidate additionally has8 stale bios and1 missing bio. Check allowed attendance evidence against data policy and intentional exclusions; preserve identity continuity, regenerate or remove stale generated text. No private names copied. Dataset work belongs Universe repo; parent pv-67zv.

## Notes

Reconciled against Universe main a82367923bee34147da575dbd0cef17b5bc285a8, Paraverse PR16 merge 83784693e74e18a725156584a578590134cf41dd and current native stack b33f9fb98a97fd177729edc81743ad05b5b3edef. Profile/publication reconciliation is complete: final 577 profiles contain 569 valid attached bios; 31 retained bios remain honestly stale. Final data E/F audits checked the cited facts: 24 earlier stale entries retain their cited facts, seven newly stale entries changed only uncited website/recent-writing facts. Invalid or orphaned derived text was omitted. This does not authorize relabeling stale bios current or claim independent verification of every source statement. The native public-attendee layer retains all 12 original stable IDs with public evidence (pv-u50r), but that proves native continuity only; no complete per-identity cross-corpus reconciliation establishes all 12 as canonical Universe attendees. Remaining scope is a future evidence-backed mapping of legacy attendee identities to the scoped canonical dataset, with each omission or identity change individually reconciled. Keep OPEN P2 as parent-approved nonpressing work; current admission uses owned public self-report proof. Related follow-ups: pv-r4w0 for standalone GitHub attendance references and pv-923x for coverage reporting. Final audits: https://github.com/jlevy/universe2026-md/pull/9#pullrequestreview-5640591820 and https://github.com/jlevy/universe2026-md/pull/9#pullrequestreview-5640616759. Evidence: /private/tmp/claude-502/-Users-levy-wrk-github-paraverse/d31a7712-52d0-48af-a28f-fa903f3a5198/scratchpad/review/dataset-readiness-stale-bead-reconciliation.json
