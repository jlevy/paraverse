---
type: is
id: is-01m5qy0rrje3mawm03yhtb70a8
title: Align shared conference contracts with PTC judge and event-sponsorship additions
kind: task
status: open
priority: 3
version: 1
labels: []
dependencies: []
created_at: 2026-10-24T21:45:38.833Z
updated_at: 2026-10-24T21:45:38.833Z
---
The PTC dataset documents additive Participation.role=judge and Organization.sponsored_events fields under shared conference contract IDs. Reconcile these additions with the Universe/shared contract source in its own reviewed change, respecting the other active dataset work. Current PTC records validate against their checked-in schemas and load into Paraverse; this follow-up is schema coordination, not a graph-load blocker. See jlevy/ptc2026-md PR1 docs/contracts.md and Paraverse PR10.
