# Patch the Conference Demo

Paraverse is a project for the
[Patch the Conference Hackathon](https://www.wemakedevs.org/hackathons/ptc?utm_source=luma),
hosted by Bright Data and WeMakeDevs ([event listing](https://luma.com/ptc)). It
connects conference sessions, speakers, organizations and public professional work so an
attendee can explore a topic, follow a speaker’s projects, and see how people and
sessions are connected.

The first dataset covers GitHub Universe.
Records keep source citations, and the graph exposes the relationships between them.
The [KB readiness review](project/research/review-2026-10-24-kb-readiness.md) records
the current dataset audit and the remaining work needed for a reproducible demo.

## How the Tools Fit

### Bright Data: acquire and enrich public sources

Bright Data supplies structured web data for the GitHub Universe dataset’s enrichment
pipeline. The collector submits profile URLs to the Web Scraper API, polls each snapshot
until it is ready, and downloads the results.
It supports LinkedIn profiles and company pages, X profiles, and posts from those
accounts.

The pipeline saves snapshots with their identifiers and a source manifest, then builds
knowledge-base records from those saved inputs.
Profile enrichment keeps the source URL for the facts it adds.
This separates data collection from the graph demo: browsing a prepared KB does not
require a Bright Data API call.
The dataset and its pipeline belong in
[universe2026-md](https://github.com/jlevy/universe2026-md); check the readiness review
for what the selected public revision contains.

The [data policy](data-policy.md) applies to collected data, derived records and demo
examples. Only public professional sources are eligible, and collected payloads need
review before publication.

### FalkorDB: connect and query the knowledge base

The [`db/` component](../db/README.md) loads the KB’s exported nodes and edges into
FalkorDB. FalkorDBLite runs the database locally, and named Cypher queries expose
connections such as a person’s sessions and repositories, shared expertise, and paths
between entities.

The read-only browser renders tables and record views from the dataset’s compiled
schemas.
Following links between records shows the same relationships exposed by the JSON
API and CLI. The
[graph architecture](project/architecture/arch-2026-10-24-graph-database.md) and
[browser architecture](project/architecture/arch-2026-10-24-kb-browser.md) describe the
implementation.

### Qodo: review the implementation

Qodo reviews Paraverse pull requests.
The repository’s [Qodo configuration](../.pr_agent.toml) includes its public data policy
and requires the data review checklist on changes that add or alter data, fixtures or
doc examples. [Contributor instructions](../AGENTS.md#qodo-code-review) also describe
optional local review with the Qodo CLI before opening a PR.

Examples of Qodo reviewing real work are the
[review on PR #6](https://github.com/jlevy/paraverse/pull/6#pullrequestreview-5639989300)
and the
[review on PR #8](https://github.com/jlevy/paraverse/pull/8#pullrequestreview-5639990820).
Use the current PR discussion and diff to show a finding and its disposition; the
presence of a review alone does not mean every finding has been resolved.

## Run the Graph Demo

You need uv and a built KB. A usable dataset includes entity records, `kb/_graph/`
exports and `kb/_schemas/` compiled schemas.
A submodule revision without those artifacts cannot be loaded; check the
[readiness review](project/research/review-2026-10-24-kb-readiness.md) for the current
public dataset status.

From the repository root, initialize the dataset checkout:

```bash
git submodule update --init
```

Install the graph component and list available datasets:

```bash
cd db
make install
make datasets
```

When the default `universe2026-md` dataset contains its built KB, load and serve it:

```bash
make load
make serve
```

Open [the local browser](http://127.0.0.1:8766/). For another built dataset, use
`make load serve DATASET=<name>` or `make load serve KB=../path/to/kb`. See the
[component README](../db/README.md#quick-start) for the command reference and validation
commands.

## Demo Flow

1. **Start with a source.** Open a public source citation from a KB record and show how
   the record retains its provenance.
   For a Bright Data example, pair an enriched record with its snapshot identifier and
   source manifest.
2. **Browse the connected records.** Find a session, follow its speaker, then explore
   the speaker’s organization and public software work where the dataset has those
   links.
3. **Explain a graph result.** From `db/`, list the query catalog with
   `UV_CONFIG_FILE=uv.toml uv run paraverse-graph queries`. Choose entity IDs from the
   loaded dataset and run `neighborhood`, `similar_people` or `connecting_paths`; show
   the relationships behind the result.
   The [CLI examples](../db/README.md#commands) show the parameter syntax.
4. **Show the review workflow.** Open a Qodo review linked above and its PR diff, then
   explain the finding, its disposition and any work still outstanding.

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
