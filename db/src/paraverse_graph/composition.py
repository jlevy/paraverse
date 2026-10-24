"""Compose named, immutable KB reads without generating another on-disk export.

Typed IDs are the join keys, never display names. Shared lists use source-order unions;
scalar conflicts choose the first non-null value in dataset-name order and keep
all variants in `_composition.conflicts`. Every record retains its source paths.
Person-ID collisions require a shared resolved GitHub account (or an explicitly
verified account edge) in every source; ambiguous people fail before graph loading.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from paraverse_graph.kb import Artifact, KbEdge, KbError, KbNode, KnowledgeBase, load_kb
from paraverse_graph.schemas import describe_fields, load_kind_schemas, merge_kind_schemas


def compose_kbs(sources: Mapping[str, Path]) -> KnowledgeBase:
    """Read named sources and return one KB with merged schemas and source guards.

    Input order and filesystem location do not affect the resulting content hash.
    No input files are written. Each source must be internally complete, even when
    another selected source could supply one of its missing relationship endpoints.
    """
    if not sources or any(not name.strip() for name in sources):
        raise KbError("composition needs at least one nonempty dataset name")
    inputs = {name: load_kb(Path(sources[name])) for name in sorted(sources)}
    schemas = merge_kind_schemas({name: load_kind_schemas(kb.root) for name, kb in inputs.items()})
    grouped: dict[str, list[tuple[str, KbNode, dict[str, Any]]]] = defaultdict(list)
    for name, kb in inputs.items():
        _validate_source(name, kb)
        for node in kb.nodes:
            payload = kb.payload_for(node)
            if "_composition" in payload:
                raise KbError(f"{name}: {node.id} uses reserved field _composition")
            grouped[node.id].append((name, node, payload))

    nodes: list[KbNode] = []
    artifacts: dict[str, Artifact] = {}
    for node_id, versions in sorted(grouped.items()):
        first_name, first, _ = versions[0]
        if len({node.kind for _, node, _ in versions}) != 1:
            raise KbError(f"{node_id}: different kinds use the same typed ID")
        if first.kind == "person" and len(versions) > 1:
            verified = [_verified_accounts(inputs[name], node) for name, node, _ in versions]
            if not set.intersection(*verified):
                names = ", ".join(name for name, _, _ in versions)
                raise KbError(
                    f"{node_id}: ambiguous person ID in {names}; "
                    "a shared verified account is required before merging"
                )
        conflicts: list[dict[str, Any]] = []
        payload = _merge_values([(name, payload) for name, _, payload in versions], "", conflicts)
        payload["id"] = node_id
        payload["_composition"] = {
            "sources": [
                {
                    "dataset": name,
                    "path": node.path,
                    "name": node.name,
                    "contract": inputs[name].artifacts[node.path].contract,
                }
                for name, node, _ in versions
            ],
            "conflicts": conflicts,
        }
        # A separate in-memory artifact per node also handles nested day/term
        # records whose original parent artifact may itself have been merged.
        # This key is only for lookup; the source display paths remain in provenance.
        path = f"{first_name}/{first.path}#{node_id}"
        nodes.append(replace(first, path=path))
        artifacts[path] = Artifact(
            path, inputs[first_name].artifacts[first.path].contract, first.kind, payload
        )

    edge_sources: dict[str, tuple[KbEdge, list[str]]] = {}
    for name, kb in inputs.items():
        for edge in kb.edges:
            key = _json([edge.source, edge.relation, edge.target, edge.attrs])
            if key not in edge_sources:
                edge_sources[key] = (edge, [])
            if name not in edge_sources[key][1]:
                edge_sources[key][1].append(name)
    edges = [
        replace(edge, attrs={**deepcopy(edge.attrs), "_datasets": names})
        for _, (edge, names) in sorted(edge_sources.items())
    ]
    stats = {
        "nodes": dict(sorted(Counter(node.kind for node in nodes).items())),
        "edges": dict(sorted(Counter(edge.relation for edge in edges).items())),
        "node_total": len(nodes),
        "edge_total": len(edges),
        "datasets": list(inputs),
    }
    for kind, schema in schemas.items():
        spec = deepcopy(schema.schema)
        spec.setdefault("properties", {})["_composition"] = {
            "type": "object",
            "title": "Dataset provenance",
            "description": "Original dataset records and conflicting source values. "
            "The first non-null value in dataset-name order is displayed.",
        }
        schemas[kind] = replace(schema, schema=spec, fields=describe_fields(spec))
    sha = hashlib.sha256()
    for value in (
        list(inputs),
        [(node.id, node.kind, node.name, artifacts[node.path].payload) for node in nodes],
        [(e.source, e.relation, e.target, e.attrs) for e in edges],
        {kind: schema.schema for kind, schema in schemas.items()},
    ):
        sha.update(_json(value).encode())
    result = KnowledgeBase(
        root=next(iter(inputs.values())).root,
        nodes=nodes,
        edges=edges,
        stats=stats,
        artifacts=artifacts,
        digest=sha.hexdigest()[:16],
        source_kbs=inputs,
        kind_schemas=schemas,
    )
    result.check_unchanged()
    return result


def _validate_source(name: str, kb: KnowledgeBase) -> None:
    ids = {node.id for node in kb.nodes}
    if len(ids) != len(kb.nodes):
        raise KbError(f"{name}: duplicate typed IDs in source graph")
    for edge in kb.edges:
        if edge.source not in ids or edge.target not in ids:
            raise KbError(f"{name}: unresolved edge {edge.source} -{edge.relation}-> {edge.target}")
        if "_datasets" in edge.attrs:
            raise KbError(f"{name}: edge uses reserved attribute _datasets")
    for category, counts in (
        ("nodes", Counter(node.kind for node in kb.nodes)),
        ("edges", Counter(edge.relation for edge in kb.edges)),
    ):
        if counts != Counter(kb.stats.get(category, {})):
            raise KbError(f"{name}: {category} counts do not match source stats.json")


def _verified_accounts(kb: KnowledgeBase, person: KbNode) -> set[str]:
    payload = kb.payload_for(person) or {}
    account_kinds = {
        node.id: node.kind
        for node in kb.nodes
        if (node.kind == "github_account" and node.id.startswith("gh:"))
        or (node.kind == "social_account" and node.id.startswith("acct:"))
    }
    linked = {
        edge.target
        for edge in kb.edges
        if edge.source == person.id
        and edge.relation == "has_account"
        and edge.target in account_kinds
    }
    verified = {
        edge.target
        for edge in kb.edges
        if edge.source == person.id
        and edge.relation == "has_account"
        and edge.target in linked
        and edge.attrs.get("verified") is True
    }
    github = payload.get("github")
    if (
        payload.get("github_resolution") == "resolved"
        and isinstance(github, str)
        and github in linked
        and account_kinds[github] == "github_account"
    ):
        verified.add(github)
    return verified


def _merge_values(
    values: list[tuple[str, Any]],
    path: str,
    conflicts: list[dict[str, Any]],
) -> Any:
    non_null = [(name, value) for name, value in values if value is not None]
    if not non_null:
        return None
    if len(non_null) == 1:
        return deepcopy(non_null[0][1])
    if all(isinstance(value, dict) for _, value in non_null):
        keys = sorted({key for _, value in non_null for key in value})
        return {
            key: _merge_values(
                [(name, value[key]) for name, value in non_null if key in value],
                f"{path}.{key}" if path else key,
                conflicts,
            )
            for key in keys
        }
    if all(isinstance(value, list) for _, value in non_null):
        items: dict[str, Any] = {}
        for _, value in non_null:
            for item in value:
                items.setdefault(_json(item), item)
        return deepcopy(list(items.values()))
    if len({_json(value) for _, value in non_null}) > 1:
        conflicts.append(
            {
                "field": path,
                "values": [{"dataset": name, "value": deepcopy(value)} for name, value in values],
            }
        )
    return deepcopy(non_null[0][1])


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
