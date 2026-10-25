---
type: is
id: is-01m5rbhhk20whxspradczmwznm
title: "PR14 Qodo r4369245962: Honor standalone GitHub references in attendee evidence export"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T01:42:00.025Z
updated_at: 2026-10-25T01:42:00.025Z
---
Review: https://github.com/jlevy/paraverse/pull/14#discussion_r4369245962 (Qodo5640948314). Bounded independent review at49bee6f5/base8cf5 confirms export_native_data.py133 _attendance_proof enumerates accounts only while _links includes accounts and standalone github references. A supported person.github record can therefore be omitted from attendee proof. No current bundled attendance regression established: the current Universe self-report uses accounts. Distinct from mixed-role proof preservation and B1 public-admission guard. Extend supported-account normalization and add a GitHub-only self-report fixture without weakening admission evidence. Accepted nonpressing Medium/P2 deferral for a later PR; keep OPEN during this merge.
