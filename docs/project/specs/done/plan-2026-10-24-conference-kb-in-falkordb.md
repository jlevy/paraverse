# Feature: Conference Knowledge Base in FalkorDB

**Date:** 2026-10-24 (last updated 2026-10-24)

**Author:** Claude Code spike session, for Joshua Levy

**Status:** Implemented (follow-up work moved to the graph catalog and hardening plan)

> The GitHub Universe KB and its pipeline now live in their own repository,
> [jlevy/universe2026-md](https://github.com/jlevy/universe2026-md), which Paraverse
> mounts as a git submodule at `vendor/universe2026-md/`. Paths under `kb/` in this
> document refer to `vendor/universe2026-md/kb/`, and the crawler’s files are in that
> repository’s `pipeline/`.

## Overview

The GitHub Universe crawler (`pipeline/` in
[universe2026-md](https://github.com/jlevy/universe2026-md)) produces a softschema
knowledge base: one YAML artifact per session, person, profile, organization,
repository, account and so on, plus a derived edge-list export in `kb/_graph/`. This
plan maps that knowledge base into FalkorDB, so the people, sessions, organizations and
software can be queried as a graph.
The graph needs to work from a web UI and from other clients.

A working spike lives in `db/`. It is a standalone uv project that:

- loads the whole KB into an embedded FalkorDB with checks
- exposes a catalog of named, read-only queries through a CLI and a loopback HTTP API
- serves a graph explorer page built on `@falkordb/canvas`
- includes a small Swift client that decodes the API’s JSON

Everything is tested against the real KB.

## Goals

- Define how every softschema structure maps to nodes, labels, properties and
  relationships, in a way that keeps working as the contracts evolve.
- Make the graph easy to query for the core questions: schedule, people and their work,
  how people connect, sponsors, and topics.
- Define one JSON contract that a web UI and other clients can all consume.
- Make loads repeatable and safe: a bad load never replaces a good graph.
- Keep this work cleanly separate from the crawler.

## Non-Goals

- Changing the crawler or the KB contracts.
  The spike only reads `vendor/universe2026-md/kb/`.
- Embeddings, vector search and LLM-generated profile text, which need paid APIs that
  have not been approved.
- Multi-conference or production hosting decisions, beyond laying out the options.

## Background

### The Data

The KB build (`universe-kb build`) writes:

- One softschema artifact per entity under `kb/`. Each artifact names its own contract,
  schema and envelope, and its YAML payload is the only source of structured values.
- `kb/_graph/nodes.jsonl` (`id`, `kind`, `name`, `path`), `edges.jsonl` (`source`,
  `relation`, `target`, plus attributes) and `stats.json`. The build fails if any edge
  points at a missing node.

Scale at the time of the spike (the KB is rebuilt often and grows):

| Measure | Value |
| --- | --- |
| Artifacts | 2,369 files, 11 MB on disk |
| Nodes | 2,483 across 17 kinds (821 repositories, 420 social accounts, 233 GitHub accounts, 195 people, 195 profiles, 156 sessions, 133 organizations, ...) |
| Relationships | 9,134 across 39 types |
| FalkorDB memory | about 5 MB (3 MB properties, 2 MB indexes) |
| RDB snapshot | 1.4 MB |

This is tiny for FalkorDB. Size is not a design constraint.
Clarity, provenance and privacy are.
The data model should still assume many conferences and many more attendees later.

New Python work here follows uv-only conventions (see Python Practices below).

## Design

### Separation

The spike is deliberately isolated so it can be adopted, moved or deleted without
touching other work:

| Concern | Where it lives | Coupling |
| --- | --- | --- |
| Crawler and KB | `vendor/universe2026-md/` (a submodule) | `db/` reads `kb/` files only; no imports from `universe_kb` |
| Graph spike | `db/` (own `pyproject.toml`, `uv.lock`, `Makefile`, tests) | none outward |
| Spike data | `db/.data/paraverse-graph.rdb` (gitignored) | none |
| Spike API | loopback port 8766 | none |
| Swift client sketch | `db/clients/swift/` (own SwiftPM package) | none |

### Pipeline

```text
vendor/universe2026-md/kb/
  _graph/nodes.jsonl, edges.jsonl, stats.json   ──┐ which nodes and edges exist
  <kind>/<id>.md|.yaml (softschema artifacts)   ──┤ node properties (YAML payload only)
                                                  ▼
                       paraverse_graph.kb.load_kb      (about 1 s; libyaml)
                       paraverse_graph.mapping         (labels, properties, relationship types)
                       paraverse_graph.loader          (batched UNWIND into <graph>__staging)
                         check counts vs stats.json, check unique ids
                         GRAPH.COPY staging → live, then unique constraint on live
                                                  ▼
                       FalkorDB graph `universe_2026`
                                                  ▼
       paraverse_graph.queries (named, parameterized, read-only) → paraverse_graph.results (JSON)
         ├─ CLI: paraverse-graph query <name> k=v  (text or --format json)
         ├─ HTTP: GET /api/query/<name>?k=v  (paraverse-graph serve, loopback only)
         ├─ Web explorer: / (falkordb-canvas)
         └─ Swift: ParaverseGraphClient (decodes the same JSON)
```

### Mapping Options Considered

The KB’s structure is already graph-shaped.
Entities refer to each other by typed IDs, and the build derives an edge list from those
references. The open question is how much of the nested YAML to turn into graph
structure. Four approaches were weighed:

**A. Export-driven projection (chosen for the spike).** Take nodes and edges from
`kb/_graph/` and properties from each node’s artifact.
Relationship names come from the crawler’s own `graph.py`, so they are curated
(`PRESENTS`, `AFFILIATED_WITH`, `EXPERT_IN`) rather than derived from field paths.
The KB build already guarantees referential integrity, and the loader re-checks counts.

- Pro: no duplicated relationship logic.
- Pro: it tracks the crawler as it adds relations; `has_account`, `maintains` and
  `works_with` all appeared during the spike and loaded with no code change.
- Con: an edge exists only if `graph.py` emits it.

**B. Generic artifact walk.** Ignore the export and derive an edge from every
typed-reference string in every payload, typing it by field path (`SPEAKERS_PERSON`,
`SLOTS_ROOM`).

- Pro: zero coupling to `graph.py`, and it picks up references the export skips.
- Con: relationship names become mechanical.
- Con: backlink fields (`Person.sessions`, `Room.sessions`) would double every edge
  unless excluded by name.

This is a useful cross-check, not the primary model.

**C. Reified value objects.** Promote nested value objects to nodes:
`(:Session)-[:HAS_SLOT]->(:Slot)-[:IN_ROOM]->(:Room)`,
`(:Person)-[:HAS_CLAIM]->(:Claim {basis, confidence})-[:ABOUT]->(:Term)`,
`(:Person)-[:HAS_AFFILIATION]->(:Affiliation {basis, current})-[:AT]->(:Organization)`,
and `(:Source)` or `(:Evidence)` nodes for provenance.

- Pro: highest fidelity; every fact can carry its own evidence, and you can ask “show me
  everything that came from a GitHub profile”.
- Con: one or two more hops on every query, and a much bigger relationship vocabulary.

Recommended selectively later, starting with `Claim` (see Findings).

**D. Document plus graph hybrid (combined with A).** Since FalkorDB properties cannot
hold maps, store the full payload as a JSON string in `doc`, and flatten only what
queries filter on. A UI gets the whole record in one fetch, and the graph stays lean.

### Node Mapping (as Built)

- **Labels.** Each kind gets a primary label (`Session`, `Person`, `GitHubAccount`, ...)
  plus `Entity` on every node, so one index serves lookups by typed ID across kinds.
  Derived labels make common filters cheap and give UIs something to style:
  - `Account` on GitHub and social accounts
  - `Speaker`, `Attendee`, `Organizer`, `SponsorRep`, `Host` or `Volunteer` on a person,
    from their `participations[].role`
  - `Sponsor` on an organization whose `roles` include `sponsor`
- **Identity.** `id` is the KB’s typed ID (`person:april-leonard`). It is unique,
  enforced by a constraint on `Entity.id`.
- **Metadata.** `entity_kind`, `display_name` and `kb_path` come from the export.
  They use new names so they never collide with payload fields such as a venue’s own
  `kind`.
- **Payload scalars.** Top-level scalars and lists of scalars are copied as-is (`title`,
  `abstract`, `bio`, `stars`, `topics`, `aliases`, ...). Typed references are dropped
  from properties, because they already exist as relationships, and two copies could
  disagree.
- **Promoted nested fields.**
  - session: `start`, `end`, `start_epoch`, `end_epoch`, `slot_count`, `capacity`,
    `in_person`, `virtual`
  - organization: `sponsor_tier`, `sponsor_booth`, `sponsor_summary`,
    `sponsor_industries`
  - person: `participation_roles`, `participation_statuses`, `current_titles`
  - profile: `expertise_labels`, `technology_labels`, `language_labels`, and so on
  - event: epochs
- **Search and document.** `search_text` joins names, titles, bios, descriptions and
  aliases for one full-text index across every kind.
  `doc` holds the full payload as JSON. `source_systems` lists where the record came
  from.

Days and taxonomy terms are nested inside `event.md` and `taxonomy/<facet>.yaml`. The
reader finds them by ID inside the parent payload.

### Relationship Mapping (as Built)

- **Type names.** The export’s `relation` becomes the type in upper case (`presents` →
  `PRESENTS`). All 39 types are listed by `CALL db.relationshipTypes()`.
- **Attributes.** Edge attributes (`role`, `tier`, `basis`, `current`, `match`, `via`,
  `field`, `status`, `start`) become relationship properties.
  A non-scalar attribute would be stored as `<name>_json`.
- **Times.** `SCHEDULED_ON` and `HELD_IN` carry `start` plus `start_epoch`, so a slot’s
  time is on the relationship and multi-slot sessions are correct.

### Indexes and Constraints

- Range index on `id` for every primary label and for `Entity`.
- Range indexes on `Session.start_epoch`, `Session.code`, `Repository.stars`,
  `GitHubAccount.login` and `Organization.sponsor_tier`.
- Full-text indexes on `Entity.search_text` (global search), `Session.title` and
  `abstract`, and `Person.display_name` and `bio`.
- Unique constraint on `Entity.id`.

Vector indexes are a later option: `vecf32` embeddings on sessions and profiles, with
HNSW and cosine similarity.
They need an approved embedding provider.

### Load Strategy

Every load is a full rebuild:

1. Write `<graph>__staging`.
2. Check node counts per kind and relationship counts per type against `stats.json`, and
   check that every `id` is unique.
3. Only then `GRAPH.COPY` staging to the live name.
4. Add the unique constraint on the live graph, and wait until it reports `OPERATIONAL`.

A failed check raises `LoadError` and leaves both the live graph and the staging graph
in place for inspection.
A `GraphMeta` node records the KB digest, the KB path, the load time and the export
stats, so any reader can tell which build it is looking at.

Incremental `MERGE` loads are not needed at this size.
They become interesting only for user-generated data, which belongs in a separate graph
anyway.

### Graph Partitioning Options

FalkorDB cannot query across graphs in one query, so the partitioning choice decides
which questions are cheap.

| Option | Good for | Cost |
| --- | --- | --- |
| One graph per edition (`universe_2026`; the spike) | Simple rebuild and swap; matches one KB build | No cross-conference questions |
| One shared catalog graph for all conferences | “Who speaks at both X and Y”, people across years | Typed IDs must be namespaced: `day:2026-10-29` and `session:2072` are only unique within one edition. Rebuilds need per-event replacement |

Recommendation:

- Keep one graph per edition while there is one conference.
- Before a second conference lands, namespace edition-scoped IDs
  (`universe-2026/session:2072`) or add an `event` key, so a shared catalog is a loader
  change rather than a remodel.

### Query API

Clients never send Cypher.
They call named queries from `paraverse_graph.queries.CATALOG`, each parameterized and
run with `GRAPH.RO_QUERY`.

The catalog has 15 queries:

- `stats`, `entity`, `neighborhood`, `search`, `days`
- `schedule`, `sessions_for_term`, `taxonomy`
- `person_card`, `person_repositories`
- `similar_people`, `connecting_paths`
- `organization_card`, `sponsors`, `top_software`

Every response has the same shape:

```json
{
  "query": "person_card",
  "columns": ["p", "r", "x"],
  "rows": [[{"id": "person:april-leonard", "labels": ["Person", "Speaker", "Entity"], "...": "..."}]],
  "graph": {
    "nodes": [{"id": "person:april-leonard", "labels": ["..."], "kind": "person", "name": "April Leonard", "data": {}}],
    "links": [{"id": 12, "relationship": "PRESENTS", "source": "person:april-leonard", "target": "session:1809k", "data": {"role": "speaker"}}]
  }
}
```

The `rows` drive tables and lists.
The `graph` drives a canvas.
Node `data` leaves out `doc` and `search_text` except in `entity`, which adds the parsed
`doc`.

The spike’s HTTP server binds to 127.0.0.1, accepts only GET, rejects unexpected `Host`
headers (a DNS-rebinding guard), and serves only catalog queries.

### Web UI

There are three options, which serve different audiences:

- **Product explorer (spiked).** `paraverse-graph serve` serves a page using
  `@falkordb/canvas` (0.2.8 from jsDelivr; pinned past the 14-day cool-off).
  It has search, a neighborhood graph with click-to-expand, a details panel with the
  full softschema payload, quick lists (sponsors, top software, schedule by day), and
  connecting paths between any two entities.
  All of it is built from the JSON contract above.
- **FalkorDB Browser,** for admin and ad hoc Cypher.
  It points at the same RDB through a normal FalkorDB server or the Docker image.
- **G.V(),** for analysts who want a desktop graph IDE.

### Swift Client

The spike proves the contract decodes in Swift (`db/clients/swift`: `GraphClient`,
`QueryResult`, `GraphNode`, `JSONValue`; 4 XCTests on captured responses).
Clients that cannot run Python have a few ways to reach the graph:

1. **Call the HTTP API.** Run `paraverse-graph serve`, or a hardened version, and have
   the client call it directly.
   This keeps the graph independent, at the cost of a process to manage.
2. **Precomputed JSON snapshots.** Export the person cards, schedule and similarity
   lists at build time, and bundle or cache them in the client.
   There’s no database at runtime and it works offline, but nothing interactive beyond
   what was precomputed.
3. **Swift talking to FalkorDB directly over RESP (not recommended).** There is no
   official Swift SDK. Result parsing is fragile, and the client would hold database
   credentials.

### Privacy

The graph inherits the KB’s rules, set by the [data policy](../../../data-policy.md).
Only public data is stored, and attendees enter only from their own public posts or
curation.

`similar_people` suggests only people with `inclusion_basis = 'published_by_event'`, and
a test enforces this.
Self-reported attendees are browsable but are never suggested as matches.

### Python Practices

`db/` follows `jlevy/simple-modern-uv` and the tbd Python guidelines:

- uv only, with no `requirements.txt`
- hatchling with `uv-dynamic-versioning`
- a project `uv.toml` that pins the uv version and a 14-day `exclude-newer` cool-off
- a `Makefile` (`install`, `lint`, `test`)
- `devtools/lint.py` running codespell, ruff check and format, and basedpyright
- inline tests below `## Tests`, plus end-to-end tests in `tests/`
- argparse with `rich-argparse`, and `--format text|json`, with data on stdout and
  diagnostics on stderr

`requires-python` is `>=3.12` because FalkorDBLite needs it.

## Findings From the Spike

- **Engine.** FalkorDBLite 0.10.0 bundles FalkorDB 4.18.3 (the C engine) with an
  embedded `redis-server`. Local runs and tests need no Docker, VM or account.
- **Speed.**
  - Reading the KB takes about 1.0 s (7 s with the pure-Python YAML loader).
  - Loading, checking, copying and constraining takes about 1.4 s.
  - Every catalog query runs in 2 to 22 ms.
  - The full Python suite runs in about 5 s.
- **Engine limits found:**
  - Properties cannot be maps, hence `doc` and `<attr>_json`.
  - Undirected `shortestPath` is unsupported, and `shortestPath` is only allowed in
    `WITH` or `RETURN`. `connecting_paths` uses a bounded `[*1..3]` match that excludes
    the hub labels `Event`, `Day` and `Facet`, which also gives better explanations.
  - `GRAPH.COPY` does not carry a unique constraint that is still building, so the
    constraint is created on the live graph.
  - `algo.pageRank(label, type)` only follows edges between nodes of one label, so it is
    not useful on bipartite person-to-session data without a projection.
  - `<>` filters do not use indexes.
- **Data quality:**
  - `similar_people` is dominated by profile claims inferred from session facets.
    Every co-speaker of a session inherits all of its topics at `medium` confidence, so
    co-speakers look nearly identical.
    Weight by `basis` and `confidence` (needs claim properties on `EXPERT_IN` and
    `WORKS_WITH`, or reified `Claim` nodes), or down-weight `session_facets`.
  - `connecting_paths` returns parallel paths that differ only in relationship type
    (`MENTIONS` versus `WORKS_WITH`). They should be de-duplicated by node sequence.
  - Full-text ranking favors GitHub accounts, whose bios repeat keywords.
    Per-kind boosts or a label filter would help.
- **Churn.** The KB changed several times during the spike, because the crawler session
  was rebuilding it. Tests read expected counts from `stats.json` at test time for this
  reason, and every load recorded the KB digest.

## Implementation Plan

### Phase 1: Spike (Done)

- [x] `db/` uv project following simple-modern-uv (`pyproject.toml`, `uv.toml`,
  `Makefile`, `devtools/lint.py`, `.gitignore`)
- [x] `paraverse_graph.kb`: read the export and the artifacts (frontmatter-md and
  pure-yaml), keeping timestamps as strings
- [x] `paraverse_graph.mapping`: labels, properties, promoted fields, relationship types
- [x] `paraverse_graph.loader`: staging load, count and uniqueness checks, copy and
  swap, constraint, `GraphMeta`
- [x] `paraverse_graph.queries` and `paraverse_graph.results`: 15-query catalog and the
  JSON contract
- [x] `paraverse_graph.server` and `paraverse_graph/web/`: loopback API and the canvas
  explorer
- [x] `paraverse_graph.cli`: `load`, `queries`, `query`, `cypher`, `serve`
- [x] `db/clients/swift`: Swift decoding of the contract
- [x] Tests: 6 inline, 10 end-to-end on the real KB, 4 Swift; lint clean

### Phase 2: Decide and Integrate

- [x] Decide how other clients reach the graph.
  `db/` stays its own project and package, and clients use its query catalog; extensions
  to the catalog are planned in
  [the graph catalog and hardening plan](../active/plan-2026-10-24-graph-catalog-and-hardening.md).

The follow-ups from this phase (weighting `similar_people` by claim basis,
de-duplicating `connecting_paths` results and boosting search per kind, namespacing
edition-scoped IDs before a second conference, and deciding on hosting and reload
triggers) moved to
[the graph catalog and hardening plan](../active/plan-2026-10-24-graph-catalog-and-hardening.md).

## Testing Strategy

- **Inline unit tests** (`uv run pytest src`):
  - frontmatter parsing and timestamp handling
  - nested payload lookup
  - typed references kept out of properties
  - derived labels and edge attribute encoding
  - query parameter binding and clamping
- **End-to-end** (`tests/test_graph.py`). These load the real KB into a temporary
  embedded database and check:
  - counts per kind and per type equal `stats.json`
  - every node’s `doc` round-trips to its artifact payload
  - indexes and the unique constraint exist on the live graph, and no staging graph is
    left behind
  - a failed check leaves the live graph untouched
  - every catalog query runs
  - the person card matches the artifact’s sessions
  - schedules are complete and ordered
  - `similar_people` honors the privacy rule
  - `connecting_paths` avoids hub nodes
  - the HTTP API serves the catalog and explorer, rejects bad input and rejects foreign
    `Host` headers
- **Swift:** `swift test` in `db/clients/swift` decodes captured responses.
- **Manual:** the explorer was checked in a browser.
  Search, the neighborhood graph, the details panel and connecting paths all worked,
  with no console errors.
- **Not covered:**
  - a remote FalkorDB server (only embedded was run)
  - FalkorDB 6.x (the Rust engine)
  - concurrent writers
  - the explorer’s mobile layout beyond the CSS breakpoint

## Rollout Plan

None yet. The spike runs locally only:

```bash
make -C db install
make -C db load
make -C db serve
```

The explorer is then at <http://127.0.0.1:8766/>.

## Open Questions

- ~~Should the graph become part of another service, or stay its own package?~~ Decided:
  `db/` stays its own package.
- One graph per edition, or a shared catalog across conferences?
  This decides when ID namespacing is needed.
- Where should the shared graph run (FalkorDB Cloud; self-hosted; or embedded), and who
  triggers reloads?
- Should profile claims become `Claim` nodes (option C) so evidence is queryable, or
  stay in `doc`?
- Is there an approved embedding provider for vector search over abstracts and bios?

## References

- [Research: GitHub Universe Knowledge Graph](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/research-2026-10-23-universe-knowledge-graph.md)
- [Architecture: conference graph database](../../architecture/arch-2026-10-24-graph-database.md)
- [KB browser plan](../done/plan-2026-10-24-kb-browser.md), which replaced the spike’s
  explorer page
- universe2026-md’s `README.md` and `kb/README.md`
- `db/README.md`
- FalkorDB docs: [design](https://docs.falkordb.com/design),
  [indexing](https://docs.falkordb.com/cypher/indexing),
  [concurrency](https://docs.falkordb.com/design/concurrency),
  [known limitations](https://docs.falkordb.com/cypher/known-limitations)
- [`@falkordb/canvas`](https://www.npmjs.com/package/@falkordb/canvas),
  [FalkorDBLite](https://pypi.org/project/falkordblite/),
  [simple-modern-uv](https://github.com/jlevy/simple-modern-uv)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
