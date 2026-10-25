---
type: is
id: is-01m5r9fjmavx2q1gfqadc3vzv1
title: "PTC PR1: reject encoded contact URLs in sanitizer and public-data gate"
kind: bug
status: in_progress
priority: 1
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5r936jh6h5sbf0a7vanfmvm
hold: null
hold_until: null
created_at: 2026-10-25T01:05:58.409Z
updated_at: 2026-10-25T01:40:31.144Z
started_at: 2026-10-25T01:06:11.024Z
---
Privacy C2 repro: a synthetic percent-encoded email in a contact URL passes clean_tree and privacy.findings. Decode bounded URL/contact forms for screening, sanitize/reject without echoing values, and regress safe URL/account identifiers to avoid overbroad exclusions.

## Notes

Final scoped Qodo5640927716 followup:4369228289 fixed URL-before-SSH scanning in20c6;4369228293 fixed complete trailing SSH token boundary in180815d15134ac2ebb41f95812eba3e5719143db. Synthetic standalone/prose adjacent-email regressions RED2failed thenGREEN13security/29fullpassed17.68s; oldredact retains suffix/newcleaner removes. Complete validSSH/prose preserved, URLcredential controls remain detected. Lint/format/typesclean,132valid,157generated outputs hashidentical. Exact-head D/E repin and CI pending; central merge hold respected.
