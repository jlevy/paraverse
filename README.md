# Paraverse

Paraverse is being built as part of the
[Patch the Conference Hackathon](https://www.wemakedevs.org/hackathons/ptc?utm_source=luma),
hosted by Bright Data and WeMakeDevs ([event listing](https://luma.com/ptc)).

Paraverse assembles the public record of a conference into a knowledge base you can
browse. It covers sessions, speakers, people, organizations, repositories and packages.
Each entity has a structured YAML record, stored in a YAML file or as Markdown
frontmatter, so different editions and different conferences line up side by side.
Each record cites the sources it was built from.

The first conference covered is GitHub Universe.

## Hackathon Demo

The project demonstrates three tools across the path from public sources to a connected
conference knowledge base:

| Tool | Role in Paraverse |
| --- | --- |
| Bright Data | Acquires public professional profile and organization data for the dataset’s enrichment pipeline, with source snapshots and provenance. |
| FalkorDB | Loads the knowledge base as a graph and runs Cypher queries behind the browser, API and CLI. |
| Qodo | Reviews pull requests against code quality rules and the repository’s public data policy. |

See the [hackathon demo guide](docs/hackathon-demo.md) for the integration details,
review evidence, dataset prerequisites and demo flow.

## Layout

- `db/`: paraverse-graph, which loads a knowledge-base dataset into FalkorDB and serves
  it through a read-only web browser, a JSON API and a CLI, with a Swift client in
  `db/clients/swift/`. It loads datasets using the supported entity kinds and
  graph-export format.
- `vendor/`: datasets mounted as git submodules, one per conference.
  `vendor/universe2026-md` is the GitHub Universe dataset
  ([universe2026-md](https://github.com/jlevy/universe2026-md)): softschema records,
  schemas and the crawl pipeline.

## Getting the Data

The datasets are git submodules.
Clone with `git clone --recurse-submodules`, or run `git submodule update --init` in an
existing clone. The selected dataset revision must include a built `kb/` tree; see the
[demo prerequisites](docs/hackathon-demo.md#run-the-graph-demo) before loading it.

## Data Policy

Everything in this repository is public.
Read the [data policy](docs/data-policy.md) before adding or changing data.
To have your data removed, open an issue or contact a maintainer.

## Docs

Design docs, research and plans are indexed in [docs/README.md](docs/README.md).

## Contributing

Agents and humans follow [AGENTS.md](AGENTS.md).
Work is tracked with [tbd](https://github.com/jlevy/tbd), and records are validated with
[softschema](https://github.com/jlevy/softschema).

## License

[MIT](LICENSE)

<!-- This document follows common-doc-guidelines.md.
See github.com/jlevy/practical-prose and review guidelines before editing.
-->
