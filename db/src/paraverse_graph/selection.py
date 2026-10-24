"""Select known local datasets and atomically rebuild a separate browser view."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from redis.exceptions import RedisError

from paraverse_graph.composition import compose_kbs
from paraverse_graph.kb import KbError, build_snapshot
from paraverse_graph.loader import LoadError, load_graph
from paraverse_graph.mapping import ENTITY_LABEL, META_LABEL

# Loader and dependency changes invalidate persisted browser views too.
_CACHE_CODE_DIGEST = hashlib.sha256(
    b"browser-cache-v1"
    + b"".join(
        path.read_bytes()
        for path in [
            *sorted(Path(__file__).parent.glob("*.py")),
            Path(__file__).parents[2] / "pyproject.toml",
            Path(__file__).parents[2] / "uv.lock",
        ]
        if path.is_file()
    )
).hexdigest()


type SourceSignatures = tuple[tuple[int, int, int] | None, ...]


class SelectionError(ValueError):
    """A selection cannot be loaded; the previous browser view remains active."""


class DatasetSelection:
    """One server's selected sources, loaded into a graph separate from source graphs."""

    def __init__(self, db: Any, sources: Mapping[str, Path], graph_name: str) -> None:
        self.db: Any = db
        self.sources: dict[str, Path] = dict(sorted(sources.items()))
        self.graph_name: str = graph_name
        self._selected: tuple[str, ...] = ()
        self._signatures: SourceSignatures = ()
        self._state_lock: threading.Lock = threading.Lock()
        self._build_lock: threading.Lock = threading.Lock()
        self._failed_build: tuple[tuple[str, ...], SourceSignatures] | None = None
        self._retry_at: float | None = None
        self._retry_delay: float = 30
        self._labels: dict[str, str] = {
            name: self._label(name, root) for name, root in self.sources.items()
        }

    @staticmethod
    def _label(name: str, root: Path) -> str:
        try:
            names = []
            with (root / "_graph/nodes.jsonl").open() as stream:
                for line in stream:
                    node = json.loads(line)
                    if not isinstance(node, dict):
                        return name
                    if node.get("kind") == "event" and node.get("name"):
                        names.append(str(node["name"]))
            if len(names) == 1:
                return names[0]
            series = {re.sub(r"\s+\d{4}$", "", title) for title in names}
            if len(series) == 1:
                return next(iter(series))
        except (OSError, ValueError):
            pass
        return name

    def describe(self) -> dict[str, Any]:
        with self._state_lock:
            selected = self._selected
        return {
            "selection_enabled": True,
            "selected": list(selected),
            "datasets": [
                {
                    "id": name,
                    "name": self._labels[name],
                    "selected": name in selected,
                    "available": (root / "_graph/nodes.jsonl").is_file(),
                }
                for name, root in self.sources.items()
            ],
        }

    def active_roots(self) -> tuple[Path, ...]:
        with self._state_lock:
            selected = self._selected
        return tuple(self.sources[name] for name in selected)

    def select(self, requested: Any) -> dict[str, Any]:
        if (
            not isinstance(requested, list)
            or not requested
            or not all(isinstance(name, str) for name in requested)
        ):
            raise SelectionError("Choose at least one dataset.")
        names = tuple(sorted(set(requested)))
        if any(name not in self.sources for name in names):
            raise SelectionError("One of the selected datasets is not available on this server.")
        with self._build_lock:
            signatures = self._signature(names)
            self._load(names, signatures)
        return {"selected": list(names), "graph": self.graph_name}

    def _load(self, names: tuple[str, ...], signatures: SourceSignatures) -> None:
        # Only callers holding the build lock may compose or replace the browser graph.
        try:
            key = self._cache_key(names)
            if not (self._cached_graph_matches(key) and self._cache_key(names) == key):
                kb = compose_kbs({name: self.sources[name] for name in names})
                loaded_key = self._cache_key(
                    names, {name: source.snapshot for name, source in kb.source_kbs.items()}
                )
                load_graph(
                    self.db, kb, self.graph_name, keep_failed=False, browser_cache_key=loaded_key
                )
        except (KbError, LoadError, RedisError, OSError, ValueError) as exc:
            failed_build = (names, signatures)
            if failed_build != self._failed_build:
                self._retry_delay = 30
            self._failed_build = failed_build
            # Invalid source content needs a new build. IO and database failures can
            # recover without a source edit, so retry with a capped backoff instead.
            cause: BaseException | None = exc
            while cause is not None and not isinstance(cause, (LoadError, RedisError, OSError)):
                cause = cause.__cause__
            if cause is not None:
                self._retry_at = time.monotonic() + self._retry_delay
                self._retry_delay = min(self._retry_delay * 2, 300)
            else:
                self._retry_at = None
            raise SelectionError(
                "The selected datasets could not be combined. The previous view is still active. "
                f"{exc}"
            ) from exc
        with self._state_lock:
            self._selected = names
            self._signatures = signatures
        self._failed_build = None
        self._retry_at = None
        self._retry_delay = 30

    def _cache_key(
        self,
        names: tuple[str, ...],
        snapshots: Mapping[str, dict[str, tuple[int, ...]] | None] | None = None,
    ) -> str:
        sources = {
            name: {
                "root": str(self.sources[name].resolve()),
                "files": snapshots[name]
                if snapshots is not None
                else build_snapshot(self.sources[name]),
            }
            for name in names
        }
        return hashlib.sha256(
            json.dumps([_CACHE_CODE_DIGEST, sources], sort_keys=True).encode()
        ).hexdigest()

    def _cached_graph_matches(self, key: str) -> bool:
        if self.db is None:
            return False
        try:
            graph = self.db.select_graph(self.graph_name)
            rows = graph.ro_query(
                f"MATCH (m:{META_LABEL}) WHERE m.graph = $graph "
                "RETURN m.browser_cache_key, m.kb_digest, m.stats_json",
                {"graph": self.graph_name},
            ).result_set
            if len(rows) != 1 or rows[0][0] != key or not rows[0][1]:
                return False
            stats = json.loads(rows[0][2])
            nodes = graph.ro_query(f"MATCH (n:{ENTITY_LABEL}) RETURN count(n)").result_set[0][0]
            edges = graph.ro_query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
            return nodes == stats["node_total"] and edges == stats["edge_total"]
        except (RedisError, ValueError, TypeError, KeyError, IndexError):
            return False

    def _signature(self, names: tuple[str, ...]) -> SourceSignatures:
        signatures = []
        for name in names:
            try:
                stat = (self.sources[name] / "_graph/stats.json").stat()
                signatures.append((stat.st_ino, stat.st_mtime_ns, stat.st_size))
            except OSError:
                signatures.append(None)
        return tuple(signatures)

    def refresh_if_changed(self) -> bool:
        with self._build_lock:
            with self._state_lock:
                selected, signatures = self._selected, self._signatures
            current = self._signature(selected)
            if current == signatures or any(value is None for value in current):
                return False
            if self._failed_build == (selected, current) and (
                self._retry_at is None or time.monotonic() < self._retry_at
            ):
                return False
            self._load(selected, current)
            return True
