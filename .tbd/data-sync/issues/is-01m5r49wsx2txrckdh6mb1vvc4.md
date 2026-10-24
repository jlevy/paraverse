---
type: is
id: is-01m5r49wsx2txrckdh6mb1vvc4
title: "PR15 Qodo r4368935594: restore world navigation entry points"
kind: bug
status: in_progress
priority: 2
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:35:29.340Z
updated_at: 2026-10-24T23:39:29.592Z
started_at: 2026-10-24T23:35:35.256Z
---
Review r4368935594 UUID8fb23b0e: sidebar routes removed but UniverseWorld openDiscovery/openSchedule/openPeople never invoked, making discovery/schedule/directory unreachable. Add bounded visible callback wiring and regression on isolated1cd2c05; preserve latest pixel style and pasted-name search. No unrelated UI changes.

## Notes

Fixed8ddb684ef3c417fc3b62918f7243332bf16732e3 based1cd2c05; WorldNavigationMenu exposed through UniverseWorld primaryControls dispatches existing discovery/schedule/people callbacks. Preserves local attendee overlay and latest pixel/search code. Focused WorldNavigationTests1/1PASS0.133s; actual NSHostingView44px minimum hit-area regression caught16px native Menu sizing and passes after outer styling. Sourceclean/diffcheck; parentprivacy integrator receives commit and owns fulltopgate/push/closure.
