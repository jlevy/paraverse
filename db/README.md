# paraverse-graph: Conference Knowledge Base in FalkorDB

This component loads a Paraverse conference knowledge base (KB) into
[FalkorDB](https://www.falkordb.com/), a graph database, and serves it.
The first KB is GitHub Universe, in `conferences/githubuniverse/kb/` (editions 2023 to
2026).
It provides:

- a read-only KB browser, with a table for every kind of entity, record views, link
  popovers and relational navigation
- a JSON API with live updates
- a CLI
- a Swift client that decodes the API’s JSON

The KB stores each entity as a softschema record and exports its nodes and edges to
`kb/_graph/`. A graph database makes those relationships queryable: neighborhoods,
paths between two entities, shared expertise.
The browser is generic: it renders every kind from the KB’s own compiled schemas.

How it relates to the rest of the repository:

- It only reads `kb/` files and never writes to them.
- Its data lives in `db/.data/`, which is gitignored, or in `$PARAVERSE_GRAPH_DATA`.
- The browser listens on loopback port 8766.
- It uses a remote FalkorDB only when you pass `--url`.
- Its test fixtures follow the [data policy](../docs/data-policy.md), like the KB.

## Quick Start

You need uv; nothing else.
FalkorDBLite runs an embedded FalkorDB server, so there is no Docker, VM or account
involved.

```bash
make install   # uv sync with the project's own uv.toml (14-day cool-off)
make load      # rebuild the `universe` graph from the KB (about 2 s)
make serve     # the browser at http://127.0.0.1:8766/
make test      # unit tests, plus end-to-end tests against the KB when it is present
make lint      # codespell, ruff, basedpyright
swift test --package-path clients/swift   # the Swift client
```

`uv run paraverse-graph serve --watch` reloads the graph whenever a KB build rewrites
`kb/_graph/stats.json` or replaces the whole `kb/` directory.
Open browsers update live, and a failed reload leaves the served graph as it was.

## Commands

```bash
uv run paraverse-graph load [--kb DIR] [--graph NAME] [--db FILE | --url redis://HOST:PORT]
uv run paraverse-graph serve [--port 8766] [--watch] [--open]
uv run paraverse-graph queries                                 # the named query catalog
uv run paraverse-graph query similar_people id=person:april-leonard
uv run paraverse-graph query connecting_paths a=person:april-leonard b=org:jfrog
uv run paraverse-graph cypher "MATCH (s:Session) RETURN count(s)"  # ad hoc, read-only
```

Every command takes `--format json` for machine-readable output on stdout.

## Browser API

The API is read-only GET with JSON responses.
It accepts only loopback Host headers.

| Endpoint | Returns |
| --- | --- |
| `/api/meta` | Graph, KB digest and load time; kinds grouped for navigation, with counts |
| `/api/schema/<kind>` | Fields from the compiled softschema schema, nested shapes, default and relationship columns |
| `/api/rows/<kind>` | A page of rows. Takes `offset`, `limit`, `sort`, `order`, `q`, `cols`, `f.<field>=<value>`, `rel=<in\|out>:<TYPE>:<id>` |
| `/api/entity/<id>` | The full payload, names for every reference in it, relationships grouped by type |
| `/api/card/<id>` | A compact card for link popovers |
| `/api/search?q=` | Full-text search across every kind |
| `/api/review`, `/api/review/<check>` | Data-quality checks and their rows |
| `/api/query/<name>` | A named query from the catalog, such as `connecting_paths?a=<id>&b=<id>` |
| `/api/events` | Server-sent events: `hello`, `graph.loaded`, heartbeats |

`connecting_paths` returns paths of one to three hops between two entities, shortest
first.
It skips paths through hub nodes (events, days and facets), which connect almost
everything and so explain nothing.

## What Gets Built

- **Nodes:** one per entity in `kb/_graph/nodes.jsonl`.
  - **Labels:** each node has its kind’s label plus `Entity`. Derived labels include
    `Speaker`, `Attendee`, `Sponsor` and `Account`.
  - **Properties:** the payload’s top-level scalars, a few promoted nested fields, and
    the full payload as JSON in `doc`.
- **Relationships:** one per line in `edges.jsonl`, with the relation in upper case and
  the edge’s attributes as properties.
- **Schema nodes:** one `(:Schema)` per kind, with field descriptions from
  `kb/_schemas/`. They make the browser generic.
- **`(:GraphMeta)`:** the KB digest, the load time and relationship statistics.
- **Indexes and constraints:** `id` indexes on every label, filter indexes, full-text
  search, and a unique constraint on `Entity.id`.
- **Load checks:** each load builds a uniquely named staging graph with its indexes,
  constraint, schemas and metadata, and checks it against `kb/_graph/stats.json`.
  Only then does it replace the live graph atomically with Redis `RENAME`, so readers
  never see a partial graph, and publish a `graph.loaded` event on the Redis channel
  `paraverse-graph:<graph>`. A failed load leaves the live graph untouched and keeps its
  `<graph>__staging_*` graph for inspection; delete it with `GRAPH.DELETE`.

## Layout

| Path | Contents |
| --- | --- |
| `src/paraverse_graph/kb.py` | Read the graph export and the softschema artifacts |
| `src/paraverse_graph/mapping.py` | Labels, properties and relationship types |
| `src/paraverse_graph/schemas.py` | Field descriptions from the compiled schemas |
| `src/paraverse_graph/loader.py` | Staging load, checks, swap, indexes, constraint, schemas and events |
| `src/paraverse_graph/browser.py` | The Starlette app: browser API, SSE, static front end |
| `src/paraverse_graph/web/` | The front end: plain ES modules and CSS, with no build step |
| `src/paraverse_graph/review.py` | Data-quality checks shown in the browser |
| `src/paraverse_graph/queries.py`, `results.py` | The named, read-only query catalog and its JSON form |
| `src/paraverse_graph/cli.py` | The `paraverse-graph` command |
| `tests/` | End-to-end tests against the KB (`kb_graph.py` loads it once) |
| `clients/swift/` | A standalone SwiftPM package that decodes the API’s JSON (`swift test`) |

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
