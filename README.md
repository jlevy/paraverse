# Paraverse

Paraverse assembles the public record of a conference into a knowledge base you can
browse.
It covers sessions, speakers, people, organizations, repositories and packages.
Every kind of entity is stored as plain YAML records in one shared format, so different
editions and different conferences line up side by side.
Each record cites the sources it was built from.

The first conference covered is GitHub Universe.

## Layout

- `db/`: paraverse-graph, which loads a knowledge-base dataset into FalkorDB and serves it
  through a read-only web browser, a JSON API and a CLI, with a Swift client in
  `db/clients/swift/`.
  It can load any dataset in the same softschema format.
- `vendor/`: datasets mounted as git submodules, one per conference.
  `vendor/universe2026-md` is the GitHub Universe dataset
  ([universe2026-md](https://github.com/jlevy/universe2026-md)): softschema records,
  schemas and the crawl pipeline.

## Getting the Data

The datasets are git submodules.
Clone with `git clone --recurse-submodules`, or run `git submodule update --init` in an
existing clone.

## Data Policy

Everything in this repository is public.
Read the [data policy](docs/data-policy.md) before adding or changing data.
To have your data removed, open an issue or contact a maintainer.

## Docs

Design docs, research and plans are indexed in [docs/README.md](docs/README.md).

## Contributing

Agents and humans follow [AGENTS.md](AGENTS.md).
Work is tracked with [tbd](https://github.com/jlevy/tbd), and records are validated
with [softschema](https://github.com/jlevy/softschema).

## License

[MIT](LICENSE)
