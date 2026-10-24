"""
`paraverse-graph`: load a knowledge base dataset into FalkorDB, query it, and serve the
knowledge base browser.

Data goes to stdout (text tables, or JSON with `--format json`); progress and
errors go to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from redis.exceptions import RedisError
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich_argparse import RichHelpFormatter

from paraverse_graph.browser import create_app, redis_subscriber
from paraverse_graph.connection import engine_version, graph_exists, open_db
from paraverse_graph.datasets import (
    KB_ENV,
    MISSING_KB_HINT,
    Dataset,
    list_datasets,
    resolve_dataset,
)
from paraverse_graph.kb import DEFAULT_DATASET, VENDOR_DIR, KbError, build_snapshot, load_kb
from paraverse_graph.loader import LoadError, load_graph
from paraverse_graph.mapping import MappingError
from paraverse_graph.queries import CATALOG, QueryError, run_query
from paraverse_graph.selection import DatasetSelection, SelectionError

DEFAULT_PORT = 8766

out = Console()
err = Console(stderr=True)


class CLIError(RuntimeError):
    """A failure to report without a traceback (exit code 1)."""


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (CLIError, KbError, LoadError, MappingError, SelectionError) as e:
        # Escaped, since a parser error can quote text that looks like markup.
        err.print(f"[bold red]error:[/bold red] {escape(str(e))}")
        return 1
    except QueryError as e:
        err.print(f"[bold red]error:[/bold red] {escape(str(e))}")
        return 2
    except KeyboardInterrupt:
        return 130


def _parser() -> argparse.ArgumentParser:
    output = argparse.ArgumentParser(add_help=False)
    output.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")

    common = argparse.ArgumentParser(add_help=False, parents=[output])
    common.add_argument(
        "--db", type=Path, help="Embedded database file (default: db/.data/paraverse-graph.rdb)."
    )
    common.add_argument(
        "--url", help="Remote FalkorDB URL, such as redis://localhost:6379. Overrides --db."
    )
    source = common.add_mutually_exclusive_group()
    source.add_argument("--kb", type=Path, metavar="DIR", help="KB directory to use.")
    source.add_argument(
        "--dataset",
        metavar="NAME",
        help=f"Dataset whose KB is at {VENDOR_DIR}/NAME/kb, found from the working directory "
        f"(default: ${KB_ENV} if set, else {DEFAULT_DATASET}).",
    )
    common.add_argument(
        "--graph",
        help="Graph name (default: derived from the dataset name, such as universe2026_md "
        "for universe2026-md).",
    )

    parser = argparse.ArgumentParser(
        prog="paraverse-graph", description=__doc__, formatter_class=RichHelpFormatter
    )
    commands = parser.add_subparsers(required=True, metavar="COMMAND")

    load = commands.add_parser(
        "load",
        parents=[common],
        formatter_class=RichHelpFormatter,
        help="Rebuild the graph from the knowledge base.",
    )
    load.add_argument(
        "--validate",
        action="store_true",
        help="Validate every artifact with softschema first and load nothing if any fails "
        "(adds about 40 s on the full KB).",
    )
    load.set_defaults(handler=_load)

    datasets = commands.add_parser(
        "datasets",
        parents=[output],
        formatter_class=RichHelpFormatter,
        help=f"List the datasets checked out under {VENDOR_DIR}/.",
    )
    datasets.set_defaults(handler=_datasets)

    queries = commands.add_parser(
        "queries",
        parents=[common],
        formatter_class=RichHelpFormatter,
        help="List the named queries.",
    )
    queries.set_defaults(handler=_queries)

    query = commands.add_parser(
        "query",
        parents=[common],
        formatter_class=RichHelpFormatter,
        help="Run a named query: `paraverse-graph query similar_people id=person:april-leonard`.",
    )
    query.add_argument("name", help="Query name (see `paraverse-graph queries`).")
    query.add_argument("params", nargs="*", metavar="KEY=VALUE", help="Query parameters.")
    query.set_defaults(handler=_query)

    cypher = commands.add_parser(
        "cypher",
        parents=[common],
        formatter_class=RichHelpFormatter,
        help="Run ad hoc read-only Cypher, for exploration.",
    )
    cypher.add_argument(
        "text", help="A Cypher query. Runs with GRAPH.RO_QUERY, so it cannot write."
    )
    cypher.set_defaults(handler=_cypher)

    serve = commands.add_parser(
        "serve",
        parents=[common],
        formatter_class=RichHelpFormatter,
        help="Serve the API and graph explorer on loopback.",
    )
    serve.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})."
    )
    serve.add_argument(
        "--watch",
        action="store_true",
        help="Reload the graph whenever a KB build replaces kb/ or rewrites kb/_graph/stats.json.",
    )
    serve.add_argument("--open", action="store_true", help="Open the browser once it is ready.")
    serve.add_argument(
        "--include-kb",
        action="append",
        default=[],
        metavar="NAME=DIR",
        help="Also offer a named KB directory in the browser's dataset selector; repeatable.",
    )
    serve.add_argument(
        "--select-all",
        action="store_true",
        help="Initially combine all available datasets in the browser.",
    )
    serve.set_defaults(handler=_serve)
    return parser


def _target(args: argparse.Namespace) -> tuple[Dataset, str]:
    """
    The dataset the options name, and its graph unless `--graph` overrides it.
    """
    dataset = resolve_dataset(args.kb, args.dataset)
    return dataset, args.graph or dataset.graph


def _open_graph(
    args: argparse.Namespace, graph_name: str, *, must_exist: bool = True
) -> tuple[Any, Any]:
    db = open_db(args.db, args.url)
    if must_exist and not graph_exists(db, graph_name):
        raise CLIError(
            f"graph `{graph_name}` not found; run `paraverse-graph load` first, "
            "with the same --dataset, --kb or --graph"
        )
    return db, db.select_graph(graph_name)


def _validate_kb(dataset: Dataset, kb_root: Path) -> None:
    from paraverse_graph.validation import validate_artifacts

    err.print(f"Validating dataset `{dataset.name}` at {kb_root} with softschema …")
    report = validate_artifacts(kb_root)
    if not report.checked:
        raise CLIError("No artifacts found in the selected KB; nothing was loaded.")
    if not report.ok:
        # Every failed path, one per line, printed as is: error text is not markup.
        for problem in report.problems:
            err.print(f"  {problem.line()}", markup=False, highlight=False, soft_wrap=True)
        raise CLIError(
            f"{len(report.problems)} of {report.checked:,} artifacts failed validation; "
            "nothing was loaded."
        )
    contracts = ", ".join(f"{c.split(':')[-1]} {n:,}" for c, n in sorted(report.contracts.items()))
    err.print(f"All {report.checked:,} artifacts are valid ({contracts}).")


def _load(args: argparse.Namespace) -> int:
    dataset, graph_name = _target(args)
    kb_root = dataset.require_kb()
    validated_snapshot = build_snapshot(kb_root) if args.validate else None
    if args.validate:
        _validate_kb(dataset, kb_root)
        if build_snapshot(kb_root) != validated_snapshot:
            raise KbError("KB changed while reading; retry after the build finishes")
    err.print(f"Reading dataset `{dataset.name}` from {kb_root} …")
    kb = load_kb(kb_root)
    if validated_snapshot is not None and kb.snapshot != validated_snapshot:
        raise KbError("KB changed while reading; retry after the build finishes")
    db, _ = _open_graph(args, graph_name, must_exist=False)
    err.print(f"Loading {len(kb.nodes):,} nodes and {len(kb.edges):,} edges into `{graph_name}` …")
    report = load_graph(db, kb, graph_name)
    if args.format == "json":
        print(json.dumps(report.as_dict(), indent=2))
        return 0
    table = Table("kind", "nodes", title=f"{graph_name} (FalkorDB {report.engine})")
    for kind, count in report.nodes_by_kind.items():
        table.add_row(kind, f"{count:,}")
    out.print(table)
    out.print(
        f"Loaded {report.node_total:,} nodes and {report.edge_total:,} relationships "
        f"({len(report.edges_by_relation)} types) in {report.seconds:.2f}s; KB {report.kb_digest}."
    )
    return 0


def _datasets(args: argparse.Namespace) -> int:
    found = list_datasets()
    if DEFAULT_DATASET not in {d.name for d in found}:
        err.print(
            f"The default dataset is not at {VENDOR_DIR}/{DEFAULT_DATASET}/kb; {MISSING_KB_HINT}."
        )
    if args.format == "json":
        rows = [
            {
                "name": d.name,
                "graph": d.graph,
                "kb": str(d.kb_root),
                "default": d.name == DEFAULT_DATASET,
            }
            for d in found
        ]
        print(json.dumps(rows, indent=2))
        return 0
    if found:
        table = Table("dataset", "graph", "kb")
        for d in found:
            default = " (default)" if d.name == DEFAULT_DATASET else ""
            table.add_row(
                escape(d.name) + default, d.graph, escape(os.path.relpath(d.require_kb()))
            )
        out.print(table)
    return 0


def _queries(args: argparse.Namespace) -> int:
    described = [q.describe() for q in CATALOG.values()]
    if args.format == "json":
        print(json.dumps(described, indent=2))
        return 0
    table = Table("name", "parameters", "description")
    for q in described:
        params = ", ".join(
            p["name"] + ("" if p["default"] is None else f"={p['default']}") for p in q["params"]
        )
        table.add_row(q["name"], params, q["description"])
    out.print(table)
    return 0


def _query(args: argparse.Namespace) -> int:
    params: dict[str, str] = {}
    for item in args.params:
        key, sep, value = item.partition("=")
        if not sep:
            raise QueryError(f"parameters are KEY=VALUE, got `{item}`")
        params[key] = value
    _, graph = _open_graph(args, _target(args)[1])
    _print_result(run_query(graph, args.name, params), args.format)
    return 0


def _cypher(args: argparse.Namespace) -> int:
    from paraverse_graph.results import result_json

    _, graph = _open_graph(args, _target(args)[1])
    _print_result(result_json(graph.ro_query(args.text)), args.format)
    return 0


def _serve(args: argparse.Namespace) -> int:
    import webbrowser

    import uvicorn

    dataset, graph_name = _target(args)
    selection_requested = bool(args.include_kb or args.select_all)
    offer_selection = selection_requested or not (args.graph or args.url)
    sources = {item.name: item.require_kb() for item in list_datasets()} if offer_selection else {}
    if (
        offer_selection
        and dataset.kb_root is not None
        and (dataset.kb_root / "_graph/nodes.jsonl").is_file()
    ):
        sources[dataset.name] = dataset.require_kb()
    for value in args.include_kb:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            raise CLIError("--include-kb requires NAME=DIR")
        resolve_dataset(name=name)  # Validate the registry name, never accept a path as a name.
        sources[name] = Dataset(name, Path(path).expanduser()).require_kb()
    selection = None
    if sources and (dataset.name in sources or args.select_all):
        db, _ = _open_graph(args, graph_name, must_exist=False)
        graph_name = f"{graph_name}__browser_{args.port}"
        selection = DatasetSelection(db, sources, graph_name)
        initial = sorted(sources) if args.select_all else [dataset.name]
        selection.select(initial)
        if args.url is None:
            # Retain the completed view across immediate app restarts. A full
            # disk must not stop an otherwise usable in-memory browser.
            try:
                db.connection.save()
            except RedisError:
                err.print("Warning: the browser cache could not be saved; continuing in memory.")
        graph = db.select_graph(graph_name)
        kb_root = None
    else:
        kb_root = dataset.require_kb() if args.watch else None
        db, graph = _open_graph(args, graph_name)
    app = create_app(
        graph,
        subscribe=redis_subscriber(db.connection, graph_name),
        selection=selection,
    )
    url = f"http://127.0.0.1:{args.port}/"
    stop = threading.Event()
    if selection is not None:
        threading.Thread(target=watch_selection, args=(selection, stop), daemon=True).start()
    elif kb_root is not None:
        threading.Thread(
            target=watch_kb,
            args=(kb_root, stop, lambda: _reload(db, kb_root, graph_name)),
            kwargs={"seen": kb_signature(kb_root)},
            daemon=True,
        ).start()
    if args.open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    err.print(
        f"Serving `{graph_name}` (FalkorDB {engine_version(db)}) at [link]{url}[/link]"
        + (f" — watching {escape(str(kb_root))}" if kb_root is not None else "")
        + " — Ctrl-C to stop."
    )
    try:
        uvicorn.run(
            app, host="127.0.0.1", port=args.port, log_level="warning", timeout_graceful_shutdown=0
        )
    finally:
        stop.set()
    return 0


def watch_selection(selection: DatasetSelection, stop: threading.Event) -> None:
    """Refresh the currently selected view when one of its source builds changes."""
    while not stop.wait(5):
        try:
            selection.refresh_if_changed()
        except (SelectionError, KbError, LoadError) as exc:
            err.print(f"[bold red]reload failed:[/bold red] {escape(str(exc))}")


def _reload(db: Any, kb_root: Path, graph_name: str) -> None:
    """
    Rebuild the graph from the KB. The loader publishes `graph.loaded`, which reaches
    every open browser. A failed reload deletes its staging graph, since the watch
    retries and a kept copy per attempt would fill the database.
    """
    report = load_graph(db, load_kb(kb_root), graph_name, keep_failed=False)
    err.print(f"Reloaded `{graph_name}` from KB {report.kb_digest}.")


def kb_signature(kb_root: Path) -> tuple[int, int, int] | None:
    """
    Identifies one KB build: a rebuild writes a new `stats.json`, in place or in a new
    `kb/`. `None` while the build is between its two renames.
    """
    try:
        st = (kb_root / "_graph" / "stats.json").stat()
    except OSError:
        return None
    return (st.st_ino, st.st_mtime_ns, st.st_size)


def watch_kb(
    kb_root: Path,
    stop: threading.Event,
    reload: Callable[[], None],
    *,
    seen: tuple[int, int, int] | None,
    debounce_ms: int = 2000,
    poll_ms: int = 5000,
) -> None:
    """
    Call `reload` once per KB build newer than `seen` (the `kb_signature` of the build
    already served, taken before the thread starts) until `stop` is set.

    The KB build swaps the whole `kb/` directory by rename, so a watch on `kb/_graph`
    goes stale after the first build. This watches the KB's parent directory for the
    `kb` entry, and the current `kb/_graph` for in-place writes to `stats.json`, and
    re-arms after every reload so it follows the new directory. Each wakeup, including
    one every `poll_ms` with no events, compares the `stats.json` signature with the
    last successfully reloaded build, which covers changes made while re-arming.
    Failed loads retry with exponential backoff, capped at a minute; a new build
    resets that delay. A failed reload never ends the watch.
    """
    from watchfiles import watch

    kb_root = kb_root.resolve()
    stats = kb_root / "_graph" / "stats.json"
    wanted = {str(kb_root), str(stats)}
    failed: tuple[int, int, int] | None = None
    retry_at = 0.0
    retry_delay = max(poll_ms / 1000, 0.1)
    while not stop.is_set():
        paths = [kb_root.parent] + ([stats.parent] if stats.parent.is_dir() else [])
        try:
            for _ in watch(
                *paths,
                watch_filter=lambda _change, path: path in wanted,
                debounce=debounce_ms,
                stop_event=stop,
                rust_timeout=poll_ms,
                yield_on_timeout=True,
                recursive=False,
            ):
                current = kb_signature(kb_root)
                if current is None or current == seen:
                    continue
                if current == failed and time.monotonic() < retry_at:
                    continue
                if current != failed:
                    retry_delay = max(poll_ms / 1000, 0.1)
                try:
                    reload()
                except Exception as e:
                    # Escaped, so markup-like text in a message cannot raise here.
                    err.print(
                        f"[bold red]reload failed:[/bold red] {escape(f'{type(e).__name__}: {e}')}"
                    )
                    failed = current
                    retry_at = time.monotonic() + retry_delay
                    retry_delay = min(retry_delay * 2, 60.0)
                else:
                    seen = current
                    failed = None
                break
        except Exception as e:
            # The watched `kb/_graph` can vanish mid-build; wait and re-arm.
            err.print(f"[yellow]watch restarting:[/yellow] {escape(f'{type(e).__name__}: {e}')}")
            stop.wait(1.0)


def _print_result(result: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    table = Table(*result["columns"])
    for row in result["rows"]:
        table.add_row(*(_cell(value) for value in row))
    out.print(table)
    graph = result["graph"]
    if graph["nodes"]:
        err.print(
            f"[dim]{len(graph['nodes'])} nodes, {len(graph['links'])} relationships in result graph[/dim]"
        )


def _cell(value: Any) -> str:
    if isinstance(value, dict) and "id" in value and "labels" in value:
        return f"{value.get('name') or ''} ({value['id']})"
    if isinstance(value, dict) and "relationship" in value:
        return value["relationship"]
    if isinstance(value, dict) and "nodes" in value:
        return " → ".join(value["nodes"])
    if isinstance(value, list):
        return ", ".join(_cell(v) for v in value)
    return "" if value is None else str(value)
