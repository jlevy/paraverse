---
type: is
id: is-01m5r7gcs879rkfg85dre51k4t
title: "PR15 E1: explain unlisted meetup visibility before creation"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
hold: null
hold_until: null
created_at: 2026-10-25T00:31:28.039Z
updated_at: 2026-10-25T01:06:52.405Z
started_at: 2026-10-25T01:02:35.616Z
---
Independent strong-max finding on0e4cf066: Luma.swift removes the existing unlisted/link-holder access notice while retaining a lock, Private meetup and Create private event. Backend visibility=private is unlisted, accessible to link holders, according to official Luma visibility/MCP documentation; it is not invite-only. Restore the short pre-create visibility notice, with no API behavior change. New PR15 E1 finding, separate from the six Qodo findings; root may fix in bounded native integration or explicitly defer.

## Notes

Fixed462539e71c29687ade3fcf455e64121a36a7d828: restore exact two-line Unlisted · Anyone with the link may view it notice in LumaEventCard before creation. Backend/API unchanged. Official help.luma.com/p/setting-your-event-visibility and /p/mcp checked read-only: private events unlisted/basic page accessible via shared link. ReviewE5640774432. ReleasecompilePASS with9focusedplanningtests;diffcheckPASS. No liveevent/invite/app termination, no push. Root owns final15integration/disposition/closure.
