# Paraverse Docs

Start with the data policy; it sets what this public repository may contain.

- [Data policy](data-policy.md): what may and may not be committed, how generated text
  is handled, and how removal requests work.
- [Hackathon demo](hackathon-demo.md): Paraverse at Patch the Conference, the Bright
  Data, FalkorDB and Qodo integrations, and the demo flow.
- [KB readiness review](project/research/review-2026-10-24-kb-readiness.md): the current
  dataset audit, reproducibility gaps and prerequisites for a complete demo.

## Graph Database and Browser

These docs cover `db/`, which loads a conference knowledge base into FalkorDB.

Architecture, describing how the system works now:

- [Conference graph database](project/architecture/arch-2026-10-24-graph-database.md):
  how `db/` maps the KB into FalkorDB, loads it safely, and serves named read-only
  queries.
- [KB browser](project/architecture/arch-2026-10-24-kb-browser.md): the read-only,
  schema-driven browser, its JSON API and live updates.

Plans:

- [Graph catalog extensions and hardening](project/specs/active/plan-2026-10-24-graph-catalog-and-hardening.md)
  (active): topic queries, joinable properties, remote loading, better ranking, and
  readiness for a second conference.
- [Conference KB in FalkorDB](project/specs/done/plan-2026-10-24-conference-kb-in-falkordb.md)
  (done): the spike that chose the graph mapping.
- [KB browser](project/specs/done/plan-2026-10-24-kb-browser.md) (done): the plan that
  built the schema-driven browser.

## The GitHub Universe Knowledge Base

The first KB, its crawl pipeline and their docs live in
[jlevy/universe2026-md](https://github.com/jlevy/universe2026-md), which Paraverse
mounts as a git submodule at `vendor/universe2026-md/`; the graph reads
`vendor/universe2026-md/kb/`. Clone with `git clone --recurse-submodules`, or run
`git submodule update --init` in an existing clone.

- [Conference knowledge base](https://github.com/jlevy/universe2026-md/blob/main/docs/project/architecture/arch-2026-10-24-conference-kb.md):
  the crawl, enrichment and build pipeline, the softschema data model, the people model,
  and how the build enforces its data policy.
- [GitHub Universe knowledge graph](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/research-2026-10-23-universe-knowledge-graph.md):
  where GitHub Universe’s data lives, what each source exposes, and worked examples.
- [Enrichment sources survey](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/research-2026-10-24-enrichment-sources-survey.md):
  further public sources for people’s interests and past work.
- [KB data-quality review](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/review-2026-10-24-universe-kb-data-quality.md):
  defects that pass structural validation, and the checks the browser runs for them.
- [Simulated conference avatars](https://github.com/jlevy/universe2026-md/blob/main/docs/project/research/research-2026-10-24-simulated-conference-avatars.md):
  what the KB can support about people, and the consent rules that come first.
- [Deeper enrichment sources](https://github.com/jlevy/universe2026-md/blob/main/docs/project/specs/active/plan-2026-10-24-deeper-enrichment-sources.md)
  and
  [KB hardening](https://github.com/jlevy/universe2026-md/blob/main/docs/project/specs/active/plan-2026-10-24-kb-hardening.md)
  (active plans), and the
  [Universe knowledge base plan](https://github.com/jlevy/universe2026-md/blob/main/docs/project/specs/done/plan-2026-10-24-universe-knowledge-base.md)
  (done).

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
