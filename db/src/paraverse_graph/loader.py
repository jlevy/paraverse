"""
Load a knowledge base into FalkorDB as a full rebuild.

The KB build is deterministic and replaces `kb/` as a whole, so the loader does the
same: it writes a staging graph with its indexes, unique constraint, schemas and
metadata, checks it against the export's own counts, and only then replaces the live
graph with a Redis `RENAME`. The rename swaps the whole graph in one step, so readers
never see a missing or half-built graph, and a failed or partial load never replaces a
good graph.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from paraverse_graph.connection import engine_version
from paraverse_graph.datasets import dataset_name
from paraverse_graph.kb import KnowledgeBase
from paraverse_graph.mapping import (
    ENTITY_LABEL,
    LABELS,
    META_LABEL,
    SCHEMA_LABEL,
    edge_properties,
    labels_for,
    node_properties,
    readable_name,
    relationship_type,
)
from paraverse_graph.schemas import KindSchema, load_kind_schemas

BATCH_SIZE = 500

# Staging graphs are `<graph>__staging_<pid>_<random>`, one per load.
STAGING_INFIX = "__staging_"

# Range indexes beyond the per-label `id` indexes, for the filters the query
# catalog and a schedule UI use.
RANGE_INDEXES: tuple[tuple[str, str], ...] = (
    ("Session", "start_epoch"),
    ("Session", "code"),
    ("Repository", "stars"),
    ("GitHubAccount", "login"),
    ("Organization", "sponsor_tier"),
)

FULLTEXT_INDEXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (ENTITY_LABEL, ("search_text",)),
    ("Session", ("title", "abstract")),
    ("Person", ("display_name", "bio")),
)


class LoadError(RuntimeError):
    """The staging graph did not match the knowledge base, so nothing was replaced."""


@dataclass
class LoadReport:
    graph: str
    dataset: str
    kb_root: str
    kb_digest: str
    engine: str | None
    nodes_by_kind: dict[str, int]
    edges_by_relation: dict[str, int]
    seconds: float
    problems: list[str] = field(default_factory=list)

    @property
    def node_total(self) -> int:
        return sum(self.nodes_by_kind.values())

    @property
    def edge_total(self) -> int:
        return sum(self.edges_by_relation.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "graph": self.graph,
            "dataset": self.dataset,
            "kb_root": self.kb_root,
            "kb_digest": self.kb_digest,
            "engine": self.engine,
            "node_total": self.node_total,
            "edge_total": self.edge_total,
            "nodes_by_kind": self.nodes_by_kind,
            "edges_by_relation": self.edges_by_relation,
            "seconds": round(self.seconds, 3),
            "problems": self.problems,
        }


def load_graph(
    db: Any, kb: KnowledgeBase, graph_name: str, *, batch_size: int = BATCH_SIZE
) -> LoadReport:
    """
    Rebuild `graph_name` from `kb`. Raises `LoadError` and leaves the live graph
    untouched if the staging graph's counts differ from `kb/_graph/stats.json`.

    Each load writes its own staging graph, `<graph>__staging_<pid>_<random>`, so a
    `serve --watch` reload and a manual `paraverse-graph load` against the same server cannot
    overwrite each other's staging graph. If any step fails, the staging graph is kept
    for inspection; nothing deletes it automatically, because another process's
    staging graph may still be loading. Delete it with `GRAPH.DELETE` when done.
    """
    started = time.monotonic()
    staging = f"{graph_name}{STAGING_INFIX}{os.getpid()}_{secrets.token_hex(3)}"
    graph = db.select_graph(staging)

    # The `id` lookups that attach every relationship need this index to exist first.
    graph.query(f"CREATE INDEX FOR (n:{ENTITY_LABEL}) ON (n.id)")

    for labels, rows in _group_nodes(kb):
        label_expr = ":".join(labels)
        for batch in _batches(rows, batch_size):
            graph.query(
                f"UNWIND $rows AS row CREATE (n:{label_expr}) SET n += row", {"rows": batch}
            )

    for rel_type, rows in _group_edges(kb):
        for batch in _batches(rows, batch_size):
            graph.query(
                f"""
                UNWIND $rows AS row
                MATCH (a:{ENTITY_LABEL} {{id: row.s}})
                MATCH (b:{ENTITY_LABEL} {{id: row.t}})
                CREATE (a)-[e:{rel_type}]->(b)
                SET e += row.p
                """,
                {"rows": batch},
            )

    _create_indexes(graph)
    report = LoadReport(
        graph=graph_name,
        dataset=dataset_name(kb.root),
        kb_root=str(kb.root),
        kb_digest=kb.digest,
        engine=engine_version(db),
        nodes_by_kind=_count_nodes(graph),
        edges_by_relation=_count_edges(graph),
        seconds=0.0,
    )
    report.problems = _compare(report, kb.stats) + _duplicate_ids(graph)
    if report.problems:
        raise LoadError(
            f"staging graph `{staging}` does not match the KB: " + "; ".join(report.problems)
        )

    _write_schemas(graph, load_kind_schemas(kb.root))
    # Uniqueness was already checked above, so this cannot fail on this data; it
    # guards later writes. It is built before the swap, so the live graph never lacks it.
    _create_unique_id_constraint(db, staging)
    loaded_at = datetime.now(UTC).isoformat(timespec="seconds")
    graph.query(
        f"CREATE (m:{META_LABEL}) SET m += $meta",
        {
            "meta": {
                "graph": graph_name,
                "dataset": report.dataset,
                "kb_root": str(kb.root),
                "kb_digest": kb.digest,
                "loaded_at": loaded_at,
                "stats_json": json.dumps(kb.stats, sort_keys=True),
                "rel_stats_json": json.dumps(_relationship_stats(graph)),
            }
        },
    )
    # `RENAME` replaces the live graph atomically and keeps its indexes and the
    # operational constraint (checked on FalkorDB 4.18, including across an RDB
    # restart), so there is no window in which the live graph is missing.
    db.connection.execute_command("RENAME", staging, graph_name)
    report.seconds = time.monotonic() - started
    # FalkorDB is Redis, so open browsers learn about the new graph over pub/sub.
    db.connection.publish(
        events_channel(graph_name),
        json.dumps({"type": "graph.loaded", "kb_digest": kb.digest, "loaded_at": loaded_at}),
    )
    return report


def events_channel(graph_name: str) -> str:
    return f"paraverse-graph:{graph_name}"


def _group_nodes(kb: KnowledgeBase) -> Iterator[tuple[tuple[str, ...], list[dict[str, Any]]]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    names = {node.id: node.name for node in kb.nodes}
    for node in kb.nodes:
        payload = kb.payload_for(node)
        display = readable_name(node, payload, names)
        groups[labels_for(node, payload)].append(
            node_properties(node, payload, display_name=display)
        )
    yield from sorted(groups.items())


def _group_edges(kb: KnowledgeBase) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in kb.edges:
        groups[relationship_type(edge.relation)].append(
            {"s": edge.source, "t": edge.target, "p": edge_properties(edge)}
        )
    yield from sorted(groups.items())


def _create_indexes(graph: Any) -> None:
    for label in sorted(set(LABELS.values())):
        graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
    for label, prop in RANGE_INDEXES:
        graph.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
    for label, props in FULLTEXT_INDEXES:
        args = ", ".join(f"'{p}'" for p in props)
        graph.query(f"CALL db.idx.fulltext.createNodeIndex('{label}', {args})")


def _write_schemas(graph: Any, schemas: dict[str, KindSchema]) -> None:
    rows = [
        {
            "kind": s.kind,
            "label": LABELS[s.kind],
            "title": s.title,
            "description": s.description,
            "contract": s.contract,
            "fields_json": json.dumps(s.fields),
            "defs_json": json.dumps(s.defs),
            "schema_json": json.dumps(s.schema),
        }
        for s in schemas.values()
    ]
    graph.query(f"UNWIND $rows AS row CREATE (s:{SCHEMA_LABEL}) SET s += row", {"rows": rows})
    graph.query(f"CREATE INDEX FOR (s:{SCHEMA_LABEL}) ON (s.kind)")


def _relationship_stats(graph: Any) -> list[dict[str, Any]]:
    """
    Which kinds each relationship type connects, with counts, so an API can describe a
    kind's relationship columns without scanning the graph on every request.
    """
    rows = graph.query(
        f"""
        MATCH (a:{ENTITY_LABEL})-[r]->(b:{ENTITY_LABEL})
        RETURN a.entity_kind, type(r), b.entity_kind, count(r)
        ORDER BY a.entity_kind, type(r), b.entity_kind
        """
    ).result_set
    return [{"from": a, "type": t, "to": b, "count": n} for a, t, b, n in rows]


def _create_unique_id_constraint(db: Any, graph_name: str, timeout: float = 30.0) -> None:
    db.connection.execute_command(
        "GRAPH.CONSTRAINT",
        "CREATE",
        graph_name,
        "UNIQUE",
        "NODE",
        ENTITY_LABEL,
        "PROPERTIES",
        "1",
        "id",
    )
    graph = db.select_graph(graph_name)
    deadline = time.monotonic() + timeout
    while True:
        statuses = [
            row[0]
            for row in graph.ro_query(
                "CALL db.constraints() YIELD label, status WHERE label = $label RETURN status",
                {"label": ENTITY_LABEL},
            ).result_set
        ]
        if statuses and all(s == "OPERATIONAL" for s in statuses):
            return
        if "FAILED" in statuses:
            raise LoadError(f"unique constraint on {ENTITY_LABEL}.id failed in `{graph_name}`")
        if time.monotonic() > deadline:
            raise LoadError(f"unique constraint on {ENTITY_LABEL}.id still building: {statuses}")
        time.sleep(0.05)


def _duplicate_ids(graph: Any) -> list[str]:
    rows = graph.query(
        f"MATCH (n:{ENTITY_LABEL}) WITH n.id AS id, count(n) AS c WHERE c > 1 RETURN id, c LIMIT 10"
    ).result_set
    return [f"duplicate id {entity_id} ({count} nodes)" for entity_id, count in rows]


def _count_nodes(graph: Any) -> dict[str, int]:
    rows = graph.query(
        f"MATCH (n:{ENTITY_LABEL}) RETURN n.entity_kind AS kind, count(n) ORDER BY kind"
    ).result_set
    return {kind: count for kind, count in rows}


def _count_edges(graph: Any) -> dict[str, int]:
    rows = graph.query("MATCH ()-[e]->() RETURN type(e) AS t, count(e) ORDER BY t").result_set
    return {rel_type.lower(): count for rel_type, count in rows}


def _compare(report: LoadReport, stats: dict[str, Any]) -> list[str]:
    problems = []
    for label, actual, expected in (
        ("nodes", report.nodes_by_kind, stats.get("nodes", {})),
        ("edges", report.edges_by_relation, stats.get("edges", {})),
    ):
        diff = Counter(expected)
        diff.subtract(Counter(actual))
        problems.extend(
            f"{label}.{key}: expected {expected.get(key, 0)}, loaded {actual.get(key, 0)}"
            for key, delta in sorted(diff.items())
            if delta
        )
    return problems


def _batches(rows: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]
