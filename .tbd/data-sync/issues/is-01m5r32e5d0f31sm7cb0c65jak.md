---
type: is
id: is-01m5r32e5d0f31sm7cb0c65jak
title: "PR #11 Qodo r4368826620: resolve selected files relative to root"
kind: bug
status: closed
priority: 2
version: 3
delegate: codex-resume
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:13:56.394Z
updated_at: 2026-10-24T23:20:51.849Z
started_at: 2026-10-24T23:20:32.016Z
closed_at: 2026-10-24T23:20:51.848Z
close_reason: Duplicate tracking consolidated into openpv-wmef for the same PR11 r4368826620 / Qodo summary6390426541 finding1. No fix claimed; explicit follow-up remains open and linked in merged PR11 dispositions/reviewC.
resolution: null
duplicate_of: null
---
Medium finding https://github.com/jlevy/paraverse/pull/11#discussion_r4368826620, also assessed by senior review https://github.com/jlevy/paraverse/pull/11#pullrequestreview-5640489804. curation/src/paraverse_curation/cli.py reports uses relative selected paths from the process directory although --root chooses another curation root. Reproduced at d905f5760c7bc7f379bfa23e488ee6e535ef3d01 through a Make root-probe: --root .. check curation/universe2026-md/additional-people.csv fails to open the list even though it is under the selected root. Absolute file paths and root-based discovery work. Deferred from the header-only PR at the user request to ship the reviewed stack; waits on the curation CLI path-semantics follow-up before expanding intake workflows. Resolve relative paths against root, preserve absolute paths, and add a regression with differing process/root directories.
