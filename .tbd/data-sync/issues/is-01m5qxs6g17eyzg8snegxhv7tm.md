---
type: is
id: is-01m5qxs6g17eyzg8snegxhv7tm
title: Require compiled schema coverage before graph publication
kind: bug
status: open
priority: 2
version: 1
labels: []
dependencies: []
created_at: 2026-10-24T21:41:30.752Z
updated_at: 2026-10-24T21:41:30.752Z
---
At6fc8c39 schemas.py:71 accepts absent/empty _schemas and loader.py:183 does not compare loaded kinds to compiled schema kinds. Browser navigation/row endpoints need schemas, so loader may publish a graph that browser cannot fully display. Require schema coverage before atomic rename and test failure leaves live graph. Parent pv-67zv.
