---
type: is
id: is-01m5qxs678mt5qwtt9ne7k32st
title: Reject graph nodes whose exported IDs do not resolve in artifacts
kind: bug
status: in_progress
priority: 2
version: 2
delegate: codex-resume
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-24T21:41:30.471Z
updated_at: 2026-10-24T22:50:20.463Z
started_at: 2026-10-24T22:50:20.463Z
---
At6fc8c39 kb.py:231 only checks envelope and contract. payload_for may return None for wrong same-kind artifact; mapping.py:121 falls back to {}. Counts and uniqueness still pass and publish an empty record. Require every node ID to resolve before writes, including nested day/term IDs. Traced failure path, not observed in original valid export. Parent pv-67zv.
