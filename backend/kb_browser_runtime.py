"""Native-owned KB launcher: bind reuse to local inputs and clean up on early close."""

from __future__ import annotations

import json
import signal
import sys
from pathlib import Path
from types import FrameType
from typing import Any


def expected_selection(root: Path) -> dict:
    from paraverse_graph.composition import compose_kbs
    from paraverse_graph.datasets import list_datasets, resolve_dataset

    sources = {dataset.name: dataset.require_kb() for dataset in list_datasets(root / "db")}
    target = resolve_dataset(start=root / "db")
    if target.kb_root is not None and (target.kb_root / "_graph/nodes.jsonl").is_file():
        sources[target.name] = target.require_kb()
    if not sources:
        raise ValueError(
            "No local knowledge bases are available; initialize the dataset submodules."
        )
    kb = compose_kbs(sources)
    return {"selected": sorted(sources), "kb_digest": kb.digest}


def serve() -> int:
    # Install this before importing the CLI or opening Redis. During startup
    # uvicorn has no signal handler yet. SystemExit runs redislite's registered
    # atexit cleanup, including its detached daemon, on an early native close.
    def terminate(signum: int, _frame: FrameType | None) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    from paraverse_graph import cli

    # The CLI owns the factory binding; instrument only this native process.
    original_open_db = cli.open_db  # pyright: ignore[reportPrivateLocalImportUsage]
    databases: list[Any] = []

    def open_owned_db(db_file: Path | None = None, url: str | None = None) -> Any:
        db = original_open_db(db_file, url)
        if url is None:
            databases.append(db)
        return db

    cli.open_db = open_owned_db  # pyright: ignore[reportPrivateLocalImportUsage]
    try:
        return cli.main(["serve", "--select-all", "--watch", "--port", "8766"])
    finally:
        cli.open_db = original_open_db  # pyright: ignore[reportPrivateLocalImportUsage]
        for db in reversed(databases):
            # Uvicorn/pubsub can leave several of our own pooled connections.
            # redislite mistakes them for other clients and skips daemon cleanup.
            # Disconnect ours first; its shared-client guard still protects users
            # connected through a different pool or process.
            db.connection.connection_pool.disconnect()
            db.close()


def main() -> int:
    if sys.argv[1:] == ["describe"]:
        print(json.dumps(expected_selection(Path(__file__).resolve().parents[1])))
        return 0
    if sys.argv[1:] == ["serve"]:
        return serve()
    raise ValueError("Expected describe or serve")


if __name__ == "__main__":
    raise SystemExit(main())
