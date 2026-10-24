---
type: is
id: is-01m5r2sg6ynma2eaq34znhpbx8
title: "PR #14 Qodo r4368869185: Closing the browser early can leave a database server running"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:03.581Z
updated_at: 2026-10-24T23:09:03.581Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/14#discussion_r4368869185. Location: native/Sources/CommonGround/KnowledgeBaseBrowser.swift:273. 5\. Closing the browser early can leave a database server running 🐞 Bug ☼ Reliability


releaseOwnedProcess sends SIGTERM and, after 2 s, SIGKILL to the Python child only. That child
starts an embedded FalkorDBLite redis-server (via open_db) and loads both datasets before
uvicorn.run installs its SIGTERM handler. If the window closes or the app quits while the browser
is still &quot;Starting…&quot;, or if shutdown takes longer than 2 s, Python dies without running redislite&#x27;s
atexit cleanup. The embedded redis-server is then orphaned, keeps holding the rdb file and memory,
and survives every later close/reopen cycle.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
