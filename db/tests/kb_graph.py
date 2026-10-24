"""
The default dataset's KB (`vendor/universe2026-md/kb`) loaded once per test process
into a temporary embedded FalkorDB, shared by the test modules.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import pytest

from paraverse_graph.connection import open_db
from paraverse_graph.kb import KB_RELATIVE_PATH, KnowledgeBase, find_kb_root, load_kb
from paraverse_graph.loader import LoadReport, load_graph

GRAPH = "universe_test"


@cache
def loaded() -> tuple[Any, Any, KnowledgeBase, LoadReport]:
    """
    `(db, graph, kb, report)`. Skips the calling test when the dataset's submodule is
    not checked out.
    """
    kb_root = find_kb_root(Path(__file__).parent)
    if kb_root is None:
        pytest.skip(f"{KB_RELATIVE_PATH} is not checked out; run `git submodule update --init`")
    kb = load_kb(kb_root)
    db = open_db(Path(mkdtemp(prefix="paraverse-graph-test-")) / "test.rdb")
    report = load_graph(db, kb, GRAPH)
    return db, db.select_graph(GRAPH), kb, report
