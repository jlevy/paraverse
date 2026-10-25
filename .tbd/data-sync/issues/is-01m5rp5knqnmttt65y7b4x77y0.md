---
type: is
id: is-01m5rp5knqnmttt65y7b4x77y0
title: "PR15 Qodo r4369675428: Await owned-server shutdown before completing app quit"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T04:47:43.285Z
updated_at: 2026-10-25T04:47:43.285Z
---
Review https://github.com/jlevy/paraverse/pull/15#discussion_r4369675428 (5641559490). Source-verified at final tree de096815: releaseOwnedProcess synchronously sends SIGTERM then schedules grace-period/SIGKILL cleanup in a Task; applicationWillTerminate does not await that task before app exit. A child that hangs during SIGTERM can survive. This is conditional fallback coverage, not a demonstrated current normal-shutdown leak; prior independent ready-server SIGTERM/Python/Redis cleanup tests pass. Distinct from fixed pv-tvq0 Python startup/ready lifetime repair. Follow up with terminateLater and bounded owned-child shutdown completion, preserving external-server isolation. Accepted nonpressing Medium/P2 deferral; keep OPEN for merge.
