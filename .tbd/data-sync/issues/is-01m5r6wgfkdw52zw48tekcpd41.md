---
type: is
id: is-01m5r6wgfkdw52zw48tekcpd41
title: "PR15 launch documentation: portable launcher and current entry page"
kind: bug
status: closed
priority: 1
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T00:20:36.466Z
updated_at: 2026-10-25T04:49:59.037Z
started_at: 2026-10-25T00:20:50.916Z
closed_at: 2026-10-25T04:49:59.036Z
close_reason: Fixed in merged PR15, main bb9a567679da7cb95724a71be1c10eac1ade11e8. Portable launch docs, current-plan people refresh, unlisted visibility notice and visible navigation preserved; F/G/H verify exact final tree de096815. 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/15#issuecomment-6393593264; nonpressing findings remain open in separate beads.
resolution: null
duplicate_of: null
---
Qodo High r4368988909 hardcodes a contributor home path in AGENTS; associated Medium launch README points to obsolete bundle name. Replace with bash native/run-app.sh from repository root, document Paraverse Final.app and current Discover returning-user default. OnlyAGENTS/README/nativeREADME; preserve effective grant block; syntax and fully mocked portable launch harness, no real app termination. Parent owns publication.

## Notes

Fixed17da864e81f2c797718d5c13dd7970da1a4ea593 based Tina0e4cf06690be7e8af5baf778c36dadf5e581d513. Qodo review5640653977 High r4368988909 https://github.com/jlevy/paraverse/pull/15#discussion_r4368988909; Medium r4368988910 exact Final bundle/launcher docs; Medium r4368988911 actual returningDiscover entry. ExactlyAGENTS/README/nativeREADME. bash-n run-app/build-app PASS; portable command/exactbundle/defaultpage/footer consistency assertionsPASS; grantblock BYTEIDENTICAL;diffcheckPASS;sourceclean. Formatter applied with managedgrantprefixpreserved. No source/scripts edits, no apps terminated or Swift rerun, no push. Root owns integration/dispositions/closure.
