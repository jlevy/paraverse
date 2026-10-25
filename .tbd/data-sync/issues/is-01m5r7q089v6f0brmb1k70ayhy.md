---
type: is
id: is-01m5r7q089v6f0brmb1k70ayhy
title: "PR15 Qodo r4368988908: preserve lazy chat history layout"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5r3wth6ew3crzr3qm9tydb0
created_at: 2026-10-25T00:35:04.584Z
updated_at: 2026-10-25T00:35:04.584Z
---
Independent strong-max Review E confirms Medium at0e4cf066: WorldPlannerPanel.swift:137 eagerly constructs retained chat messages with VStack after the first question. Preserve question anchoring while making long histories lazy or bounded. No long-history benchmark was claimed. Original https://github.com/jlevy/paraverse/pull/15#discussion_r4368988908. Nonpressing UI performance follow-up after native stack.
