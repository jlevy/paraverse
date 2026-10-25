---
type: is
id: is-01m5rc0n1xf9vrjhnbwwkg500c
title: Package final tested native release without rebuilding
kind: task
status: in_progress
priority: 1
version: 2
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-25T01:50:15.089Z
updated_at: 2026-10-25T01:51:26.349Z
started_at: 2026-10-25T01:51:26.320Z
---
Package the release-tested b33f9fb native executable and frozen resources in external task scratch using build-app.sh packaging logic. Do not compile, launch, terminate processes, or change source/primary refs. Preserve demo.commonground.mac bundle ID; available development identity or ad-hoc fallback, verify codesign/plist and exact resource/binary hashes; finalize source metadata after root supplies final main SHA.
