---
type: is
id: is-01m5r7d2c5f1f5419mxf2hza0t
title: "PR13 Qodo r4369000076: align profile URL validation"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T00:29:39.076Z
updated_at: 2026-10-25T00:29:39.076Z
---
Verified Medium at13748: native Onboarding.swift:20-25/40-48 accepts query/fragment/port/extra LinkedIn path segments, while backend profile_url.py:26 rejects the unchanged submitted URL. Align accepted/normalized URL contract and reject unsupported variants before import. Follow-up after native stack. Original https://github.com/jlevy/paraverse/pull/13#discussion_r4369000076.
