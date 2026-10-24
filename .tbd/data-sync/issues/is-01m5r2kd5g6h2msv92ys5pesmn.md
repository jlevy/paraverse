---
type: is
id: is-01m5r2kd5g6h2msv92ys5pesmn
title: "PR #13 A1: redact obfuscated contact addresses in cached QCon sources"
kind: bug
status: closed
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
hold: null
hold_until: null
created_at: 2026-10-24T23:05:43.855Z
updated_at: 2026-10-24T23:07:41.971Z
started_at: 2026-10-24T23:05:58.692Z
closed_at: 2026-10-24T23:07:41.970Z
close_reason: Fixed and pushed contact redaction in fc165b2; pre-fix scan failed, post-fix all132 work/data JSON files parse and contain no matching obfuscated contacts; PR13 review A1 disposition posted.
resolution: null
duplicate_of: null
---
PR #13 senior review A1 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. High. work/data/conference-catalog/sources/qcon-sf-2026.json:7 and qcon-agenda-2026.json:7 retain organizational mailboxes spelled with [at] and [dot]. Redact contacts while preserving dates, venue and agenda evidence; include obfuscated forms in data scan. MUST FIX BEFORE MERGE; not deferred. Coordinator owns implementation. Acceptance: cached pages contain no contact addresses and targeted obfuscated-contact scan passes.
