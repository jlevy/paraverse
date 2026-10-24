---
type: is
id: is-01m5qwr1fm58a58924w1kmxfk5
title: Port closed enforced v2 contracts to verified Universe KB
kind: task
status: in_progress
priority: 1
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qwpf7egtr4snchk904vy3s
hold: null
hold_until: null
created_at: 2026-10-24T21:23:24.275Z
updated_at: 2026-10-24T23:31:30.953Z
started_at: 2026-10-24T21:23:41.121Z
---
Apply the saved adapted contracts-v2 port on kb/contracts-v2. Rebase onto final privacy-verified kb/data; regenerate 18 schemas and KB from target pipeline; prove payload/search/graph equality; run make check and softschema repair; publish after dependency confirmation.

## Notes

Oldc6 review/publication claim superseded. Tested own-v2 migration committed LOCALLY7663ac66ecd96920193c71d043c797ca9fdee994 on corrected data71193ec; source external /Volumes/spud-ext2/agent-source/universe2026-contracts-v2-final-01a16fc8, branchcodex/contracts-v2-final, clean. Fresh18schemas;5001inventorysame;4977payloads,Markdownbodies,frontmatter-exceptmetadata,exports/otherbytes0diff. makecheck4977valid/0invalid,210tests81.30s,Ruffclean,types0errors0warnings. Fullstockrepair4977valid0repairs182s. All7olderunsafe/intermediateancestors absent. Preserved evidence $S/review/final-v2-evidence.json +final-v2-check.log,final-v2-repair.json,final-v2-delta.json. BaseKB git tree1b3e5bc3411a0060e18778f9c34097401f4ea575; v2KB treea6df4e25631787f23ac70f6e81ddbd281e5d5d10. PUBLICATIONHELD pending coordinator new source/data parent for newly reported source Highs. Replay ONLY own7663ac6 migration there; carry4977repair proof only ifexactKBtree unchanged. No push performed.
