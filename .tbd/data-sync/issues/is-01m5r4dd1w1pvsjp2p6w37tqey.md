---
type: is
id: is-01m5r4dd1w1pvsjp2p6w37tqey
title: Reintroduce cross-restart browser cache without weakening runtime graph isolation
kind: task
status: open
priority: 2
version: 2
labels: []
dependencies: []
created_at: 2026-10-24T23:37:24.282Z
updated_at: 2026-10-24T23:48:53.897Z
---
Deferred from PR15 by coordinator decision under the user priority-first instruction. Preserve source ref codex/kb-fast-entry-original-1cd2c057 at1cd2c0579971b0effa8ddd48e66573c26bfa3fb2. Original implementation b4dcda1 adds graph cache keys/reuse in db/src/paraverse_graph/selection.py, browser_cache_key metadata in loader.py, stable browser names and save in cli.py, tests in db/tests/test_selection.py and test_cli_selection_review.py, and a6.27x restart claim in docs. New merged main16 creates unique per-runtime graphs and closes/deletes only its owned view, including failed second launches; stable retained names conflict with that isolation/cleanup contract. Future implementation needs an explicit compatible retained cache/template lifecycle and meaningful concurrent/failed-startup/shutdown plus restart benchmarks. Current PR15 retains native warm owned-server reuse and fast KB entry; cross-restart DB caching and its claims are removed, not left as dead helpers. Original measured evidence/code/tests remain recoverable in preserved ref; do not treat6.27x as measured on the reconciled implementation.

## Notes

Deferred in published PR15 f565556ccde57af4a8501ce57caf5074000a71dc. All DBsource/tests/docs are byte-identical to mergedmain8378469, preserving unique owned runtime graphs and cleanup. Native warmownedserverreuse/directentry/navigation preserved. Original1cd2c05 source remains on codex/kb-fast-entry-original-1cd2c057. Current55native/64backend/35graphisolation tests pass. PR15 title/body remove cross-restart6.27x/cache claims and name this openP2follow-up. Implement compatible persistence only in an additional PR with concurrency/lifecycle evidence.
