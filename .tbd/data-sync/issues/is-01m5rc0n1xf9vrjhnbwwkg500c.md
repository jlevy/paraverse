---
type: is
id: is-01m5rc0n1xf9vrjhnbwwkg500c
title: Package final tested native release without rebuilding
kind: task
status: closed
priority: 1
version: 6
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:50:15.089Z
updated_at: 2026-10-25T04:49:52.712Z
started_at: 2026-10-25T01:51:26.320Z
closed_at: 2026-10-25T04:49:52.711Z
close_reason: Final external native bundle packaged, merged/tested trees identical, provenance finalized, signature and297resources verified; no rebuild or launch.
resolution: null
duplicate_of: null
---
Package the release-tested b33f9fb native executable and frozen resources in external task scratch using build-app.sh packaging logic. Do not compile, launch, terminate processes, or change source/primary refs. Preserve demo.commonground.mac bundle ID; available development identity or ad-hoc fallback, verify codesign/plist and exact resource/binary hashes; finalize source metadata after root supplies final main SHA.

## Notes

COMPLETE: packaged exact release-tested b33f9fb executable without rebuilding; final main bb9a567679da7cb95724a71be1c10eac1ade11e8 has exact same tree de096815310dec75fd19f83b230ff24f6954e308. External app native-review/final-package-b33f9fb/Paraverse Final.app is44MB; bundleIDdemo.commonground.mac, validplist, arm64/system-onlylibs. Metadata records actualmain sourceRevision, testedSourceRevisionb33 separately, cleanfalse-dirtystate and manifestSHA02a6c263295fae72fa1e380fffed24f0cdaf887e524675297ef30b998e502c69.297resourcefiles/295sourceassets byte-identical/12minimizedpublicattendees/0symlinks. No validdevelopmentidentity available; authorizedad-hoc signing completed. codesign --verify --deep --strict --verbose=2 PASS: valid on disk/satisfies designated requirement. Source/binary precopySHA7b78840db7767548c4570a48d80d633d01647a5f0a9de637ac0e4f7d464b4698 matched; signedSHA41aa2acb97cc65df800f8eee6b4660e719ed0bd5ea12a3a7dd1788950e22faaf. Audit+verification+artifact-onlyscripts under /Volumes/spud-ext2/agent-evidence/paraverse-final-native-package-01a16fc8/. No compile/launch/process/source/ref mutation; finalprimarymain clean.
