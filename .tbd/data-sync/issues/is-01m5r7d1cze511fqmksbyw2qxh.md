---
type: is
id: is-01m5r7d1cze511fqmksbyw2qxh
title: "PR13 Qodo r4369000069: align nearby conference eligibility window"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T00:29:38.066Z
updated_at: 2026-10-25T00:29:38.066Z
---
Verified Medium at13748 by strong-max reviewer: conference_catalog.py:42/52 accepts365days while conference_service.py:88/94 and native Conferences.swift:146 promise180days/sixmonths. No actual current out-of-window match was asserted. Align eligibility and displayed contract with a boundary regression in the conference discovery follow-up. Original https://github.com/jlevy/paraverse/pull/13#discussion_r4369000069.
