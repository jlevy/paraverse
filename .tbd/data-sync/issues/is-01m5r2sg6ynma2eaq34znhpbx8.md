---
type: is
id: is-01m5r2sg6ynma2eaq34znhpbx8
title: "PR #14 Qodo r4368869185: Closing the browser early can leave a database server running"
kind: bug
status: closed
priority: 2
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:09:03.581Z
updated_at: 2026-10-25T00:31:03.784Z
started_at: 2026-10-24T23:17:39.773Z
closed_at: 2026-10-25T00:31:03.783Z
close_reason: Fixed fully-ready native shutdown in 8cce7ae; real CLI RED/GREEN, unrelated Redis preserved, 3 focused tests and lint/types pass.
resolution: null
duplicate_of: null
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869185. Location: native/Sources/CommonGround/KnowledgeBaseBrowser.swift:273. 5\. Closing the browser early can leave a database server running 🐞 Bug ☼ Reliability


releaseOwnedProcess sends SIGTERM and, after 2 s, SIGKILL to the Python child only. That child
starts an embedded FalkorDBLite redis-server (via open_db) and loads both datasets before
uvicorn.run installs its SIGTERM handler. If the window closes or the app quits while the browser
is still &quot;Starting…&quot;, or if shutdown takes longer than 2 s, Python dies without running redislite&#x27;s
atexit cleanup. The embedded redis-server is then orphaned, keeps holding the rdb file and memory,
and survives every later close/reopen cycle.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.

## Notes

Fixed517292f: native-owned launcher installs early SIGTERM->SystemExit before CLI import, allowing detached redislite atexit cleanup; native waits35s before exact-owned-child escalation, reopening waits shutdown. Real Redis early-close/reopen2cycles kills both owned daemons while unrelated server responds. Legacy handler-disabled control expectedRED(-15vs143); productionGREEN. Full62backend13.120s and49Swift12.744s. Parent integrates; no db/cli.py edits or push.

Ready-server follow-up fixed in 8cce7aed3ee755604020f55baaea33df4ee40b21 (parent 9037dc0). The original early-close fix did not cover the real Uvicorn/pubsub lifecycle: redislite counted this browser's own pooled connections as separate clients and skipped shutdown. Native runtime now tracks embedded DBs opened by its CLI call, disconnects its own pool after CLI cleanup, then invokes embedded close; the existing guard still preserves separately connected clients. No DB component or Swift edits.

RED: supplied real-CLI probe loaded both saved datasets (5,651 nodes / 25,802 edges), reached HTTP readiness, exited Python143, but owned Redis remained alive after2s (94,784KiB RSS). Exact private daemon cleaned. New real-Uvicorn regression independently failed on owned Redis survival.

GREEN: actual both-dataset CLI reached readiness8.325s, exited143, owned Redis absent after2s; recorded PID41617 absent at final evidence capture. Final3runtime tests22.544s pass, including early close/reopen and fully-ready shutdown with unrelated Redis same-PID+PING assertions. Ruff passes; BasedPyright0errors/0warnings. Only backend/kb_browser_runtime.py and backend/test_kb_browser_runtime.py changed in isolated detached external worktree. Parent owns integration/publication; no push/merge.

Evidence: /private/tmp/claude-502/-Users-levy-wrk-github-paraverse/d31a7712-52d0-48af-a28f-fa903f3a5198/scratchpad/review/dataset-readiness-pr14-redis-fix.json
