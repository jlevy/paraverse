---
type: is
id: is-01m5r2sej20pa3j1gzy3z67b5k
title: "PR #13 Qodo r4368861876: Luma module comments misdescribe what it sends"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:01.889Z
updated_at: 2026-10-24T23:09:01.889Z
---
Low. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861876. Location: backend/luma_service.py:1. 11\. Luma module comments misdescribe what it sends 🐞 Bug ⚙ Maintainability


The module docstrings say &#x27;Demo recipients are never sent&#x27; (luma_service.py) and &#x27;no browser
automation or invitation calls&#x27; (luma_mcp.py). Yet invite_selected sends real invitations to the
emails in work/demo-invite-contacts.json through the allow-listed invite_guests tool, and
browser_command (a Node browser runner over a pipe) is never called. A later maintainer who trusts
these comments can mistake the safety guarantees of a path that emails real addresses, and has to
keep dead browser-bridge code that also never kills a runner that times out.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
