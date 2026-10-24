---
type: is
id: is-01m5r1x1102zyp94m0fzzeadfh
title: "PR #11 Qodo r4368798004: isolate pipeline lock configuration"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
created_at: 2026-10-24T22:53:30.527Z
updated_at: 2026-10-24T22:53:30.527Z
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368798004 cli.py handoff inherits curation UV_EXCLUDE_NEWER, overriding pipeline uv.toml and potentially rewriting lock. Remove inherited override and invoke uv run --locked; verify subprocess environment.
