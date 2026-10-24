---
type: is
id: is-01m5r2schhs066n4bjm1vg7zcs
title: "PR #13 Qodo r4368861833: A speaker photo can exhaust downloader memory"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:08:59.824Z
updated_at: 2026-10-24T23:08:59.824Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861833. Location: backend/collect_speaker_photos.py:41. 4\. A speaker photo can exhaust downloader memory 🐞 Bug ⛨ Security


collect() opens each URL supplied in the saved speaker response and calls response.read()
without a download limit or URL restriction. A malformed or compromised photo URL can make a
collection run request an unintended local or internal resource, while an oversized response is
fully buffered before the content-type check.

Awaiting coordinator security/correctness triage; no deferral, rebuttal or decline decided by administrative agent.
