---
type: is
id: is-01m5r1x1102zyp94m0fzzeadfh
title: "PR #11 Qodo r4368798004: isolate pipeline lock configuration"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
hold: null
hold_until: null
created_at: 2026-10-24T22:53:30.527Z
updated_at: 2026-10-24T23:20:49.880Z
started_at: 2026-10-24T22:54:05.755Z
closed_at: 2026-10-24T23:20:49.880Z
close_reason: Implemented, reviewed and merged in Paraverse PR11 at main35218bb. Final head628ec8e passed44tests plus lint/format/type and header-only list checks. Independent securityB5640549894 and follow-upC5640555080 clear the fixes; full Qodo/reviewA disposition6390779837. User explicitly approved local checks in lieu of absent CI. Populated intake remains futureu26-p69k; nonpressing relative-path edge remains openpv-wmef.
resolution: null
duplicate_of: null
---
Medium https://github.com/jlevy/paraverse/pull/11#discussion_r4368798004 cli.py handoff inherits curation UV_EXCLUDE_NEWER, overriding pipeline uv.toml and potentially rewriting lock. Remove inherited override and invoke uv run --locked; verify subprocess environment.

## Notes

Fixed locally in d4d4cec4095e9e714fd691704c13b52f597557f0, following 26adb35. Pipeline subprocess removes curation UV_EXCLUDE_NEWER, preserves cache environment, selects pipeline UV_CONFIG_FILE and runs uv run --locked. Handoff regression verifies exact argv and subprocess environment. Full curation make lint-check test check PASS,44tests,0typeserrors. Root now owns native stack integration/publication and bead closure.
