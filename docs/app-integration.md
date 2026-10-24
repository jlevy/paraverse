# App Integration and Dataset Updates

The dataset repository owns its records and softschema contracts.
FalkorDB holds a rebuildable projection for queries; applications should read it through
Paraverse’s HTTP API. See the [architecture diagram](../README.md#architecture),
[database guide](../db/README.md), and
[graph architecture](project/architecture/arch-2026-10-24-graph-database.md).

## How Softschema Reaches FalkorDB

The dataset’s build produces three inputs:

| Input under `kb/` | Role in the graph load |
| --- | --- |
| Markdown records with YAML frontmatter, or YAML records | Structured entity payloads and their contract declarations |
| `_schemas/*.schema.yaml` | Compiled JSON Schemas describing fields, types, enums, typed references, and nested shapes |
| `_graph/nodes.jsonl`, `edges.jsonl`, and `stats.json` | Which entities and relationships exist, their attributes, and expected counts |

The [schema reader](../db/src/paraverse_graph/schemas.py) extracts descriptions from the
compiled schemas. The [loader](../db/src/paraverse_graph/loader.py) stores those
descriptions and schemas in `Schema` nodes, which supply the browser’s generic fields
and tables. FalkorDB entity properties contain scalars, scalar lists, and the full
structured payload as JSON in `doc`. Selected nested values become queryable scalar
properties through explicit [mapping code](../db/src/paraverse_graph/mapping.py); adding
a schema field alone does not add a new promoted property or relationship.

Every load checks record envelopes and contract declarations.
Full [softschema validation](../db/src/paraverse_graph/validation.py) is opt-in through
`load --validate` or `make validate`. It uses each artifact’s referenced schema and
maturity status. Softschema supports envelope inference, so an explicit envelope hint is
not always required.
These are application-side checks; `Schema` nodes do not make FalkorDB enforce
softschema contracts natively.
FalkorDB separately enforces the loaded graph’s unique `Entity.id` constraint.

## Update and Reload a Dataset

1. Edit records or contracts in the dataset’s own repository, then run its documented
   build to produce a complete KB, including graph exports and compiled schemas.

2. Run the dataset’s validation, review the published content against the
   [data policy](data-policy.md), and commit or release the dataset.

3. Review and update Paraverse’s pinned dataset commit when consuming a new release.
   For a submodule checkout, run `git submodule update --init` from Paraverse’s root.
   This checks out the parent repository’s recorded commit; it does not fetch and select
   the latest dataset release automatically.

4. Validate and load that completed KB, then serve its graph.
   From `db/`, replacing the example path with the KB directory:

   ```bash
   make validate KB=../path/to/kb
   make serve KB=../path/to/kb
   ```

`make validate` validates **and loads** the source graph.
Local serving builds a separate browser view from available KB sources.
The **Datasets** control selects one or more sources; Overview and the data API describe
that shared selection.
Selection preserves the source graphs, and selected source builds are watched
automatically. For an explicit graph, add `--watch` to reload it from completed KB
builds:

```bash
UV_CONFIG_FILE=uv.toml uv run paraverse-graph serve --kb ../path/to/kb --graph my_dataset --watch
```

Replace `my_dataset` with the graph name reported by the load.

The [watcher](../db/src/paraverse_graph/cli.py) detects a new `_graph/stats.json` build
marker, including after the dataset build replaces `kb/` by rename.
It imports completed builds; it does not pull Git, run the dataset build, or repeat full
softschema validation.
Editing a record or schema without publishing a new build marker does not trigger a
reload. Build producers must publish complete builds atomically.

Each load builds a separate staging graph, creates its indexes and constraint, and
checks counts and duplicate IDs before an atomic Redis `RENAME` replaces the live graph.
It also detects files changing during the import.
A failure before the swap preserves the previous graph.
After the swap, Redis pub/sub carries `graph.loaded` to the HTTP server, which
invalidates cached descriptions and forwards an SSE event to clients.

## Read the API From an App

Use the [read-only HTTP API](../db/README.md#browser-api) for application features:

| Endpoint | Use |
| --- | --- |
| `/api/meta`, `/api/overview` | Load identity, catalog counts, provenance, and coverage |
| `/api/schema/<kind>` | Field descriptions, reference kinds, and table columns |
| `/api/rows/<kind>` | Filtered, sorted pages using `offset` and `limit` |
| `/api/entity/<id>` | One entity’s payload and relationships |
| `/api/search?q=...` | Search results across entity kinds |
| `/api/query/<name>` | Parameterized named queries, such as schedule or connecting paths |
| `/api/events` | SSE load notifications and a reconnect `hello` stamp |

`GET /api/datasets` lists available and selected sources.
When selection is enabled, `POST /api/datasets/select` with
`{"datasets":["<id>","<id>"]}` replaces the shared browser view atomically; a failed
load keeps the previous view.
Selection changes apply to every client using that server.

Keep typed IDs, such as `person:example`, as entity identity rather than display names.
Namespace caches by server, `dataset`, `graph`, and `load_id`, with request parameters
included in each cache key.
On `graph.loaded`, invalidate and refetch metadata and data.
On reconnect, compare the SSE `hello` stamp; poll `/api/meta` if events are unavailable.
Separate API requests do not share a pinned transaction.
For a consistent multi-request screen, compare metadata before and after fetching and
retry if the load changed.

`kb_digest` hashes only the node and edge exports, excluding full record payloads and
schemas. `load_id` identifies one runtime import, including repeated imports of the same
exports. Use a dataset Git commit or release as the durable content version.

The existing
[Swift client](../db/clients/swift/Sources/ParaverseGraphClient/GraphClient.swift) is a
SwiftPM package using Foundation `URLSession` for named queries.
Other browser API routes require additional client methods.

## Keep Writes and Hosting Separate

Store user state in an application-owned store.
Correct catalog data through the dataset records and rebuild; direct writes to the
generated graph would be replaced on reload.

The current server binds to loopback, restricts Host headers, and has no authentication
or API versioning. It is not a hosted production service.
A hosted app needs an authenticated HTTPS backend and a private database connection;
that deployment boundary remains to be implemented.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
