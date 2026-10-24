# Architecture: Conference Graph Database

**Date:** 2026-10-24 (last updated 2026-10-24)

**Author:** Joshua Levy, with LLM assistance

**Status:** In Review

## Overview

`db/` loads a conference knowledge base (KB) into
[FalkorDB](https://docs.falkordb.com/), so that people, sessions, organizations and
software can be queried as a graph.
It is a self-contained uv project (package `paraverse_graph`, CLI `paraverse-graph`) and
serves the graph through:

- a read-only [KB browser](arch-2026-10-24-kb-browser.md) on port 8766
- a JSON API with live updates
- a CLI with a catalog of named, read-only queries
- a Swift client, `clients/swift/ParaverseGraphClient`, that decodes the API’s JSON

The first KB is GitHub Universe, built and published in its own repository,
[jlevy/universe2026-md](https://github.com/jlevy/universe2026-md), and described in its
[architecture doc](https://github.com/jlevy/universe2026-md/blob/main/docs/project/architecture/arch-2026-10-24-conference-kb.md).
Paraverse mounts that repository as a git submodule at `vendor/universe2026-md/`, and
the graph reads its records from `vendor/universe2026-md/kb/`. To get it, clone
Paraverse with `git clone --recurse-submodules`, or run `git submodule update --init` in
an existing clone. `db/README.md` has the quick start and command reference.

## Goals and Non-Goals

### Goals

- Map every softschema structure to nodes, labels, properties and relationships, in a
  way that keeps working as the contracts gain fields and relations.
- Answer the common questions cheaply: the schedule, people and their work, how two
  entities connect, sponsors, and topics.
- Offer one JSON contract that a web UI and other clients can all consume.
- Make loads repeatable and safe: a bad load never replaces a good graph, and readers
  never see a partial one.

### Non-Goals

- Changing the KB, its contracts or how it is built.
  The graph is a projection of `vendor/universe2026-md/kb/`, and corrections go into the
  KB’s curation in universe2026-md.
- Writing user data or anything user-generated into the catalog graph.
- Embeddings and vector search, which need an approved embedding provider.
- Public hosting. The server binds to loopback.

## System Context

```text
vendor/universe2026-md/kb/
  _graph/nodes.jsonl, edges.jsonl, stats.json   ──┐ which nodes and edges exist
  _schemas/*.schema.yaml                         ──┤ field descriptions per kind
  <kind>/<id>.md|.yaml (softschema artifacts)    ──┤ node properties (YAML payload only)
                                                   ▼
                    paraverse-graph load
                      read the export and artifacts
                      map labels, properties and relationship types
                      build a uniquely named staging graph, with indexes,
                        constraint, schema nodes and metadata
                      check counts against stats.json
                      RENAME staging → live; publish graph.loaded
                                                   ▼
                    FalkorDB graph `universe2026_md`  (embedded by default, data in db/.data/)
                                                   ▼
    named query catalog (parameterized, read-only)  →  JSON results
      ├─ CLI:     paraverse-graph query <name> k=v
      ├─ HTTP:    GET /api/query/<name>?k=v and the browser API (loopback only)
      ├─ Browser: tables, records, search and review checks
      └─ Swift:   ParaverseGraphClient
```

`db/` stands apart from the conference pipeline:

- It reads only files under `vendor/universe2026-md/kb/` and imports nothing from
  `universe_kb`.
- Its data lives in `db/.data/paraverse-graph.rdb` by default (`PARAVERSE_GRAPH_DATA`
  overrides the directory), which is Git-ignored.
- It uses a remote FalkorDB only when `--url` is passed; by default it runs an embedded
  server.

## Design

### Engine

[FalkorDBLite](https://pypi.org/project/falkordblite/) bundles the FalkorDB engine with
an embedded `redis-server` child process, so local runs and tests need no Docker, VM or
account. The whole multi-edition KB is small for FalkorDB (a few thousand nodes, tens of
thousands of relationships, a few megabytes of memory), so size is not a design
constraint; clarity, provenance and privacy are.

### Mapping

The KB is already graph-shaped: entities refer to each other by typed IDs, and the KB
build derives an edge list from those references.
The loader takes nodes and edges from `vendor/universe2026-md/kb/_graph/` and each
node’s properties from its artifact’s YAML payload.

#### Nodes

- **Labels.** Each kind gets a primary label (`Session`, `Person`, `GitHubAccount` and
  so on) plus `Entity` on every node, so one index serves lookups by typed ID across
  kinds. Derived labels make common filters cheap and give UIs something to style:
  `Account` on GitHub and social accounts; `Speaker`, `Attendee`, `Organizer`,
  `SponsorRep`, `Host` or `Volunteer` on a person, from their participations; and
  `Sponsor` on an organization whose roles include `sponsor`.
- **Identity.** `id` is the KB’s typed ID, such as `person:jane-doe`, enforced unique by
  a constraint on `Entity.id`.
- **Metadata.** `entity_kind`, `display_name` and `kb_path` come from the export.
  Their names never collide with payload fields such as a venue’s own `kind`.
- **Payload scalars.** Top-level scalars and lists of scalars are copied as they are
  (`title`, `abstract`, `bio`, `stars`, `topics`, `aliases` and so on).
  Typed references are left out of properties, because they already exist as
  relationships and two copies could disagree.
- **Promoted nested fields.** A few nested values that queries filter on are flattened:
  a session’s `start`, `end`, `start_epoch`, `end_epoch`, `slot_count`, `capacity`,
  `in_person` and `virtual`; an organization’s `sponsor_tier`, `sponsor_booth`,
  `sponsor_summary` and `sponsor_industries`; a person’s `participation_roles`,
  `participation_statuses` and `current_titles`; and a profile’s claim labels.
- **Search and document.** `search_text` joins names, titles, bios, descriptions and
  aliases for one full-text index across every kind.
  `doc` holds the full payload as a JSON string, because FalkorDB properties cannot hold
  maps; a client gets the whole record in one fetch while the graph stays lean.
  `source_systems` lists where the record came from.

Days and taxonomy terms are nested inside their event and facet files; the loader finds
them by ID inside the parent payload.

#### Relationships

- **Types.** The export’s `relation` becomes the type in upper case (`presents` becomes
  `PRESENTS`).
- **Attributes.** Edge attributes (`role`, `tier`, `basis`, `current`, `match`, `field`,
  `status`, `start`) become relationship properties; a non-scalar attribute would be
  stored as `<name>_json`.
- **Times.** `SCHEDULED_ON` and `HELD_IN` carry `start` and `start_epoch`, so each
  slot’s time is on its relationship and sessions with several slots are correct.

Because names come from the KB’s curated relation vocabulary (`PRESENTS`,
`AFFILIATED_WITH`, `EXPERT_IN`), a relation the KB build adds loads with no code change.

#### Schema and Metadata Nodes

- **One `(:Schema)` node per kind** holds the kind’s title, description, contract, the
  compiled JSON Schema, and a flattened field list (name, title, description, JSON type,
  whether it is required, whether it is a reference and to which kinds, and the nested
  definition if any). Kinds without a schema of their own (`day` and `term`) take their
  fields from the parent’s definitions.
  These nodes let the browser render any kind generically.
- **One `(:GraphMeta)` node** records the KB digest, the KB path, the load time, the
  export statistics and relationship statistics (`kind -[TYPE]-> kind` with counts), so
  any reader can tell which KB build it is looking at without scanning the graph.

#### Indexes and Constraints

- Range indexes on `id` for every primary label and for `Entity`.
- Range indexes on the fields that queries filter on, such as `Session.start_epoch`,
  `Session.code`, `Repository.stars`, `GitHubAccount.login` and
  `Organization.sponsor_tier`.
- Full-text indexes on `Entity.search_text` (global search), on session titles and
  abstracts, and on people’s names and bios.
- A unique constraint on `Entity.id`.

### Load Strategy

Every load is a full rebuild:

1. Build a uniquely named staging graph (`<graph>__staging_*`) with batched `UNWIND`
   writes, its indexes, the unique constraint, the schema nodes and the metadata.
2. Check node counts per kind and relationship counts per type against
   `vendor/universe2026-md/kb/_graph/stats.json`, and check that every `id` is unique.
3. Only then replace the live graph atomically with Redis `RENAME`, so readers never see
   a partial graph.
4. Publish a `graph.loaded` event on the Redis channel `paraverse-graph:<graph>`.
   FalkorDB is Redis, so live updates need no other infrastructure.

A failed check leaves the live graph untouched and keeps the staging graph for
inspection; `GRAPH.DELETE` removes it.
Loading the whole KB takes a couple of seconds, so incremental `MERGE` loads are not
needed.

`paraverse-graph serve --watch` reloads the graph when the KB build rewrites
`vendor/universe2026-md/kb/_graph/stats.json` or replaces `vendor/universe2026-md/kb/`,
and open browsers update live.
A failed reload leaves the served graph as it was.

### Query Catalog

Clients never send Cypher.
They call named queries from the catalog, each parameterized and run with
`GRAPH.RO_QUERY`:

- **Lookup:** `stats`, `entity`, `neighborhood`, `search`
- **Program:** `days`, `schedule`, `sessions_for_term`, `taxonomy`
- **People:** `person_card`, `person_repositories`, `similar_people`
- **Connections:** `connecting_paths`
- **Organizations and software:** `organization_card`, `sponsors`, `top_software`

`paraverse-graph queries` lists the catalog with each query’s description and
parameters.

- **`connecting_paths`** returns paths of up to three hops between two entities that
  avoid hub nodes (events, days and facets).
  FalkorDB does not support undirected `shortestPath`, so the query uses a bounded
  `[*1..3]` match; excluding hubs also gives better explanations, because a path through
  “both are at the same event” explains nothing.
- **`similar_people`** ranks people by how many `EXPERT_IN` and `WORKS_WITH` targets
  they share with a given person.
  It never suggests self-reported attendees, and a test enforces this.

Every response has the same shape:

```json
{
  "query": "person_card",
  "columns": ["p", "r", "x"],
  "rows": [[{"id": "person:jane-doe", "labels": ["Person", "Speaker", "Entity"]}]],
  "graph": {
    "nodes": [{"id": "person:jane-doe", "labels": ["Person", "Speaker", "Entity"],
               "kind": "person", "name": "Jane Doe", "data": {}}],
    "links": [{"id": 12, "relationship": "PRESENTS", "source": "person:jane-doe",
               "target": "session:bld9001b", "data": {"role": "speaker"}}]
  }
}
```

`rows` drive tables and lists, and `graph` drives a canvas.
Node `data` leaves out `doc` and `search_text`, except in `entity`, which adds the
parsed `doc`.

### CLI

```bash
paraverse-graph load [--kb DIR] [--graph NAME] [--db FILE | --url redis://HOST:PORT]
paraverse-graph serve [--port 8766] [--watch] [--open]
paraverse-graph queries
paraverse-graph query similar_people id=person:jane-doe
paraverse-graph cypher "MATCH (s:Session) RETURN count(s)"   # ad hoc, read-only
```

Every command takes `--format json` for machine-readable output on stdout, with
diagnostics on stderr.
`cypher` is for developers at a terminal; the HTTP API never accepts Cypher.

### Swift Client

`clients/swift/ParaverseGraphClient` is a standalone SwiftPM package that decodes the
query catalog’s JSON contract.
Its tests (`swift test`) decode captured responses, so a change to the contract that
breaks decoding fails there.

### Project Layout

| Module | Responsibility |
| --- | --- |
| `kb` | Read the graph export and the softschema artifacts (frontmatter Markdown and pure YAML), keeping timestamps as strings |
| `mapping` | Labels, properties, promoted fields and relationship types |
| `schemas` | Field descriptions from the compiled schemas |
| `loader` | Staging load, checks, swap, indexes, constraint, schema nodes and events |
| `queries`, `results` | The named query catalog and its JSON form |
| `browser`, `web/` | The browser’s Starlette app and its static front end |
| `review` | Data-quality checks shown in the browser |
| `cli` | The `paraverse-graph` command |

## Trade-offs and Alternatives

### Mapping the KB to a Graph

**Chosen approach:** an export-driven projection.
Nodes and edges come from `vendor/universe2026-md/kb/_graph/`, properties from each
node’s artifact, and the full payload is kept as `doc`.

**Alternatives considered:**
- **A generic artifact walk** that derives an edge from every typed reference and names
  it by field path (`SPEAKERS_PERSON`): rejected as the primary model because relation
  names become mechanical, and backlink fields would double every edge unless excluded
  by name. It remains a useful cross-check.
- **Reified value objects** (`(:Person)-[:HAS_CLAIM]->(:Claim)-[:ABOUT]->(:Term)`,
  `Affiliation` and `Evidence` nodes): deferred.
  It gives the highest fidelity (every fact carries its evidence, and “everything that
  came from a GitHub profile” becomes a query), at the cost of extra hops on every query
  and a much larger vocabulary.

**Rationale:** the KB build already guarantees referential integrity and owns the
relation vocabulary, so the graph adds no relationship logic of its own.

### Swapping Graphs

**Chosen approach:** build in a staging graph, check it, then `RENAME`.

**Alternatives considered:**
- Copying staging to live with `GRAPH.COPY`: rejected because the copy does not carry a
  unique constraint that is still building, so the constraint would have to be created
  on the live graph after the swap.

**Rationale:** a rename is atomic, so readers see either the old graph or the new one,
and the staging graph is complete, constraint included, before anyone reads it.

### Partitioning

**Chosen approach:** one graph per KB build.
The GitHub Universe KB holds all four editions, so a single `universe2026_md` graph
answers questions across years.

**Alternatives considered:**
- **One graph per edition:** simpler swaps, but no cross-edition questions.
- **One shared graph for several conferences:** answers “who spoke at both”, but needs
  conference-scoped IDs (sessions, days, terms) to be namespaced first.

**Rationale:** FalkorDB cannot query across graphs, so the partition decides which
questions are cheap; one graph per KB matches one build and one swap.

## Security Considerations

- **Read-only.** Every query runs with `GRAPH.RO_QUERY`. Queries through the HTTP API
  and browser also have a 4-second timeout; the CLI’s `query` command has none.
  The HTTP server accepts only GET and serves only catalog queries and the browser API.
- **Loopback only.** The server binds to 127.0.0.1 and rejects requests whose `Host`
  header is not a loopback name (a DNS-rebinding guard).
- **No injection through names.** Labels, relationship types and property names are
  interpolated into Cypher only after they are checked against the schema nodes, the
  known labels, the stored relationship statistics and a strict identifier pattern.
  Values are always query parameters.
- **Remote servers.** A remote FalkorDB is used only when `--url` is passed, so a
  default `load` never writes to a shared instance.
- **Privacy.** The graph inherits the KB’s [data policy](../../data-policy.md): it holds
  only what the KB holds, and `similar_people` never suggests self-reported attendees.
  Nothing about a client’s user is written to the graph; user input is only ever a query
  parameter.
- **Untrusted text.** Payload text is copied from public sources, and clients,
  especially LLM-based ones, must treat it as data.

## Operational Concerns

### Testing

- **Inline unit tests** (`uv run pytest src`) cover frontmatter parsing and timestamps,
  nested payload lookup, typed references kept out of properties, derived labels, edge
  attribute encoding, and query parameter binding and clamping.
- **End-to-end tests** (`tests/`) load the real KB once into a temporary embedded
  database and check that counts per kind and per type equal `stats.json`, that every
  node’s `doc` round-trips to its artifact, that indexes and the constraint exist and no
  staging graph is left behind, that a failed check leaves the live graph untouched,
  that every catalog query runs, that `similar_people` honors the privacy rule, that
  `connecting_paths` avoids hub nodes, and that the HTTP API rejects bad input and
  foreign `Host` headers.
  Expected counts are read from `stats.json` at test time, so the tests follow KB
  rebuilds.
- **Swift:** `swift test` in the client package.

### Project Practices

`db/` follows [simple-modern-uv](https://github.com/jlevy/simple-modern-uv): uv only,
hatchling with `uv-dynamic-versioning`, a project `uv.toml` with a 14-day
`exclude-newer` cool-off, a `Makefile` (`install`, `load`, `serve`, `test`, `lint`), and
lint with codespell, ruff and basedpyright.
`requires-python` is at least 3.12, as FalkorDBLite requires.

### Engine Pitfalls

Facts about FalkorDB that shape the queries:

- Properties cannot be maps, hence `doc` and `<attr>_json`.
- Undirected `shortestPath` is unsupported, and `shortestPath` is allowed only in `WITH`
  or `RETURN`.
- `algo.pageRank(label, type)` follows only edges between nodes of one label, so it is
  not useful on bipartite person-to-session data without a projection.
- `<>` filters do not use indexes.
- `count(*)` over a relationship pattern can collapse parallel edges (a session with two
  slots in one room); count relationships with `count(r)`.
- Concatenating a string with an aggregate in one `RETURN` yields `null`; aggregate in a
  `WITH` first.

### Deployment and Scaling

The graph runs locally, embedded, with `make load` and `make serve`. Loads take seconds
and queries milliseconds at the current size.
Hosting a shared graph, and deciding who triggers reloads after a KB build, are open
questions.

## Open Questions

Open work is tracked in
[the graph catalog and hardening plan](../specs/active/plan-2026-10-24-graph-catalog-and-hardening.md);
[the FalkorDB spike spec](../specs/done/plan-2026-10-24-conference-kb-in-falkordb.md)
records how the mapping was chosen.

- Should profile claims become `Claim` nodes, so evidence is queryable in the graph?
- Where should a shared graph run (a hosted FalkorDB, self-hosted, or embedded per
  machine), and what triggers its reloads?
- Before a second conference: one graph per conference, or a shared graph with
  namespaced conference-scoped IDs?
- Is there an approved embedding provider for vector search over abstracts and bios?

## References

- [Architecture: conference knowledge base](https://github.com/jlevy/universe2026-md/blob/main/docs/project/architecture/arch-2026-10-24-conference-kb.md)
- [Architecture: KB browser](arch-2026-10-24-kb-browser.md)
- `db/README.md`
- FalkorDB docs: [design](https://docs.falkordb.com/design),
  [indexing](https://docs.falkordb.com/cypher/indexing),
  [concurrency](https://docs.falkordb.com/design/concurrency),
  [known limitations](https://docs.falkordb.com/cypher/known-limitations)
- [FalkorDBLite](https://pypi.org/project/falkordblite/),
  [simple-modern-uv](https://github.com/jlevy/simple-modern-uv)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
