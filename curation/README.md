# Curation Lists

Curation lists record public, professional connections between people and a dataset.
This component checks `<dataset>/additional-people.csv` before a reviewer considers
adding its rows to the knowledge base.
Follow the [data policy](../docs/data-policy.md) for every cell, including reasons and
sources.

The checker and the header-only `universe2026-md` list are ready to use.
Populated intake is a separate dataset feature tracked as `u26-p69k`; the current build
handoff rejects a populated list before running the dataset pipeline.
That follow-up implements association records, identity matching, removal handling and
the corresponding bios, search and graph behavior.
A valid list alone does not establish those behaviors.

## Commands

Use Python 3.12 or later.
Run from `curation/`:

```bash
make install
make lint-check test check
make build DATASET=universe2026-md
```

`make check` checks all lists.
To check selected files, run
`uv run paraverse-curation check example-data/additional-people.csv`. `--root PATH`
before the command selects another curation directory.
Problems identify the file, physical CSV line and column; cell values are not echoed.

`make build` checks the selected header-only list and runs `uv run universe-kb build` in
`../vendor/<dataset>/pipeline`, with that pipeline’s `uv.toml` selected explicitly.
Initialize the submodule first with `git submodule update --init` from the repository
root. The dataset’s own pipeline owns its generated data; this component does not edit
it. The handoff preserves the dataset command’s exit status.

For task-specific environments, set `UV_PROJECT_ENVIRONMENT` to an external environment
directory. The handoff uses a separate sibling `<dataset>-pipeline-venv` for the dataset
so its dependencies cannot replace the checker environment.

## CSV Format

Use UTF-8 without a byte-order mark and the exact header in the checked-in list.
Keep every cell on one line and use normal CSV quoting for commas.
One row records one person, relation and target; duplicate facts are rejected by
normalized account identity.

| Columns | Requirement | Meaning |
| --- | --- | --- |
| `name` | Required | The person’s public professional name |
| `reason` | Required | A professional fact supported by the source; no private context or sensitive inference |
| `relation` | Required | `maintainer`, `author`, `colleague`, `organizer_staff`, `sponsor_staff` or `community` |
| `target` | Optional | A typed KB ID, such as `software:example-project`, or a public HTTPS URL |
| `source_url` | Required | A public HTTPS source that supports the relation |
| `github`, `linkedin`, `x`, `bluesky`, `mastodon`, `website` | At least one | The person’s own professional account or website |
| `organization`, `title` | Optional | A public professional role |
| `attendance_source` | Optional | A public statement by the person that they are attending |
| `added_by`, `added_on` | Required | The editor’s GitHub handle and an ISO date (`YYYY-MM-DD`) |

GitHub and X accept a handle or profile URL; LinkedIn accepts a profile URL. Bluesky
accepts a handle. Mastodon accepts `@user@host` or an HTTPS profile URL, and websites
must use HTTPS on a domain name.
Local hosts, IP addresses and URLs with credentials are rejected.

The checker rejects missing fields, malformed accounts and dates, duplicate facts, email
addresses and phone numbers, including common obfuscations.
A reviewer must still verify that each source is public, belongs to the person and
supports the professional fact.
The checker cannot establish source ownership, sensitive inference, identity equivalence
across different accounts or the truth of an attendance claim.
A URL in `attendance_source` never establishes attendance by itself.

Removal requests belong in the dataset’s suppression process.
Keep request details and identifiers out of this public list; see the dataset’s removal
instructions.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
