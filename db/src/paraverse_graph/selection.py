"""Select known local datasets and atomically rebuild a separate browser view."""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from redis.exceptions import RedisError

from paraverse_graph.composition import compose_kbs
from paraverse_graph.connection import delete_graph
from paraverse_graph.kb import KbError
from paraverse_graph.loader import LoadError, TransientLoadError, load_graph

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
        self._closed: bool = False
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
            return DatasetSelection._event_label(name, names)
        except (OSError, ValueError):
            pass
        return name

    @staticmethod
    def _event_label(name: str, titles: list[str]) -> str:
        if len(titles) == 1:
            return titles[0]
        series = {re.sub(r"\s+\d{4}$", "", title) for title in titles}
        return next(iter(series)) if len(series) == 1 else name

    def describe(self) -> dict[str, Any]:
        with self._state_lock:
            selected = self._selected
            labels = self._labels.copy()
        return {
            "selection_enabled": True,
            "selected": list(selected),
            "datasets": [
                {
                    "id": name,
                    "name": labels[name],
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
            with self._state_lock:
                if self._closed:
                    raise SelectionError("The browser server is shutting down.")
            signatures = self._signature(names)
            self._load(names, signatures)
        return {"selected": list(names), "graph": self.graph_name}

    def _load(self, names: tuple[str, ...], signatures: SourceSignatures) -> None:
        # Only callers holding the build lock may compose or replace the browser graph.
        try:
            kb = compose_kbs({name: self.sources[name] for name in names})
            labels = {
                name: self._event_label(
                    name,
                    [str(node.name) for node in source.nodes if node.kind == "event" and node.name],
                )
                for name, source in kb.source_kbs.items()
            }
            load_graph(self.db, kb, self.graph_name, keep_failed=False)
        except (KbError, LoadError, RedisError, OSError, ValueError) as exc:
            failed_build = (names, signatures)
            if failed_build != self._failed_build:
                self._retry_delay = 30
            self._failed_build = failed_build
            # Invalid source content needs a new build. IO and database failures can
            # recover without a source edit, so retry with a capped backoff instead.
            cause: BaseException | None = exc
            while cause is not None and not isinstance(
                cause, (TransientLoadError, RedisError, OSError)
            ):
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
            self._labels.update(labels)
        self._failed_build = None
        self._retry_at = None
        self._retry_delay = 30

    def close(self) -> None:
        """Stop new builds and remove this server's graph after any active build."""
        with self._state_lock:
            self._closed = True
        with self._build_lock:
            delete_graph(self.db, self.graph_name)

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
                if self._closed:
                    return False
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
