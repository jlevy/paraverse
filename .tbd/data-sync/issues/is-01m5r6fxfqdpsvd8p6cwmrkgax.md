---
type: is
id: is-01m5r6fxfqdpsvd8p6cwmrkgax
title: "PR14 Qodo r4368916765: show event context for PTC host"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
created_at: 2026-10-25T00:13:43.786Z
updated_at: 2026-10-25T00:13:43.786Z
---
Confirmed Medium at9037dc0 by independent strong-max review. Current Kunal PTC host is presented without event context in directorySummary and planner branches, which label judges but not the host. Preserve source event identity in role labels instead of implying a Universe host. Original finding https://github.com/jlevy/paraverse/pull/14#discussion_r4368916765. Nonpressing display follow-up after native stack lands; no attendance or role inference.
