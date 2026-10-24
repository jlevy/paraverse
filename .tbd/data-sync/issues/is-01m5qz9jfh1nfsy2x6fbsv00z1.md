---
type: is
id: is-01m5qz9jfh1nfsy2x6fbsv00z1
title: "PR #8 Qodo 5640168732 #1: validate graph-referenced artifacts of every extension"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvkvm4t4kd9pjkwvhdbbs8
hold: null
hold_until: null
created_at: 2026-10-24T22:07:55.888Z
updated_at: 2026-10-24T22:50:38.634Z
started_at: 2026-10-24T22:08:34.506Z
closed_at: 2026-10-24T22:50:38.634Z
close_reason: "Fixed and landed in Paraverse PRs #6–#8, merged 2026-10-24 at main beabb16f0332ce6afcdb047b12cdb04b4dc59025. Combined owning-layer suite: 143 passed, clean exit; lint/format/type checks passed. Final independent reviews PV6F (5640363560) and PV8E (5640363811) report no findings. Qodo dispositions: PR6 comments 6390252206, 6390447043; PR8 comments 6390252630, 6390447546. User explicitly approved merging with local checks because neither repo has CI configured."
resolution: null
duplicate_of: null
---
High finding https://github.com/jlevy/paraverse/pull/8#discussion_r4368644160. artifact_paths currently ignores .yml and arbitrary graph-referenced paths although loader accepts them; discover all referenced artifacts and unreferenced .yml, choose Markdown/YAML reader by content, add invalid.yml beside valid.md regression.
