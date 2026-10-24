---
type: is
id: is-01m5r2scwj3dj7y9ax2mn3m25s
title: "PR #13 Qodo r4368861840: Photo reruns can publish stale portraits"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:09:00.177Z
updated_at: 2026-10-24T23:09:00.177Z
---
Medium. Original review: https://github.com/jlevy/paraverse/pull/13#discussion_r4368861840. Location: backend/collect_speaker_photos.py:38. 5\. Photo reruns can publish stale portraits 🐞 Bug ≡ Correctness


collect() names a portrait file from the speaker slug and URL extension, then skips the download
whenever that file already exists. If the source changes its photo or URL while retaining the
extension, the next manifest associates the new photo_url with the old image bytes and hash.

Candidate for user-authorized merge-first follow-up after current stack lands; final disposition remains with coordinator.
