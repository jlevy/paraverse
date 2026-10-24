---
type: is
id: is-01m5r2keb2kbhynf0230zxp8qx
title: "PR #13 A5: preserve reviewed profile fields during partial editor imports"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2962gx3jdwh8zwdp57h42
created_at: 2026-10-24T23:05:45.057Z
updated_at: 2026-10-24T23:05:45.057Z
---
PR #13 senior review A5 at head 7f9d33bbb4503ec92e7ffa5089dccbce81f72fb3. Original review: https://github.com/jlevy/paraverse/pull/13#pullrequestreview-5640490422. Medium. native/Sources/CommonGround/YourProfile.swift:93-96 assigns empty imported background and nil title/avatar over reviewed draft. Use ProfileEnrichment.refresh merge helper, as onboarding does; test interests-only response preserves biography, title and avatar. Save remains explicit. Deferred under user merge-first authorization; waits on current native stack landing before profile editor merge follow-up.
