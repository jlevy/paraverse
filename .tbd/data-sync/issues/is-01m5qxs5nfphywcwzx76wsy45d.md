---
type: is
id: is-01m5qxs5nfphywcwzx76wsy45d
title: Wire CI and require real-dataset integration coverage
kind: task
status: open
priority: 1
version: 1
labels: []
dependencies: []
created_at: 2026-10-24T21:41:29.902Z
updated_at: 2026-10-24T21:41:29.902Z
---
Audited 6fc8c39 has no .github/workflows and eight open Paraverse PRs report empty statusCheckRollup. tests/kb_graph.py:28-30 skips all real-graph callers if default dataset missing; make check can appear successful with no KB coverage. Add pinned CI invoking make check plus Swift tests, initialize loadable dataset, and make required integration lane fail for missing KB. Existing missing-pin issue pv-3rk4. Parent pv-67zv.
