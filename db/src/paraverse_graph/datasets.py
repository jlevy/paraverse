"""
Choose the dataset a command works on, and the graph it loads into.

A dataset is a repository with its knowledge base in `kb/`, mounted as a git
submodule at `vendor/<name>/`. One dataset maps to one graph, named after it, so
datasets loaded into the same database never overwrite each other.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from paraverse_graph.kb import DEFAULT_DATASET, VENDOR_DIR, KbError, find_kb_root

KB_ENV = "PARAVERSE_KB"

MISSING_KB_HINT = "run `git submodule update --init` or pass --kb/--dataset"

# A dataset name is one directory name under `vendor/`, never a path.
_DATASET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass(frozen=True)
class Dataset:
    """
    A dataset and where its KB is. `kb_root` is `None` when a named dataset is not
    checked out under any `vendor/` at or above the working directory.
    """

    name: str
    kb_root: Path | None

    @property
    def graph(self) -> str:
        return graph_name(self.name)

    def require_kb(self) -> Path:
        """
        The KB directory, or a `KbError` that says how to get it.
        """
        root = self.kb_root
        if root is None or not (root / "_graph" / "nodes.jsonl").is_file():
            where = root or Path(VENDOR_DIR, self.name, "kb")
            raise KbError(
                f"no knowledge base at {where} (no _graph/nodes.jsonl); {MISSING_KB_HINT}"
            )
        return root


def resolve_dataset(
    kb: Path | None = None, name: str | None = None, *, start: Path | None = None
) -> Dataset:
    """
    The dataset a command means, in this order: `kb` (`--kb DIR`), `name`
    (`--dataset NAME`, the KB at `vendor/NAME/kb`), `$PARAVERSE_KB`, and then the
    default dataset. Named datasets are found by walking up from `start` (default:
    the working directory). A missing KB is reported only by `Dataset.require_kb()`,
    since serving or querying a loaded graph needs only the name.
    """
    if kb is None and name is None:
        env = os.environ.get(KB_ENV)
        kb = Path(env) if env else None
    if kb is not None:
        return Dataset(dataset_name(kb), kb)
    name = name or DEFAULT_DATASET
    if not _DATASET_NAME.fullmatch(name):
        raise KbError(f"invalid dataset name `{name}`; use a directory name under vendor/")
    return Dataset(name, find_kb_root(start, name))


def list_datasets(start: Path | None = None) -> list[Dataset]:
    """
    Every `vendor/*/kb` with a graph export at or above `start` (default: the working
    directory), sorted by name. When two `vendor/` directories hold the same name, the
    nearer one wins, as in `find_kb_root`.
    """
    here = (start or Path.cwd()).resolve()
    found: dict[str, Path] = {}
    for directory in (here, *here.parents):
        for nodes in sorted((directory / VENDOR_DIR).glob("*/kb/_graph/nodes.jsonl")):
            kb_root = nodes.parents[1]
            found.setdefault(kb_root.parent.name, kb_root)
    return [Dataset(name, found[name]) for name in sorted(found)]


def dataset_name(kb_root: Path) -> str:
    """
    The dataset a KB directory belongs to: the directory that holds `kb/`, as in
    `vendor/<name>/kb`, or the KB directory's own name when it is not called `kb`.
    Symlinks are not followed, so a mounted dataset keeps its mount name.
    """
    path = Path(os.path.abspath(kb_root))
    return path.parent.name if path.name == "kb" else path.name


def graph_name(dataset: str) -> str:
    """
    The graph a dataset loads into: the dataset name in lower case, with every
    character other than a letter, digit or underscore replaced by `_`, so it is a
    plain identifier (`universe2026-md` loads into `universe2026_md`).
    """
    return re.sub(r"[^a-z0-9_]", "_", dataset.lower())
