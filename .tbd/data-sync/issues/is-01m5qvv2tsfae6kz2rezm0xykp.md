---
type: is
id: is-01m5qvv2tsfae6kz2rezm0xykp
title: "PR #1 qodo-5639982758 S1: provision the GitHub CLI outside session hooks (https://github.com/jlevy/paraverse/pull/1#issuecomment-6389403870)"
kind: task
status: closed
priority: 3
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvrh49dgg0m7by1349fe3w
hold: null
hold_until: null
created_at: 2026-10-24T21:07:35.383Z
updated_at: 2026-10-24T21:07:36.872Z
started_at: 2026-10-24T21:07:36.328Z
closed_at: 2026-10-24T21:07:36.871Z
close_reason: "Declined: the project controls no agent environment (no devcontainer, Dockerfile or CI workflow on any stack branch); agents start in unprepared environments, where Qodo's own assessment says to keep the checked installer; an environment definition is out of scope for the tbd setup PR."
resolution: canceled
duplicate_of: null
---
Qodo suggestion from the PR summary's High-Level Assessment, PR #1: https://github.com/jlevy/paraverse/pull/1#issuecomment-6389403870. The summary has no IDs, so this suggestion is numbered S1 here.

Suggestion: for environments the project controls, provision the pinned GitHub CLI outside the session hooks; keep the checked installer (`.claude/scripts/ensure-gh-cli.sh`, `.codex/ensure-gh-cli.sh`) where agents start in unprepared environments. The same assessment recommends keeping the generated tbd surfaces.

Disposition: declined. The project controls no agent environment: no branch in the stack (main through kb/pipeline) has a devcontainer, Dockerfile, CI workflow or other environment definition. Agents start on contributors' own machines and in hosted sessions, which is the unprepared case where the summary itself says to keep the installer. Adding an environment definition is outside the scope of a PR that sets up tbd.
