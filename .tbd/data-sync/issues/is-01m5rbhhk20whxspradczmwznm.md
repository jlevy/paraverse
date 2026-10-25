---
type: is
id: is-01m5rbhhk20whxspradczmwznm
title: "PR14 Qodo r4369245962: Honor standalone GitHub references in attendee evidence export"
kind: bug
status: open
priority: 2
version: 3
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
hold: null
hold_until: null
created_at: 2026-10-25T01:42:00.025Z
updated_at: 2026-10-25T01:42:26.242Z
started_at: 2026-10-25T01:42:17.219Z
---
Review: https://github.com/jlevy/paraverse/pull/14#discussion_r4369245962 (Qodo5640948314). Independently confirmed at49bee6f5/base8cf5 in backend/export_kb_native.py133: _attendance_proof enumerates accounts only while _links includes accounts and standalone github references. Schema-valid synthetic Person/v2 at pinnedcd41: accounts=[gh:example] exports1person/1attendee; changing only to github=gh:example still yields githubURL but0proof and rejects for no confirmed/self-reported participants. Aggregate of577pinnedUniversepeople:1currentattendee using accounts,0currentGitHub-onlyattendees; no present bundled regression. Distinct from pv-t0k5 mixed-role proof and B1 public-admission guard. Next PR should share account-reference normalization while preserving account-ownership and explicit-public-post admission guards, with a GitHub-only regression. Accepted nonpressing Medium/P2 deferral; keep OPEN during this merge.
