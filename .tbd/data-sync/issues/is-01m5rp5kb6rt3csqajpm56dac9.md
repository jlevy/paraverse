---
type: is
id: is-01m5rp5kb6rt3csqajpm56dac9
title: "PR15 Qodo r4369675424: Stop running app copies before rebuilding their bundle"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T04:47:42.949Z
updated_at: 2026-10-25T04:47:42.949Z
---
Review https://github.com/jlevy/paraverse/pull/15#discussion_r4369675424 (5641559490). Source-verified at final tree de096815: native/run-app.sh invokes build-app.sh before its terminate/wait block. Replacing and signing the running bundle can interrupt graceful shutdown and leave an owned server; no live macOS kill was reproduced and no launcher was executed against active apps. Medium/P2 conditional packaging risk; distinct from pv-mdct renamed-bundle identification and fixed pv-tvq0 Python lifetime cleanup. Later PR should stop copies first or stage and atomically publish the bundle. Accepted nonpressing deferral; keep OPEN for merge.
