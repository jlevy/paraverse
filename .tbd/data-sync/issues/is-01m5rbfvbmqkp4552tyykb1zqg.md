---
type: is
id: is-01m5rbfvbmqkp4552tyykb1zqg
title: "PR15 Qodo r4369243676: Cancel the external-events request when its plan is reset"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T01:41:04.497Z
updated_at: 2026-10-25T01:41:04.497Z
---
Review: https://github.com/jlevy/paraverse/pull/15#discussion_r4369243676 (Qodo5640945499). Independently confirmed at918bf3f/base49bee: Plan.swift145-162 uses an unstructured external-events Task; reset cancels the parent while awaiting eventsTask.value, so defer cancellation runs only after the external request finishes. Generation guards164/167/186 prevent stale publication. Impact is wasted and overlapping backend/LLM work, not the older pv-nmco stale-task busy-state race. Follow up with structured cancellation or a cancellation handler and a suspended-request cancellation regression. Accepted nonpressing Medium/P2 deferral for a later PR; keep OPEN during this merge.
