---
type: is
id: is-01m5qxs72sszs9yg0m0akf5x5j
title: Distinguish successful graph swap from notification failure
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-24T21:41:31.352Z
updated_at: 2026-10-24T21:41:31.352Z
---
At6fc8c39 loader.py:206 performs RENAME before publish209. Pubsub failure raises from load_graph after live graph already changed, contradicting broad failed-load preservation guarantee. Return committed load result with notification warning/retry and make watch behavior consistent. Parent pv-67zv.
