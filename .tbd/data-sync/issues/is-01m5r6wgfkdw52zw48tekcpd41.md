---
type: is
id: is-01m5r6wgfkdw52zw48tekcpd41
title: "PR15 launch documentation: portable launcher and current entry page"
kind: bug
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T00:20:36.466Z
updated_at: 2026-10-25T00:31:42.925Z
started_at: 2026-10-25T00:20:50.916Z
---
Qodo High r4368988909 hardcodes a contributor home path in AGENTS; associated Medium launch README points to obsolete bundle name. Replace with bash native/run-app.sh from repository root, document Paraverse Final.app and current Discover returning-user default. OnlyAGENTS/README/nativeREADME; preserve effective grant block; syntax and fully mocked portable launch harness, no real app termination. Parent owns publication.

## Notes

Fixed17da864e81f2c797718d5c13dd7970da1a4ea593 based Tina0e4cf06690be7e8af5baf778c36dadf5e581d513. Qodo review5640653977 High r4368988909 https://github.com/jlevy/paraverse/pull/15#discussion_r4368988909; Medium r4368988910 exact Final bundle/launcher docs; Medium r4368988911 actual returningDiscover entry. ExactlyAGENTS/README/nativeREADME. bash-n run-app/build-app PASS; portable command/exactbundle/defaultpage/footer consistency assertionsPASS; grantblock BYTEIDENTICAL;diffcheckPASS;sourceclean. Formatter applied with managedgrantprefixpreserved. No source/scripts edits, no apps terminated or Swift rerun, no push. Root owns integration/dispositions/closure.
