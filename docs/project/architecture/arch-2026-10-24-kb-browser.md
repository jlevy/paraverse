# Architecture: Knowledge Base Browser

**Date:** 2026-10-24 (last updated 2026-10-24)

**Author:** Joshua Levy, with LLM assistance

**Status:** In Review

## Overview

The KB browser is a read-only, administrative view of a whole conference knowledge base,
served from the [graph database](arch-2026-10-24-graph-database.md).
Every kind of entity (sessions, people, profiles, organizations, repositories, accounts,
rooms, taxonomy terms, pages and the rest) gets the same kind of table, with sorting,
filtering and paging.
Every record gets the same detail view.
Every reference is a link with a hover preview, and relationships link the tables to
each other.

It is one small component inside `db/`:

- a Python server (Starlette and uvicorn) with a JSON API and server-sent events
- a static front end of plain ES modules and CSS, with no build step

It runs with `paraverse-graph serve` at <http://127.0.0.1:8766/> and embeds in a browser
tab, an iframe or a WebKit web view.

## Goals and Non-Goals

### Goals

- **Show everything.** Every node kind and every field of every record is reachable.
  Nested values (time slots, affiliations, claims and their evidence, sponsorship,
  sources) are rendered, not hidden in JSON.
- **One schema-driven model.** Columns, field order, labels, descriptions, nested shapes
  and reference targets come from the KB’s compiled softschema JSON Schemas and from the
  graph. There is no per-kind UI code beyond a small table of default columns, so a new
  kind or field appears with no front-end change.
- **Relational navigation.** References are link chips with hover popovers; each record
  lists its outgoing and incoming relationships by type; each table can be filtered by a
  relationship, such as “sessions presented by person X” or “sessions about term Y”.
- **Consistent visuals.** One small design vocabulary (tokens, table, chip, card,
  popover, badge) in light and dark.
- **Easy to load and embed.** No build step and no CDN at runtime; deep-linkable URLs;
  an embed mode without chrome.
- **Live.** When the graph is reloaded, open browsers are told over server-sent events
  and refresh the current view.
- **Review built in.** Data-quality checks run as named queries and appear as a Review
  table whose rows link to the entities.

### Non-Goals

- Editing data. The KB is generated; corrections go into the conference’s `curation/` and
  a rebuild.
- Authentication, multi-user hosting or public deployment.
  The server binds to loopback.
- A graph drawing as the primary view.

## System Context

```text
vendor/universe2026-md/kb/        ──paraverse-graph load──►  FalkorDB graph `universe2026_md`
  artifacts, _graph/, _schemas/                              entity nodes and relationships
                                                             (:Schema) nodes, one per kind
                                                             (:GraphMeta); PUBLISH graph.loaded
                                                                    │
                           Starlette app (uvicorn) ◄────────────────┘
                             /api/meta  /api/overview  /api/schema/<kind>  /api/rows/<kind>
                             /api/entity/<id>  /api/card/<id>  /api/search
                             /api/review[/<check>]  /api/query/<name>  /api/events (SSE)
                             /  and  /static/*   (no-build ES modules and CSS)
                                                                    │
                           browser tab · iframe · WebKit web view (embed=1)
```

All data comes from FalkorDB at request time.
The server reads nothing from `vendor/universe2026-md/kb/` directly, so the same server
works against a remote FalkorDB loaded elsewhere.

## Design

### Data in FalkorDB

The browser relies on three things the loader stores besides the entities:

- **`(:Schema)` nodes,** one per kind, with the compiled JSON Schema and a flattened
  field list. Each field records its name, title, description, JSON type, whether it is
  required, whether it is a reference and to which kinds, and its nested definition if
  any.
- **`(:GraphMeta)`,** with the KB digest, the load time and relationship statistics
  (`kind -[TYPE]-> kind` with counts), so the API can describe relationship columns
  without scanning the graph on each request.
- **A `graph.loaded` message** published on a Redis channel after each successful swap,
  with the KB digest and load time.

### Overview and Data Transparency

The default route and the sidebar’s Overview entry open a welcome summary.
The first summary renders from `/api/meta`; `/api/overview` fills in entity and
relationship inventories, citations by source provider, retrieval dates, exact
enrichment coverage, event editions and people inclusion bases.
Data-quality checks load separately so their queries do not delay the inventory.
Section links, entity-table links and review links provide a path from aggregates to
records. Loading failures remain visible with a retry.

The overview reads entity JSON payloads and graph metadata, and caches the aggregation
for one graph load. Reloads invalidate it alongside schemas and review results.
Its response includes load identity so the front end can reject a response for an older
load. A load change during aggregation requires a retry rather than a mixed summary.
Quality results carry the same captured identity and retry computations that span a
reload. Event dates retain their source timezone offsets so UTC conversion cannot change
their displayed calendar dates.

Citations count direct source entries in each entity payload, not independently verified
facts or raw collection snapshots.
An entity can cite several providers, and derived entities may inherit provenance
through their parent.
Missing or malformed metadata is reported explicitly.
Coverage separates populated fields from stale bios and explicit true/false/unknown
fetch states.
Review counts may overlap across checks; truncated checks are lower bounds.
Load time and source retrieval time remain distinct, and the export digest identifies
node/edge exports rather than every payload and schema.

### API

Every endpoint is a read-only JSON GET.

| Endpoint | Returns |
| --- | --- |
| `GET /api/overview` | Load identity, graph inventories, source-provider citation counts and retrieval dates, enrichment coverage, event editions and inclusion bases; cached per load |
| `GET /api/meta` | The graph, KB digest and load time; node and edge totals; kinds grouped for navigation with titles, descriptions and counts; relationship counts |
| `GET /api/schema/<kind>` | The kind’s title, description and contract; its fields and nested definitions; default columns; and its relationships with direction, type, target kinds and count |
| `GET /api/rows/<kind>` | A page of rows: `{kind, columns, total, offset, limit, sort, order, rows: [{id, name, cells}]}`. Takes `offset`, `limit`, `sort`, `order`, `q`, `cols`, `f.<field>=<value>` and `rel=<in\|out>:<TYPE>:<id>`. |
| `GET /api/entity/<id>` | The full payload (`doc`), properties, names for every reference in it, and relationships grouped by type and direction, with up to 50 items per group |
| `GET /api/card/<id>` | A compact card for link popovers: name, kind, labels, title, image and a few fields |
| `GET /api/search?q&kinds&limit` | Full-text hits across every kind, with snippets and scores |
| `GET /api/review`, `GET /api/review/<check>` | The data-quality checks with name, title, severity, area, description and count, sorted by severity; one check adds its rows (`id`, `name`, `detail`). Results are cached per graph load; the list includes its captured load identity. |
| `GET /api/query/<name>` | The named query catalog |
| `GET /api/events` | Server-sent events: `hello` on connect, `graph.loaded` after each reload, `resync` after an overflow, and heartbeats |

- **Cells** are a scalar or list; `{refs: [{id, name, kind}]}` for references;
  `{nested, count, preview}` for nested shapes; or `{items, count}` for relationship
  columns.
- **Paging** is server-side, with a default `limit` of 100 and a maximum of 2,000. The
  browser asks for 2,000 rows, so every current kind fits on one page, and the pager
  appears only beyond that.
- **Table search.** `q` is a case-insensitive substring match on `search_text`, which is
  predictable for an admin filter.
  Global search uses the full-text index, with user text sanitized for its syntax.
- **Filters.** `f.<field>` matches scalars by equality and lists by membership.
  Reference and nested fields are filtered through `rel=`: `in:PRESENTS:person:x`
  returns the sessions that `person:x` presents.
- **Errors** are JSON `{error}`: 400 for bad input, 404 for unknown IDs and routes, 503
  for an unloaded graph or a query timeout, and 421 for a foreign `Host` header.

### Front End

Plain ES modules and CSS served from the package’s `web/` directory, with no bundler, no
npm runtime dependency and no CDN.

- **Shell.** A sidebar lists kinds grouped as Program, People, Organizations, Code,
  Content and Taxonomy, with counts.
  The top bar has global search, a Review link, and a badge with the KB digest and load
  time that flashes when the graph reloads.
- **Routing** uses the URL hash, so every view has a deep link:
  `#/t/<kind>?sort=&order=&q=&rel=&f.x=` for a table, `#/e/<id>` for a record,
  `#/overview` (also `#/`) for the welcome summary, `#/review` and `#/review/<check>`
  for review checks, and `#/search?q=` for search.
- **Table view.** A sticky header, sortable columns, a column picker (any schema field
  or relationship column), a filter box, chips for active relationship filters, and
  paging. Cells render by type: text and numbers, booleans as badges, URLs as external
  links, images as thumbnails, references as entity chips, and relationship columns as
  up to three chips plus a count.
  Clicking a row opens the record.
- **Record view.** A header with name, kind, `id`, labels and source path, then: fields
  in schema order, with nested objects as definition lists, lists of objects as
  sub-tables using their definition’s fields, references as chips, and long text as
  escaped Markdown with links only; outgoing and incoming relationships, one compact
  table per type, each linking to the filtered table; sources with links; and the raw
  payload as JSON.
- **Popovers.** Hovering or focusing an entity chip shows its card in a popover, cached
  for the session; clicking navigates.
- **Embed mode.** `?embed=1` hides the sidebar and top bar, keeps the routes, and posts
  `{type: "paraverse-kb:navigate", id}` to the parent window, or to the WebKit message
  handler `paraverseKb` when one exists, so the host page can react.
- **Theme.** CSS custom properties with light and dark through `prefers-color-scheme`,
  overridable with a `data-theme` attribute.
  A test fails if a color literal appears in the stylesheet outside the base `:root`
  tokens, and dark themes must be pure token remaps.

The visual vocabulary (design tokens, table chrome, chips, filter chips, search palette
and icons) follows the web viewers of [tbd](https://github.com/jlevy/tbd) and
metabrowser. Borrowed blocks carry a one-line comment naming their source.
The router, record view, popovers and keyboard handling are written for this browser.

### Server

- **App.** An app factory returns a Starlette app for a given graph, run with uvicorn by
  `paraverse-graph serve`, which binds to 127.0.0.1 and checks the `Host` header.
- **Events.** One Redis pub/sub subscriber task per process fans out to per-client
  queues, with heartbeats and disconnect handling; the front end reconnects with
  backoff.
- **`--watch`** watches `vendor/universe2026-md/kb/_graph/stats.json` and the
  `vendor/universe2026-md/kb/` directory, reloads the graph, and the published event
  reaches every client.

### Review Checks

Data-quality checks are curated in the `review` module, each with a name, title,
severity, area, description and read-only Cypher that returns `id`, `name` and `detail`,
so every row links to its entity.
They appear in `#/review` with counts and a severity badge.
[review-2026-10-24-universe-kb-data-quality.md](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/review-2026-10-24-universe-kb-data-quality.md)
describes the checks and the classes of defects they find.

## Trade-offs and Alternatives

### A Generic Browser Instead of Per-Kind Pages

**Chosen approach:** one table renderer and one record renderer driven by the schema
nodes.

**Alternatives considered:**
- Hand-built pages per kind: rejected because they fall behind as the contracts gain
  fields and kinds.

**Rationale:** the compiled schemas already name every field, its type and its reference
targets, which is enough to render any record.

### No Build Step

**Chosen approach:** plain ES modules and CSS, system fonts, a few static files.

**Alternatives considered:**
- A bundled single-page app: rejected because it adds a toolchain and a build artifact
  for a small admin tool.

**Rationale:** the browser loads fast, embeds anywhere and has nothing to rebuild.

### Live Updates Through Redis

**Chosen approach:** the loader publishes on Redis pub/sub, and the server relays it as
server-sent events.

**Alternatives considered:**
- Polling `/api/meta`: workable, but slower to notice a reload and noisier.

**Rationale:** FalkorDB is Redis, so pub/sub is already there.

### FalkorDB Browser for Ad Hoc Work

The stock FalkorDB Browser, pointed at the same database through a normal FalkorDB
server, remains the tool for ad hoc Cypher.
The KB browser covers browsing, navigation and review, which need the KB’s schemas.

## Security Considerations

- Read-only GET endpoints only, each query with `GRAPH.RO_QUERY` and a 4-second timeout.
- Loopback binding and a `Host` header check (421 for a foreign host).
- Labels, types and property names are checked against the schema nodes, the stored
  relationship statistics and a strict identifier pattern before they reach Cypher;
  values are always parameters.
- Long text is rendered as escaped Markdown with links only, because every free-text
  field comes from public sources and is untrusted.

## Operational Concerns

### Testing

- **API** (pytest, the real KB in a temporary embedded FalkorDB): every kind has a
  schema and a non-empty first page; `total` equals the kind’s count; sort and paging
  are stable; `rel=` returns only linked rows; every reference in `entity` resolves; a
  card exists for every kind; search finds a known title; unknown kinds and fields
  return 400; a foreign `Host` header returns 421.
- **Review:** every check runs and returns its three columns.
- **Events:** a published message reaches a connected client within a timeout.
- **Front end:** a scripted pass in a real browser over every kind’s table and a sample
  record per kind, with no console errors, checking popovers, deep links, embed mode and
  dark mode.

### Deployment

Local only:

```bash
make -C db install
make -C db load
make -C db serve
```

## Open Questions

- Should the browser also show `vendor/universe2026-md/kb/_graph/coverage.json` (field
  coverage per kind) as a view?
  It is cheap and useful for review.
- Should the browser be packaged apart from `paraverse_graph`, so that other
  conferences’ KBs can reuse it without the graph tooling?

## References

- [Architecture: conference graph database](arch-2026-10-24-graph-database.md)
- [Review: KB data quality](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/review-2026-10-24-universe-kb-data-quality.md)
- `db/README.md`
- [Starlette](https://www.starlette.io/), [uvicorn](https://www.uvicorn.org/)
- [tbd](https://github.com/jlevy/tbd)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
