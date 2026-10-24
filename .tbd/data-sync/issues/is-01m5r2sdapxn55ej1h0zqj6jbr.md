---
type: is
id: is-01m5r2sdapxn55ej1h0zqj6jbr
title: "PR #13 Qodo r4368861845: A failed luma step locks the meetup draft forever"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:00.629Z
updated_at: 2026-10-24T23:09:00.629Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861845. Location: backend/luma_service.py:106. 6\. A failed luma step locks the meetup draft forever 🐞 Bug ☼ Reliability


create_event saves status=&#x27;creating&#x27; before calling tool(), marks the draft needs_review on
any exception, and returns early when the status is creating or needs_review, so the only way
out is to edit the draft file by hand. invite_selected sets invitationStatus the same way. An
expired or missing Luma token (access_token() raises inside the try), a network error, or a
backend crash between the two saves all lock the draft, even when Luma never received a request.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
