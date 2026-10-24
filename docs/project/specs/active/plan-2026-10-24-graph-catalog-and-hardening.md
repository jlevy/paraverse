# Feature: Graph Catalog Extensions and Hardening

**Date:** 2026-10-24 (last updated 2026-10-24)

**Author:** Claude Code spike session, for Joshua Levy

**Status:** Draft

## Overview

Extend the `paraverse_graph` named-query catalog in `db/` so that clients beyond the KB
browser can use it: topic resolution from free text, people for a set of topics, the
overlap between one person and a topic list, properties that join graph results to
catalog IDs and profile URLs, list parameters, and safe loading of a remote FalkorDB. It
also collects the graph’s open hardening work: better ranking, CI, and readiness for a
second conference.

This plan builds on
[the FalkorDB spike spec](../done/plan-2026-10-24-conference-kb-in-falkordb.md), which
covers the mapping, the catalog and the JSON contract.
The graph reads the GitHub Universe KB from `vendor/universe2026-md/kb/`, a git
submodule (clone with `--recurse-submodules`, or run `git submodule update --init`).

## Goals

- **Topic queries:** map free-text interests to KB terms and software, and find people
  by those terms, with evidence for every stated connection.
- **Joinable results:** give clients the catalog session IDs and profile URLs they need
  to link graph results to the event’s own pages.
- **Remote-ready:** run against a remote FalkorDB without shipping a bundled
  `redis-server` and without credentials on the command line.
- **Better results:** rank `similar_people` and search by the strength of their
  evidence.
- **Ready for more conferences:** load several KBs without ID collisions.

## Non-Goals

- Changing the crawler, the KB contracts or how the KB is built.
- Writing user data into the shared graph.

## Design

### Changes in `db/` (paraverse_graph)

- **Embedded server as an extra.** Make FalkorDBLite optional:
  `paraverse-graph[embedded]`. A service that talks to a remote FalkorDB in production
  should not ship a bundled `redis-server`. Development and tests install the extra.
- **List parameters.** Add `Param(type=list)`, comma-separated over HTTP and a Cypher
  list in queries, for queries that take several term IDs.
- **Bridging properties** (`mapping.py` promoters):
  - Session: `rainfocus_id`, from the RainFocus `sources[].record_id`, with a range
    index.
  - Person: `x_handle` and `primary_profile_url`, from linked accounts, and
    `listing_url`, the session URL that put them in the KB.
- **New catalog queries:**
  - `resolve_topics(q, limit)`: full-text search restricted to `Term` and `Software`, to
    map free-text interests ("AI agents", “databases”) to KB IDs.
  - `people_for_topics(terms, limit)`: people with `EXPERT_IN` or `WORKS_WITH` to any of
    the terms. It returns the shared terms with each claim’s `basis`, the person’s
    `inclusion_basis`, `participation_roles`, `x_handle` and the sessions they present
    (`rainfocus_id` and title).
    Claims are weighted by basis: direct evidence such as bios, repositories and the
    person’s own posts outranks claims inferred from session facets, which keeps
    co-speakers from crowding the list.
  - `shared_topics(id, terms)`: the overlap between one person and a term list, for “why
    this person” evidence.
- **De-duplicated paths.** `connecting_paths` drops parallel paths that differ only in
  relationship type, keeping one per node sequence.
- **Remote loading without credentials in argv.** `paraverse-graph load` reads a
  `PARAVERSE_GRAPH_URL` environment variable, or `FALKORDB_*` variables, and never takes
  a password on the command line.
  Remote loads require an explicit `--remote` flag, so a default `load` can never
  overwrite a shared instance.

### Loading a Remote Instance

1. Load locally with `make -C db load` (embedded) and run clients against it.
2. Confirm the remote instance supports `GRAPH.CONSTRAINT`, full-text indexes and the
   `MODULE LIST` version read, and record its engine version.
3. Load the remote instance with `paraverse-graph load --remote` (credentials from the
   environment).

Reloads after each `universe-kb build` are a manual step at first.
`GraphMeta` shows which KB build is live.

## Implementation Plan

### Phase 1: Catalog and Loading

- [ ] FalkorDBLite as the `embedded` extra
- [ ] list parameters
- [ ] `rainfocus_id`, `x_handle`, `primary_profile_url` and `listing_url` properties,
  with indexes
- [ ] `resolve_topics`, `people_for_topics` and `shared_topics`
- [ ] de-duplicated `connecting_paths` paths
- [ ] environment-based remote load with `--remote`
- [ ] tests for each

### Phase 2: Ranking and Checks

- [ ] Weight `similar_people` by claim `basis`, which the export already puts on
  `EXPERT_IN` and `WORKS_WITH`; add `confidence` to the export if it is needed too.
- [ ] Add per-kind boosts or a label filter to full-text search, since GitHub accounts,
  whose bios repeat keywords, crowd the top results.
- [ ] Run CI on `db/`: `make lint`, `make test` and the Swift client’s `swift test`.

### Phase 3: Remote Instance and More Conferences

- [ ] Decide on hosting for a shared graph (FalkorDB Cloud, self-hosted, or embedded per
  machine) and how loads are triggered after a KB build.
- [ ] Verify the remote instance’s capabilities, then load the graph remotely.
- [ ] Namespace edition-scoped IDs (sessions, days, terms) or add a conference key
  before a second conference, so a shared graph is a loader change rather than a
  remodel.

## Testing Strategy

- Inline tests for list parameters and the new promoters.
- End-to-end tests on the real KB:
  - `resolve_topics` maps “AI agents” to `term:topic/ai-agents`
  - `people_for_topics` returns `rainfocus_id` values that exist among the KB’s sessions
  - `people_for_topics` ranks direct evidence above session-facet claims
  - de-duplicated paths are unique by node sequence
- A remote-load test that refuses to run without `--remote`.
- `similar_people` ranks direct evidence above session-facet claims.

## Rollout Plan

1. Phases 1 and 2 land in `db/` with tests against the embedded graph.
2. Phase 3 loads a remote instance after the capability check.

## Open Questions

- Should profile claims become `Claim` nodes, so evidence is queryable in the graph?
- Who runs remote reloads after a KB build, and should a server refuse to serve a graph
  whose `kb_digest` is older than the KB on disk?
- Is the remote instance FalkorDB 4.x or 6.x? The 6.0 engine has no 4.x upgrade path
  until 6.2. This matters only if the instance is upgraded mid-project.

## References

- [FalkorDB spike spec](../done/plan-2026-10-24-conference-kb-in-falkordb.md) and
  `db/README.md`
- [KB browser plan](../done/plan-2026-10-24-kb-browser.md)
- [Architecture: conference graph database](../../architecture/arch-2026-10-24-graph-database.md)
- [simple-modern-uv](https://github.com/jlevy/simple-modern-uv)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
