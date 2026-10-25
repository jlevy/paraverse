---
type: is
id: is-01m5qvq83d2m7nebnh4br3zc6w
title: "PR #9 qodo-5640006360 #1: cloning does not give loadable data until the dataset pin moves (https://github.com/jlevy/paraverse/pull/9#discussion_r4368502073)"
kind: bug
status: closed
priority: 2
version: 6
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvq0n2h1swggks54s011d7
hold: null
hold_until: null
created_at: 2026-10-24T21:05:29.708Z
updated_at: 2026-10-25T04:46:17.294Z
started_at: 2026-10-24T21:05:45.497Z
closed_at: 2026-10-25T04:46:17.294Z
close_reason: Completed in merged Paraverse PR14, merge 01cae9f21e5f3d0f5c95b52027bfa223959ab457. Final safe merged dataset pins a823679/64e3c0e match manifest; 4977+132 artifacts valid, deterministic native assets, owned explicit attendance proof and expected browser identity gates verified. Independent F/G/H carry exact source; final upper-stack 96 backend/64 release Swift tests pass. Both safe datasets run in browser8879 (5536 entities/25564 relationships); all nonpressing findings remain separate open beads.
resolution: null
duplicate_of: null
---
PR: jlevy/paraverse#9 (layer vendor/universe2026-md).
Review: https://github.com/jlevy/paraverse/pull/9#pullrequestreview-5640006360
Inline comment: https://github.com/jlevy/paraverse/pull/9#discussion_r4368502073
Severity: Medium (Qodo: Remediation recommended), Correctness.
References: README.md:19-27 (vendor/ entry and Getting the Data), AGENTS.md:108-111 (Build & Test), vendor/universe2026-md gitlink at a803714e170bfea35720cdb1128e97cf4d6ef5da.

Finding: the README says initializing the submodule gets the dataset, but the pinned commit (the dataset's initial commit on main) has no kb/. After following the steps, find_kb_root() finds no graph export, make load fails and make datasets omits the default dataset.
Qodo's suggested fix: state in README.md and AGENTS.md that the current pin lacks kb/ until the pointer moves.

Resolution: move the vendor/universe2026-md pin to the dataset commit on main that holds kb/, in its own small PR on top of this stack. That waits on the dataset's records landing on jlevy/universe2026-md main (tracked there as u26-uff0).

## Notes

Disposition: deferred (review qodo-5640006360, #1), at PR #9 head f3bd9fb77c1d7d0fa5232b2204ed836e48bce32f.

Confirmed the finding at the pinned head:
- gh api repos/jlevy/universe2026-md/commits/main: a803714 "Initial commit", tree holds only .gitignore and LICENSE.
- git submodule update --init: checks out a803714 with no kb/.
- db/ make datasets: exit 0, prints "The default dataset is not at vendor/universe2026-md/kb; run git submodule update --init or pass --kb/--dataset." and lists nothing.
- db/ make load: exit 2, "no knowledge base at vendor/universe2026-md/kb (no _graph/nodes.jsonl)".
- db/ make test: 35 passed, 44 skipped; every skip is "vendor/universe2026-md/kb is not checked out".

Why deferred: the pin is set on purpose to the dataset's main, which has only its initial commit until the records land through the dataset's own PR stack (jlevy/universe2026-md #1 to #7 are open; the KB is u26-uff0). The PR description records this interim state. The fix for the finding is moving the pin, in its own small PR once kb/ is on the dataset's main; it removes the problem rather than describing it.
Qodo's suggested README/AGENTS.md note is not added: it would describe a transient state in durable docs, and the pin-update PR would have to remove it again. The tooling already reports the missing KB and the end-to-end tests skip.

Waits on: jlevy/universe2026-md main gaining kb/ (u26-uff0), then the pin-update PR. Done when git submodule update --init followed by make load succeeds and make test runs the end-to-end tests.
