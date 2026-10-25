---
type: is
id: is-01m5r49wsx2txrckdh6mb1vvc4
title: "PR15 Qodo r4368935594: restore world navigation entry points"
kind: bug
status: closed
priority: 2
version: 4
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r23chnhgvbw2529w9d655c
hold: null
hold_until: null
created_at: 2026-10-24T23:35:29.340Z
updated_at: 2026-10-25T04:49:59.078Z
started_at: 2026-10-24T23:35:35.256Z
closed_at: 2026-10-25T04:49:59.078Z
close_reason: Fixed in merged PR15, main bb9a567679da7cb95724a71be1c10eac1ade11e8. Portable launch docs, current-plan people refresh, unlisted visibility notice and visible navigation preserved; F/G/H verify exact final tree de096815. 96 backend and 64 release Swift tests pass. Dispositions https://github.com/jlevy/paraverse/pull/15#issuecomment-6393593264; nonpressing findings remain open in separate beads.
resolution: null
duplicate_of: null
---
Review r4368935594 UUID8fb23b0e: sidebar routes removed but UniverseWorld openDiscovery/openSchedule/openPeople never invoked, making discovery/schedule/directory unreachable. Add bounded visible callback wiring and regression on isolated1cd2c05; preserve latest pixel style and pasted-name search. No unrelated UI changes.

## Notes

Fixed8ddb684ef3c417fc3b62918f7243332bf16732e3 based1cd2c05; WorldNavigationMenu exposed through UniverseWorld primaryControls dispatches existing discovery/schedule/people callbacks. Preserves local attendee overlay and latest pixel/search code. Focused WorldNavigationTests1/1PASS0.133s; actual NSHostingView44px minimum hit-area regression caught16px native Menu sizing and passes after outer styling. Sourceclean/diffcheck; parentprivacy integrator receives commit and owns fulltopgate/push/closure.
