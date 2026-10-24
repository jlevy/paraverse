"""
Convert FalkorDB query results into plain JSON.

Every result has `columns` and `rows`. Any nodes, relationships or paths in the rows
are also collected into `graph` (`nodes` plus `links`), in the shape the
`@falkordb/canvas` web component takes, so one response can drive a table and a
graph view. A native client can decode the same JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from falkordb import Edge, Node, Path

# Large or internal properties that are left out of graph payloads; `entity`
# results return `doc` separately, parsed.
HIDDEN_PROPS = frozenset({"doc", "search_text"})


@dataclass
class _GraphCollector:
    # Keyed by FalkorDB's internal IDs, which query results always carry.
    nodes: dict[int | None, dict[str, Any]] = field(default_factory=dict)
    links: dict[int | None, dict[str, Any]] = field(default_factory=dict)
    include_doc: bool = False

    def add_node(self, node: Node) -> str:
        entity_id = str(node.properties.get("id", f"internal:{node.id}"))
        if node.id not in self.nodes:
            self.nodes[node.id] = node_json(node, include_doc=self.include_doc)
        return entity_id

    def add_edge(self, edge: Edge) -> dict[str, Any]:
        link = {
            "id": edge.id,
            "relationship": edge.relation,
            "source": edge.src_node,
            "target": edge.dest_node,
            "data": dict(edge.properties),
        }
        self.links.setdefault(edge.id, link)
        return link

    def graph(self) -> dict[str, Any]:
        """
        Links refer to internal node IDs until here; they are rewritten to entity IDs,
        and any link whose endpoint is not in the result is dropped.
        """
        ids = {internal: node["id"] for internal, node in self.nodes.items()}
        links = [
            {**link, "source": ids[link["source"]], "target": ids[link["target"]]}
            for link in self.links.values()
            if link["source"] in ids and link["target"] in ids
        ]
        return {"nodes": list(self.nodes.values()), "links": links}


def node_json(node: Node, *, include_doc: bool = False) -> dict[str, Any]:
    props = node.properties
    data = {k: v for k, v in props.items() if k not in HIDDEN_PROPS}
    result: dict[str, Any] = {
        "id": props.get("id", f"internal:{node.id}"),
        "labels": list(node.labels or []),
        "kind": props.get("entity_kind"),
        "name": props.get("display_name"),
        "data": data,
    }
    if include_doc and isinstance(props.get("doc"), str):
        result["doc"] = json.loads(props["doc"])
    return result


def result_json(result: Any, *, include_doc: bool = False) -> dict[str, Any]:
    collector = _GraphCollector(include_doc=include_doc)
    columns = [
        column[1] if isinstance(column, list | tuple) else column for column in result.header
    ]
    rows = [
        [_jsonable(value, collector, include_doc=include_doc) for value in row]
        for row in result.result_set
    ]
    return {"columns": columns, "rows": rows, "graph": collector.graph()}


def _jsonable(value: Any, collector: _GraphCollector, *, include_doc: bool) -> Any:
    if isinstance(value, Node):
        collector.add_node(value)
        return node_json(value, include_doc=include_doc)
    if isinstance(value, Edge):
        return collector.add_edge(value)
    if isinstance(value, Path):
        return {
            "nodes": [collector.add_node(n) for n in value.nodes()],
            "relationships": [collector.add_edge(e)["relationship"] for e in value.edges()],
        }
    if isinstance(value, list):
        return [_jsonable(v, collector, include_doc=include_doc) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v, collector, include_doc=include_doc) for k, v in value.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return value
    # Temporal and point values have no JSON form; their string form is ISO-like.
    return str(value)
