---
type: is
id: is-01m5r3wth6ew3crzr3qm9tydb0
title: Review PR15 cache and app-entry performance layer
kind: task
status: in_progress
priority: 1
version: 12
delegate: codex@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r2ex2vsny69m3dnps770t0
child_order_hints:
  - is-01m5r7gcs879rkfg85dre51k4t
  - is-01m5r7pzw9hf5t48vgq06683x3
  - is-01m5r7q089v6f0brmb1k70ayhy
  - is-01m5r7q0jfj07d2asjpraampcx
  - is-01m5rbfvbmqkp4552tyykb1zqg
  - is-01m5rbfvqmpejy4jc67k7t67w7
  - is-01m5rbfw432axqsq3pyd3sd7wr
hold: null
hold_until: null
created_at: 2026-10-24T23:28:21.029Z
updated_at: 2026-10-25T01:41:05.282Z
started_at: 2026-10-24T23:28:28.330Z
---
Independent strong-max senior and dedicated performance/security/correctness reviews of PR15, pinned to1cd2c057 on base021a745. Isolated read-only worktree; publish formal reviews, track findings with owner, no code edits or merges.

## Notes

Original A5640602183 B5640610923 C5640617959 D5640623486 at1cd2/base021a verified. BoundedE5640774432 exact0e4/base9037 coveredall20filesincl12Tina additions,25focusednativePASS; cachedpeopleREDtwoassertionsrootfixed70529d5. LatestboundedF5640908331 exact4af553bbf0729417e72c851c7a69f437ef30f719/basef05e7e00c58db649643339943d5302ae56e5da80 publishedandparentverified. Independent same REDreproducer now2testsPASS2.322s/build40.12; all9ownpatches range-diff equal. Docs17da removes personalpath, fixesportablelauncherandDiscover-firstprose;462539restoresLumaunlistednoticeE1/pv-hndd. SixQodo extras:8909/8910/8911 fixedpv-gq27;8905renamecopiesdeferredpv-mdct;8908eagerchatdeferredpv-jxra;4369017647 cachedpeoplefixedpv-k49x. Crossrestartcachepv-vdku remainsopen; do notquoteobsoletebenchmarks. No ownDBchanges, inheritedruntimecleanup retained. Finalrootclean13reconstruction8cf/basef041 andsafePTCpin change require boundedparentcarry review beforefinal15merge; F is not clearanceofunseenrestack. Durablepr15-dispositions-draft updatedFandactualfixes butFINAL_HEAD/finalparentcarrymustfill. Rootowns allrefs/source/merges; no launcher/liveapp terminated. PTCprivacyHOLDseparateuntilownerfinaldatasetreview. Trackingupdatedforhandoff; noCIpassclaim.
