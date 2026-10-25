---
type: is
id: is-01m5r9fksrnfedxp5fzg1b6bqa
title: "PTC followup: validate stored bio hashes against curated inputs"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:05:59.607Z
updated_at: 2026-10-25T01:05:59.607Z
---
Deferred PR1 correctness finding: standalone validate can return ok after a curated input changes while stored bio input_sha256 no longer matches. Compare hashes and require honest stale marking or regeneration; add focused regression. Do not expand pressing security repair.
