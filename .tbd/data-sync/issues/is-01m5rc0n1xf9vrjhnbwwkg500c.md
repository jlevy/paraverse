---
type: is
id: is-01m5rc0n1xf9vrjhnbwwkg500c
title: Package final tested native release without rebuilding
kind: task
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:50:15.089Z
updated_at: 2026-10-25T04:36:48.326Z
started_at: 2026-10-25T01:51:26.320Z
---
Package the release-tested b33f9fb native executable and frozen resources in external task scratch using build-app.sh packaging logic. Do not compile, launch, terminate processes, or change source/primary refs. Preserve demo.commonground.mac bundle ID; available development identity or ad-hoc fallback, verify codesign/plist and exact resource/binary hashes; finalize source metadata after root supplies final main SHA.

## Notes

Packaging paused before any artifact write: required external volume spud-ext2 disappeared after successful writable/df check. /Volumes contains only MacintoshHD; diskutil list external physical still reports disk4/APFScontainerdisk5. Exact release-tested binary under /Volumes/spud-ext2/.../privacy/primary-restack-r2-swift-build/arm64-apple-macosx/release/CommonGround is therefore inaccessible. Final source remains clean b33f9fb98a97fd177729edc81743ad05b5b3edef. Privacywriter reports64Swiftrelease/96backendPASS; manifestSHA02a6c263295fae72fa1e380fffed24f0cdaf887e524675297ef30b998e502c69. No compile, launch, source/ref change, package output, or signing occurred. security find-identity reports0valididentities; ad-hoc fallback authorized once packaging resumes. Await external volume availability and coordinator final mergedmainSHA for metadata. Mount not attempted because ejection may be intentional; parent informed.
