---
type: is
id: is-01m5r7q0jfj07d2asjpraampcx
title: "PR15 Qodo r4369017647: bind cached people to generating inputs"
kind: bug
status: closed
priority: 1
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
hold: null
hold_until: null
created_at: 2026-10-25T00:35:04.911Z
updated_at: 2026-10-25T04:49:59.051Z
started_at: 2026-10-25T01:02:35.350Z
closed_at: 2026-10-25T04:49:59.051Z
close_reason: Fixed in merged PR15, main bb9a567679da7cb95724a71be1c10eac1ade11e8. Portable launch docs, current-plan people refresh, unlisted visibility notice and visible navigation preserved; F/G/H verify exact final tree de096815. 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/15#issuecomment-6393593264; nonpressing findings remain open in separate beads.
resolution: null
duplicate_of: null
---
Independent strong-max Review E reproduces Medium at0e4cf066: complete plan A then sessions-only B then complete B retains A people results, with one people request instead of two. Two deterministic reviewer assertions fail in pr15_cached_people_probe.swift. Track the successful people-result input fingerprint or disable reuse until identity exists, without removing unrelated parallel planning. Original https://github.com/jlevy/paraverse/pull/15#discussion_r4369017647, Qodo b771a759-2850-4a45-883e-2d8b674f96c6. Root should address before final merge.

## Notes

Fixed70529d5ae7b6c7033f7786f35d365704fe5e6c0d atop docs17da864/Tina0e4. Supplied completeA→sessions-onlyB→completeB regression RED twoassertions (one request/staleA), nowGREEN and kept as CachedPeopleTests.swift. Until cached results carry generating inputs, complete plans always refresh people; parallel externalTask,750ms reveal,generation guard,retries and saved fallback unchanged. Focusedrelease9testsPASS7.390s,compile36.77s,diffcheckPASS. Syntheticexample-domainfixtures; no credentials,realpeople,liveproviderorcalendarwrites. Root received cleancommit; no push; root owns integration/disposition/closure.
