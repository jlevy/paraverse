---
type: is
id: is-01m5r7gcs879rkfg85dre51k4t
title: "PR15 E1: explain unlisted meetup visibility before creation"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T00:31:28.039Z
updated_at: 2026-10-25T00:31:28.039Z
---
Independent strong-max finding on0e4cf066: Luma.swift removes the existing unlisted/link-holder access notice while retaining a lock, Private meetup and Create private event. Backend visibility=private is unlisted, accessible to link holders, according to official Luma visibility/MCP documentation; it is not invite-only. Restore the short pre-create visibility notice, with no API behavior change. New PR15 E1 finding, separate from the six Qodo findings; root may fix in bounded native integration or explicitly defer.
