---
type: is
id: is-01m5qxs678mt5qwtt9ne7k32st
title: Reject graph nodes whose exported IDs do not resolve in artifacts
kind: bug
status: closed
priority: 2
version: 3
delegate: codex-resume
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T21:41:30.471Z
updated_at: 2026-10-24T22:50:38.664Z
started_at: 2026-10-24T22:50:20.463Z
closed_at: 2026-10-24T22:50:38.664Z
close_reason: "Fixed and landed in Paraverse PRs #6–#8, merged 2026-10-24 at main beabb16f0332ce6afcdb047b12cdb04b4dc59025. Combined owning-layer suite: 143 passed, clean exit; lint/format/type checks passed. Final independent reviews PV6F (5640363560) and PV8E (5640363811) report no findings. Qodo dispositions: PR6 comments 6390252206, 6390447043; PR8 comments 6390252630, 6390447546. User explicitly approved merging with local checks because neither repo has CI configured."
resolution: null
duplicate_of: null
---
At6fc8c39 kb.py:231 only checks envelope and contract. payload_for may return None for wrong same-kind artifact; mapping.py:121 falls back to {}. Counts and uniqueness still pass and publish an empty record. Require every node ID to resolve before writes, including nested day/term IDs. Traced failure path, not observed in original valid export. Parent pv-67zv.
