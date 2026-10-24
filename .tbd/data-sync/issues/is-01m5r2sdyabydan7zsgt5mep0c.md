---
type: is
id: is-01m5r2sdyabydan7zsgt5mep0c
title: 'PR #13 Qodo r4368861863: Any chat mention of "invite" drafts a meetup'
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:01.257Z
updated_at: 2026-10-24T23:09:01.257Z
---
Low. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861863. Location: backend/chat_service.py:33. 10\. Any chat mention of "invite" drafts a meetup 🐞 Bug ≡ Correctness


answer() sends every prompt matching \binvite\b to draft_event, which makes a paid OpenAI
call, writes a draft file and returns a coffee meetup card instead of an answer. A question such as
&#x27;Which sessions are invite-only?&#x27; (the hyphen counts as a word boundary) or &#x27;Who should I invite?&#x27;
sent before any draft exists gets a meetup proposal instead of an answer.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
