# paraverse-graph: Conference Knowledge Bases in FalkorDB

This component loads a conference knowledge base (KB) into
[FalkorDB](https://www.falkordb.com/), a graph database, and serves it.
Each KB is a dataset in its own repository, mounted as a git submodule under `vendor/`
(see [Datasets](#datasets)). The first is GitHub Universe,
[universe2026-md](https://github.com/jlevy/universe2026-md) (editions 2023 to 2026), at
`vendor/universe2026-md/`. The browser, API and CLI stay here and work on any dataset.
It provides:

- a read-only KB browser, with a table for every kind of entity, record views, link
  popovers and relational navigation
- a JSON API with live updates
- a CLI
- a Swift client that decodes the API’s JSON

The KB stores each entity as a softschema record and exports its nodes and edges to
`kb/_graph/`. A graph database makes those relationships queryable: neighborhoods, paths
between two entities, shared expertise.
The browser is generic: it renders every kind from the KB’s own compiled schemas.

How it relates to the rest of the repository:

- It only reads a dataset’s `kb/` files and never writes to them.
- Its data lives in `db/.data/`, which is gitignored, or in `$PARAVERSE_GRAPH_DATA`.
- The browser listens on loopback port 8766.
- It uses a remote FalkorDB only when you pass `--url`.
- Its test fixtures follow the [data policy](../docs/data-policy.md), like the KB.

## Quick Start

You need uv; nothing else.
FalkorDBLite runs an embedded FalkorDB server, so there is no Docker, VM or account
involved.

Check out the dataset submodules first, from the repository root, or clone with
`git clone --recurse-submodules`:

```bash
git submodule update --init
```

Then, in `db/`:

```bash
make install   # uv sync with the project's own uv.toml (14-day cool-off)
make load      # rebuild the `universe2026_md` graph from the default dataset (a few seconds)
make serve     # the browser at http://127.0.0.1:8766/
make datasets  # the datasets checked out under vendor/
make test      # unit tests, plus end-to-end tests when the default dataset is checked out
make lint      # codespell, ruff, basedpyright (fixes what it can)
make check     # lint without fixing, then all tests: the single command for a CI job
make validate  # validate every artifact of the dataset with softschema, then load
swift test --package-path clients/swift   # the Swift client
```

`make load`, `make validate` and `make serve` take `DATASET=<name>` for another dataset
under `vendor/`, or `KB=<dir>` for any KB directory (relative to `db/`), as in
`make load serve DATASET=other`.

`uv run paraverse-graph serve --watch` reloads the graph whenever a KB build rewrites
`kb/_graph/stats.json` or replaces the whole `kb/` directory.
Open browsers update live, and a failed reload leaves the served graph as it was.

## Datasets

A dataset is a repository with this layout:

```
<dataset repo>/
  kb/                 the knowledge base this component loads
    <kind dirs>/      softschema records: Markdown with YAML frontmatter, or YAML
    _graph/           nodes.jsonl, edges.jsonl and stats.json: the graph export
    _schemas/         the compiled softschema schema for each kind
    _search/          search documents
```

The dataset’s own build writes `_graph/`, `_schemas/` and `_search/`.

To add a dataset, mount its repository under `vendor/` from the repository root, then
load and serve it by name:

```bash
git submodule add https://github.com/<owner>/<dataset>.git vendor/<dataset>
cd db
make datasets                       # lists vendor/*/kb
make load serve DATASET=<dataset>
```

Every command finds its dataset in this order:

1. `--kb DIR`: any KB directory.
2. `--dataset NAME`: the KB at `vendor/NAME/kb`.
3. `$PARAVERSE_KB`: a KB directory.
4. The default dataset, `vendor/universe2026-md/kb`.

`--kb` and `--dataset` cannot be combined.
Named datasets are found by walking up from the working directory, so commands work from
the repository root or from `db/`. If the KB is missing, the error says to run
`git submodule update --init` or pass `--kb` or `--dataset`.

Each dataset loads into its own graph, so several can share one database.
The default dataset, `universe2026-md`, loads into `universe2026_md`. Every other exact
dataset name uses `dataset_` followed by its UTF-8 bytes in hex: `other` loads into
`dataset_6f74686572`. Case and punctuation remain distinct, so `foo-bar`, `foo_bar`,
`Foo` and `foo` have different graph names.
A dataset given as a KB directory is named after the directory that holds `kb/`, or
after the KB directory itself if it is not called `kb`. `--graph NAME` overrides the
graph name. The browser shows the loaded dataset’s name in its header, and `/api/meta`
returns it as `dataset`.

### Selecting and Combining Datasets

The browser’s **Datasets** control selects one or several sources.
With multiple datasets selected, tables, search and records show their combined view.
Selection is shared by browsers using the same server address.
The source datasets and their individual graphs remain unchanged.

Local `serve` offers built datasets found under `vendor/` and loads the initially
selected view before opening the server.
`--include-kb NAME=DIR` adds another local source; `--select-all` initially combines
every available source:

```bash
UV_CONFIG_FILE=uv.toml uv run paraverse-graph serve --dataset universe2026-md \
  --include-kb ptc2026-md=../vendor/ptc2026-md/kb --select-all
```

Shared entity IDs join records.
Person ID collisions require shared verified accounts; names alone never merge people.
Source citations and event participation roles are preserved.
Conflicting scalar values retain source-specific variants under
`_composition.conflicts`, with the first non-null value in dataset-name order used for
the table’s primary value.
A failed selection leaves the last valid view active.

Selected browser views use `<source-graph>__browser_<port>`, separate from source
graphs. They check selected source builds every five seconds and refresh after a build
changes, including when it is loaded separately with `make load`; `--watch` is not
required for these views.
When the requested dataset has no local source, serving an already loaded graph still
works without the selector.

Passing `--graph NAME` or `--url` serves the existing graph directly without rebuilding
it or offering the selector.
This mode needs no local KB unless `--watch` is used.
Add `--include-kb` or `--select-all` to explicitly enable a selected browser view with
these options. Its separate graph is created in the chosen database, using the explicit
graph name as the prefix when supplied.

## Commands

```bash
uv run paraverse-graph load [--dataset NAME | --kb DIR] [--graph NAME] [--db FILE | --url redis://HOST:PORT] [--validate]
uv run paraverse-graph serve [--dataset NAME | --kb DIR] [--graph NAME] [--db FILE | --url redis://HOST:PORT] [--include-kb NAME=DIR ...] [--select-all] [--port 8766] [--watch] [--open]
uv run paraverse-graph datasets                                # the datasets under vendor/
uv run paraverse-graph queries                                 # the named query catalog
uv run paraverse-graph query similar_people id=person:april-leonard
uv run paraverse-graph query connecting_paths a=person:april-leonard b=org:jfrog
uv run paraverse-graph cypher "MATCH (s:Session) RETURN count(s)"  # ad hoc, read-only
```

Every command takes `--format json` for machine-readable output on stdout.
Query and load commands work on the graph of the dataset their options name (see
[Datasets](#datasets)). Local serving offers a separate selected view when sources are
available; explicit graph and remote server targets require selection options to enable
it.

## Browser API

The browser opens to **Overview** (`#/overview`, also the default `#/` route), with a
summary of the loaded dataset and tables for entities, relationship types, source
providers, enrichment coverage, event editions and inclusion basis.
Counts come from the loaded graph.
Links open the corresponding entity tables and quality checks.

Source counts describe direct citations in entity payloads, rather than independent
verification or collected snapshot counts.
Derived entities can inherit provenance through their parent record.
Coverage shows exact present/missing counts and separately identifies stale, unfetched
and unknown states. Review findings can overlap, and a truncated check reports a lower
bound. Load time describes the graph import; source retrieval dates describe the cited
inputs. The export digest covers the node and edge exports, excluding artifact payloads
and schemas.

Data queries use read-only GET requests with JSON responses.
The dataset selection POST changes the server’s shared browser view while preserving the
source datasets and their graphs.
It accepts only loopback Host headers.

| Method | Endpoint | Returns |
| --- | --- | --- |
| GET | `/api/meta` | Graph, dataset, KB digest and load time; kinds grouped for navigation, with counts |
| GET | `/api/overview` | Current load identity; entity and relationship counts; source-provider citations and retrieval dates; exact enrichment coverage, event editions and inclusion basis. Cached per graph load. |
| GET | `/api/datasets` | Available datasets, selected IDs and whether selection is enabled |
| POST | `/api/datasets/select` | Selected IDs and the browser graph after loading the JSON body `{"datasets":["<id>","<id>"]}`; a failed load keeps the previous view |
| GET | `/api/schema/<kind>` | Fields from the compiled softschema schema, nested shapes, default and relationship columns |
| GET | `/api/rows/<kind>` | A page of rows. Takes `offset`, `limit`, `sort`, `order`, `q`, `cols`, `f.<field>=<value>`, `rel=<in\|out>:<TYPE>:<id>` |
| GET | `/api/entity/<id>` | The full payload, names for every reference in it, relationships grouped by type |
| GET | `/api/card/<id>` | A compact card for link popovers |
| GET | `/api/search?q=` | Full-text search across every kind |
| GET | `/api/review`, `/api/review/<check>` | Data-quality checks and their rows |
| GET | `/api/query/<name>` | A named query from the catalog, such as `connecting_paths?a=<id>&b=<id>` |
| GET | `/api/events` | Server-sent events: `hello`, `graph.loaded`, heartbeats |

`connecting_paths` returns paths of one to three hops between two entities, shortest
first. It skips paths through hub nodes (events, days and facets), which connect almost
everything and so explain nothing.

`similar_people` suggests only people the event itself published (`inclusion_basis` of
`published_by_event`), never self-reported or curated people.

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
- **`(:GraphMeta)`:** the dataset name, the KB digest, the load time and relationship
  statistics.
- **Indexes and constraints:** `id` indexes on every label, filter indexes, full-text
  search, and a unique constraint on `Entity.id`.
- **Validation:** every load checks that each node’s artifact declares the envelope of
  the node’s kind and names a contract.
  `load --validate` also runs softschema on every artifact (about 40 s for the full KB),
  the way `softschema validate <artifact>` does: against the compiled schema the
  artifact itself names, at the status it declares.
  It loads nothing if any artifact fails.
  The KB build’s own validation adds its Pydantic models on top.
- **Load checks:** each load builds a uniquely named staging graph with its indexes,
  constraint, schemas and metadata, and checks it against `kb/_graph/stats.json`. Only
  then does it replace the live graph atomically with Redis `RENAME`, so readers never
  see a partial graph, and publish a `graph.loaded` event on the Redis channel
  `paraverse-graph:<graph>`. A failed load leaves the live graph untouched and keeps its
  `<graph>__staging_*` graph for inspection; delete it with `GRAPH.DELETE`. A failed
  `serve --watch` reload deletes its staging graph instead.
  Changes to the KB root, exports, artifacts or schemas during a load abort it before
  publication. Direct-graph `--watch` retries failed loads with exponential backoff,
  capped at a minute. Selected views retry transient database and IO failures after 30
  seconds, doubling to a five-minute cap.
  Invalid source content is retried after its build signature changes or an explicit
  selection request. Build producers must publish complete builds atomically; an in-place
  build paused in a mixed state cannot always be identified from file metadata.

## Layout

| Path | Contents |
| --- | --- |
| `src/paraverse_graph/kb.py` | Find a dataset’s KB; read the graph export and the softschema artifacts |
| `src/paraverse_graph/datasets.py` | Choose the dataset and its graph name; list the datasets under `vendor/` |
| `src/paraverse_graph/mapping.py` | Labels, properties and relationship types |
| `src/paraverse_graph/schemas.py` | Field descriptions from the compiled schemas |
| `src/paraverse_graph/loader.py` | Staging load, checks, swap, indexes, constraint, schemas and events |
| `src/paraverse_graph/validation.py` | Softschema validation of every KB artifact (`load --validate`) |
| `src/paraverse_graph/browser.py` | The Starlette app: browser API, SSE, static front end |
| `src/paraverse_graph/overview.py` | Aggregate provenance and coverage statistics for the welcome page |
| `src/paraverse_graph/web/` | The front end: plain ES modules and CSS, with no build step |
| `src/paraverse_graph/review.py` | Data-quality checks shown in the browser |
| `src/paraverse_graph/queries.py`, `results.py` | The named, read-only query catalog and its JSON form |
| `src/paraverse_graph/cli.py` | The `paraverse-graph` command |
| `tests/` | Dataset resolution tests, and end-to-end tests against the default dataset (`kb_graph.py` loads it once) |
| `clients/swift/` | A standalone SwiftPM package that decodes the API’s JSON (`swift test`) |

## Notices

The browser adapts selected parts of metabrowser, tbd and Lucide; [NOTICE.md](NOTICE.md)
lists them with their licenses.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
