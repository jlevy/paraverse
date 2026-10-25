---
type: is
id: is-01m5rb4r2peg72t66xk0ptbzfd
title: "PR13 Qodo r4369238729: pin conference fetches to validated public DNS"
kind: bug
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:35:00.692Z
updated_at: 2026-10-25T01:36:14.889Z
started_at: 2026-10-25T01:36:14.874Z
---
High review5640939881 https://github.com/jlevy/paraverse/pull/13#discussion_r4369238729. Replace check-then-reresolve urllib conference fetch path with DNS-pinned public HTTPS transport preserving original TLS hostname and Host. Validate/pin redirects, reject private destinations, drop credential forwarding and preserve size/type limits. Isolated8cf source; no primary refs/push.
