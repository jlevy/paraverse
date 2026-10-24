"""Select known local datasets and atomically rebuild a separate browser view."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from redis.exceptions import RedisError

from paraverse_graph.composition import compose_kbs
from paraverse_graph.kb import KbError
from paraverse_graph.loader import LoadError, load_graph


class SelectionError(ValueError):
    """A selection cannot be loaded; the previous browser view remains active."""


class DatasetSelection:
    """One server's selected sources, loaded into a graph separate from source graphs."""

    def __init__(self, db: Any, sources: Mapping[str, Path], graph_name: str) -> None:
        self.db: Any = db
        self.sources: dict[str, Path] = dict(sorted(sources.items()))
        self.graph_name: str = graph_name
        self._selected: tuple[str, ...] = ()
        self._signatures: tuple[tuple[int, int, int] | None, ...] = ()
        self._lock: threading.RLock = threading.RLock()
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
        with self._lock:
            return {
                "selection_enabled": True,
                "selected": list(self._selected),
                "datasets": [
                    {
                        "id": name,
                        "name": self._labels[name],
                        "selected": name in self._selected,
                        "available": (root / "_graph/nodes.jsonl").is_file(),
                    }
                    for name, root in self.sources.items()
                ],
            }

    def active_roots(self) -> tuple[Path, ...]:
        with self._lock:
            return tuple(self.sources[name] for name in self._selected)

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
        with self._lock:
            signatures = self._signature(names)
            try:
                kb = compose_kbs({name: self.sources[name] for name in names})
                load_graph(self.db, kb, self.graph_name, keep_failed=False)
            except (KbError, LoadError, RedisError, OSError, ValueError) as exc:
                raise SelectionError(
                    "The selected datasets could not be combined. The previous view is still active. "
                    f"{exc}"
                ) from exc
            self._selected = names
            self._signatures = signatures
            return {"selected": list(names), "graph": self.graph_name}

    def _signature(self, names: tuple[str, ...]) -> tuple[tuple[int, int, int] | None, ...]:
        signatures = []
        for name in names:
            try:
                stat = (self.sources[name] / "_graph/stats.json").stat()
                signatures.append((stat.st_ino, stat.st_mtime_ns, stat.st_size))
            except OSError:
                signatures.append(None)
        return tuple(signatures)

    def refresh_if_changed(self) -> bool:
        with self._lock:
            current = self._signature(self._selected)
            if current == self._signatures or any(value is None for value in current):
                return False
            self.select(list(self._selected))
            return True
