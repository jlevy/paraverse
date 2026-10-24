---
type: is
id: is-01m5r35mqshepw6d63c1brp3e6
title: "Follow-up: resolve explicit relative curation selections against --root"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
parent_id: is-01m5qwqq56sft2fbb53bsgp2dd
created_at: 2026-10-24T23:15:41.431Z
updated_at: 2026-10-24T23:15:41.431Z
---
Deferred from Paraverse PR11 Qodo comment6390426541 at head628ec8e, finding1. reports() interprets explicitly selected relative file paths from cwd even when --root selects another curation directory. Default check and build handoff remain usable. In a follow-up PR, resolve relative selections against root while retaining absolute paths, and test a different cwd. User explicitly permits nonpressing items to be deferred to follow-up PRs.
