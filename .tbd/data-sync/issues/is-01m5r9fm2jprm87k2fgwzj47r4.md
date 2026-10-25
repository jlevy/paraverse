---
type: is
id: is-01m5r9fm2jprm87k2fgwzj47r4
title: "PTC followup: publish KB output atomically on copy failures"
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-25T01:05:59.889Z
updated_at: 2026-10-25T01:05:59.889Z
---
Deferred PR1 correctness finding: injected final copytree failure can delete the old KB before replacement succeeds. Stage output and atomically publish or recover old tree; failure-injection regression required. Preserve current pressing privacy/security scope.
