---
type: is
id: is-01m5qvrdmd50fm53bjncv95e40
title: "PR #6 qodo-5639989300 #9: malformed KB files crash the CLI with a traceback (https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)"
kind: bug
status: closed
priority: 3
version: 3
delegate: claude-code@spud10.local
labels: []
dependencies: []
parent_id: is-01m5qvqrkg8ta7ghjbs3d36x25
hold: null
hold_until: null
created_at: 2026-10-24T21:06:08.140Z
updated_at: 2026-10-24T21:13:19.579Z
started_at: 2026-10-24T21:10:23.173Z
closed_at: 2026-10-24T21:13:19.563Z
close_reason: "fixed in 'fix(db): report malformed KB files as one-line errors' (7e188aa before restack): JSON, YAML and UTF-8 errors in nodes/edges JSONL, stats.json, artifacts and schemas are KbErrors naming the file (and JSONL line); CLI escapes error text. Confirmed by tests/test_datasets.py::test_malformed_kb_files_are_one_line_errors and schemas.py::test_unreadable_schema_is_a_kb_error (both failed before the fix)."
resolution: null
duplicate_of: null
---
Severity: Low (Qodo). PR #6. Review: https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300. Inline comment: https://github.com/jlevy/paraverse/pull/6#discussion_r4368488670. Location: db/src/paraverse_graph/kb.py:74-146, 220-230; cli.py:48-54 (main). load_kb and read_artifact call json.loads and yaml.load directly, so a bad JSONL line, stats.json or artifact YAML raises JSONDecodeError or YAMLError instead of KbError, and main exits with a traceback instead of a one-line error and exit code 1. Suggested fix: convert parse errors to KbError naming the file and line.
