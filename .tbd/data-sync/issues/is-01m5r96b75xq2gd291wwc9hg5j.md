---
type: is
id: is-01m5r96b75xq2gd291wwc9hg5j
title: Fix Knowledge Base slash search results rendering
kind: bug
status: closed
priority: 2
version: 4
delegate: codex@tinas-macbook-pro.local
labels: []
dependencies: []
hold: null
hold_until: null
created_at: 2026-10-25T01:00:55.908Z
updated_at: 2026-10-25T01:04:37.305Z
started_at: 2026-10-25T01:01:17.696Z
closed_at: 2026-10-25T01:04:37.304Z
close_reason: null
resolution: null
duplicate_of: null
---
User reports slash search does not render Knowledge Base results; diagnose, fix, verify, and restart Paraverse Final.

## Notes

Fixed WebKit auto-height dialog flex layout: search results used flex: 1 (zero basis) and collapsed to zero height in the native WKWebView despite matching rows being present. Changed results to flex: 1 1 auto and prevented search/header/footer rows from shrinking. Verified original failure visually and fixed results in restarted Paraverse Final with Satyam (5 hits), Copilot (40 hits), keyboard wrap scrolling to last match, and Down+Enter opening a matching record. Focused browser regression suite: 16 passed. git diff --check passed. Restarted via canonical native/run-app.sh. Existing native asset edits preserved.
