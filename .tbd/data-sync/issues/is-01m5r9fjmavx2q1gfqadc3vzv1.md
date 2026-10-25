---
type: is
id: is-01m5r9fjmavx2q1gfqadc3vzv1
title: "PTC PR1: reject encoded contact URLs in sanitizer and public-data gate"
kind: bug
status: closed
priority: 1
version: 5
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:58.409Z
updated_at: 2026-10-25T01:44:08.180Z
started_at: 2026-10-25T01:06:11.024Z
closed_at: 2026-10-25T01:44:08.180Z
close_reason: "Fixed in PTC PR1 feature180815d15134ac2ebb41f95812eba3e5719143db and verified merged as64e3c0e7c5923baf74c88e408e642837da1bc54f. Final D/E clean;29tests and both CI pass;132artifacts valid. Public PR: https://github.com/jlevy/ptc2026-md/pull/1"
resolution: null
duplicate_of: null
---
Privacy C2 repro: a synthetic percent-encoded email in a contact URL passes clean_tree and privacy.findings. Decode bounded URL/contact forms for screening, sanitize/reject without echoing values, and regress safe URL/account identifiers to avoid overbroad exclusions.

## Notes

Final scoped Qodo5640927716 followup:4369228289 fixed URL-before-SSH scanning in20c6;4369228293 fixed complete trailing SSH token boundary in180815d15134ac2ebb41f95812eba3e5719143db. Synthetic standalone/prose adjacent-email RED2failed thenGREEN13security/29fullpassed17.68s; oldredact retains suffix/newcleaner removes. Complete validSSH/prose preserved; URLcredential controls detected. Lint/format/typesclean,132valid,157generated outputs identical. Both final CI jobs SUCCESS54s/49s runs40151514052+40151517538. Final D0findings/Eunchanged-source carry pinned180815d under /Volumes/spud-ext2/agent-source/ptc-review-evidence-01a16fcd; ledger/body updated bothQodoIDs. Central received final handoff and owns publication/currentQodo gate/authorizedmerge. Pending verified merge only; no new issue scope.
