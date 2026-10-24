"""
Open a FalkorDB database: an embedded FalkorDBLite server by default, or a remote
server when a URL is given.

The embedded server is a `redis-server` with the FalkorDB module, started as a
child process and persisted to one RDB file, so local runs and tests need no
Docker, VM or account. A remote URL is only ever used when passed explicitly; this
package never takes a server address from the environment (`FALKORDB_*` or
otherwise), so it cannot write to a shared server by accident.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DATA_DIR_ENV = "PARAVERSE_GRAPH_DATA"
DEFAULT_DB_FILE = "paraverse-graph.rdb"


def default_data_dir() -> Path:
    """
    `$PARAVERSE_GRAPH_DATA`, else `.data/` in this project (`db/`), else in the working
    directory when the package is installed elsewhere.
    """
    env = os.environ.get(DATA_DIR_ENV)
    if env:
        return Path(env)
    project = Path(__file__).resolve().parents[2]
    base = project if (project / "pyproject.toml").is_file() else Path.cwd()
    return base / ".data"


def open_db(db_file: Path | None = None, url: str | None = None) -> Any:
    """
    Return a `falkordb.FalkorDB`-compatible client.
    """
    if url:
        from falkordb import FalkorDB

        return FalkorDB.from_url(url)

    from redislite.falkordb_client import FalkorDB as EmbeddedFalkorDB

    path = db_file or default_data_dir() / DEFAULT_DB_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    return EmbeddedFalkorDB(str(path))


def graph_exists(db: Any, name: str) -> bool:
    return name in db.list_graphs()


def delete_graph(db: Any, name: str) -> None:
    if graph_exists(db, name):
        db.select_graph(name).delete()


def engine_version(db: Any) -> str | None:
    """
    The FalkorDB module version, such as `4.18.3`, from `MODULE LIST`.
    """
    for module in db.connection.execute_command("MODULE", "LIST"):
        if isinstance(module, dict):
            name, version = module.get("name"), module.get("ver")
        else:
            fields = dict(zip(module[::2], module[1::2], strict=False))
            name, version = fields.get(b"name") or fields.get("name"), fields.get(b"ver")
        if name in ("graph", b"graph") and isinstance(version, int):
            return f"{version // 10000}.{version // 100 % 100}.{version % 100}"
    return None
