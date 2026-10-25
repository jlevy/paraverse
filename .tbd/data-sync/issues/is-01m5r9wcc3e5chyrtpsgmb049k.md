---
type: is
id: is-01m5r9wcc3e5chyrtpsgmb049k
title: "PR14 Qodo r4368997709: report post-launch mismatch ownership correctly"
kind: bug
status: open
priority: 3
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T01:12:57.986Z
updated_at: 2026-10-25T01:12:57.986Z
---
Independent strong-max adjudication rates Low (Qodo Medium): post-launch dataset mismatch safely fails and terminates its owned child, but the retained message says server was left running and should be stopped manually. Correct the ownership-aware recovery message without taking over external processes. Original https://github.com/jlevy/paraverse/pull/14#discussion_r4368997709 from review5640663254. Nonpressing UI recovery-message follow-up.
