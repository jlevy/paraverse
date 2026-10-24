---
type: is
id: is-01m5qxs6scx3q34w9pate4y27b
title: Include pinned repositories in person_repositories query
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-24T21:41:31.051Z
updated_at: 2026-10-24T21:41:31.051Z
---
At6fc8c39 queries.py:212 promises maintained or pinned repositories but line214 matches only MAINTAINS; original export contains125 PINS edges omitted. m.via returned at216 absent from current export attrs. Include PINS and meaningful relationship explanation or deliberately narrow API contract/docs. Parent pv-67zv.
