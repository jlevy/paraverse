---
type: is
id: is-01m5rp5kzyeae637sa47ktmyg9
title: "PR15 Qodo r4369675429: Make the canned security-session lookup explicit"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T04:47:43.613Z
updated_at: 2026-10-25T04:47:43.613Z
---
Review https://github.com/jlevy/paraverse/pull/15#discussion_r4369675429 (5641559490). Source-verified at final tree de096815: CompanionReply.quickSecuritySearch recognizes three exact prompts, filters bundled sessions for a fixed first-day date and bypasses the assistant with a500ms delay. This demo path ignores profile/calendar/history while similar phrasing uses the backend. Low/P3 consistency and transparency issue; no security vulnerability asserted. Later PR should remove the shortcut, make a shared backend tool, or explicitly label/gate demo behavior and derive its date from conference data. Accepted nonpressing deferral; keep OPEN for merge.
