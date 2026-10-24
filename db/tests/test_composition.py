"""Composition contracts exercised with small portable JSON/YAML source exports."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml
from redis.exceptions import RedisError

from paraverse_graph.composition import compose_kbs
from paraverse_graph.connection import open_db
from paraverse_graph.kb import KbError
from paraverse_graph.loader import load_graph


def write_kb(
    root: Path,
    records: list[tuple[str, dict[str, Any]]],
    edges: list[dict[str, Any]] | None = None,
    *,
    role: str = "speaker",
) -> Path:
    (root / "_graph").mkdir(parents=True)
    (root / "_schemas").mkdir()
    nodes = []
    for kind, record in records:
        path = f"{len(nodes)}.yaml"
        nodes.append(
            {
                "id": record["id"],
                "kind": kind,
                "name": record.get("name", record["id"]),
                "path": path,
            }
        )
        (root / path).write_text(
            yaml.safe_dump(
                {
                    "softschema": {"contract": f"example:{kind}/v1", "envelope": kind},
                    kind: record,
                }
            )
        )
    edges = edges or []
    for filename, rows in (("nodes", nodes), ("edges", edges)):
        (root / "_graph" / f"{filename}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )
    (root / "_graph" / "stats.json").write_text(
        json.dumps(
            {
                "nodes": dict(Counter(node["kind"] for node in nodes)),
                "edges": dict(Counter(edge["relation"] for edge in edges)),
            }
        )
    )
    (root / "_schemas" / "person.schema.yaml").write_text(
        yaml.safe_dump(
            {
                "type": "object",
                "required": ["id", "name"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "participations": {"type": "array", "items": {"$ref": "#/$defs/Participation"}},
                },
                "$defs": {
                    "Participation": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": [role]},
                            "event": {"type": "string", "pattern": "^(event):[a-z0-9]+$"},
                        },
                    }
                },
            }
        )
    )
    return root


def test_composition_preserves_claims_references_and_graph_schema(tmp_path: Path):
    def source(name: str, role: str, description: str) -> Path:
        event = f"event:{name}"
        return write_kb(
            tmp_path / name,
            [
                ("event", {"id": event, "name": name}),
                (
                    "organization",
                    {
                        "id": "org:example",
                        "description": description,
                        "roles": [role],
                        "sources": [{"system": name, "url": f"https://example.org/{name}"}],
                    },
                ),
                ("github_account", {"id": "gh:example", "login": "example"}),
                (
                    "person",
                    {
                        "id": "person:example",
                        "name": "Example Person",
                        "github": "gh:example",
                        "github_resolution": "resolved",
                        "participations": [{"event": event, "role": role}],
                    },
                ),
                ("person", {"id": f"person:{name}", "name": "Same Display Name"}),
            ],
            [
                {"source": "person:example", "relation": "has_account", "target": "gh:example"},
                {
                    "source": "person:example",
                    "relation": "participates_in",
                    "target": event,
                    "role": role,
                },
            ],
            role=role,
        )

    first, second = (
        source("alpha", "judge", "One description"),
        source("beta", "speaker", "Another description"),
    )
    kb = compose_kbs({"beta": second, "alpha": first})
    assert kb.source_names == ("alpha", "beta")
    assert len(kb.nodes) == 7
    assert len(kb.edges) == 3
    org = kb.payload_for(next(node for node in kb.nodes if node.id == "org:example"))
    assert org is not None
    assert org["roles"] == ["judge", "speaker"]
    assert org["description"] == "One description"
    assert len(org["sources"]) == 2
    assert org["_composition"]["conflicts"] == [
        {
            "field": "description",
            "values": [
                {"dataset": "alpha", "value": "One description"},
                {"dataset": "beta", "value": "Another description"},
            ],
        }
    ]
    assert kb.digest == compose_kbs({"alpha": first, "beta": second}).digest

    db = open_db(tmp_path / "composed.rdb")
    try:
        report = load_graph(db, kb, "composition")
        assert report.problems == []
        assert report.as_dict()["datasets"] == ["alpha", "beta"]
        graph = db.select_graph("composition")
        rows = graph.ro_query(
            "MATCH (p:Person:Judge:Speaker)-[:PARTICIPATES_IN]->(e:Event) RETURN e.id ORDER BY e.id"
        ).result_set
        assert rows == [["event:alpha"], ["event:beta"]]
        rows = graph.ro_query("MATCH (s:Schema {kind: 'person'}) RETURN s.defs_json").result_set
        role = next(
            field for field in json.loads(rows[0][0])["Participation"] if field["name"] == "role"
        )
        assert role["enum"] == ["judge", "speaker"]
        assert graph.ro_query("MATCH (m:GraphMeta) RETURN m.datasets").result_set == [
            [["alpha", "beta"]]
        ]
    finally:
        db.close()


def test_committed_load_succeeds_when_notification_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    old = write_kb(tmp_path / "old", [("organization", {"id": "org:old"})])
    new = write_kb(tmp_path / "new", [("organization", {"id": "org:new"})])
    replacement = compose_kbs({"new": new})
    db = open_db(tmp_path / "notification.rdb")
    try:
        load_graph(db, compose_kbs({"old": old}), "notification")

        def unavailable(*_args: Any, **_kwargs: Any) -> None:
            raise RedisError("notification connection lost")

        monkeypatch.setattr(db.connection, "publish", unavailable)
        report = load_graph(db, replacement, "notification", keep_failed=False)
        assert report.problems == []
        assert report.kb_digest == replacement.digest
        assert report.datasets == ["new"]
        graph = db.select_graph("notification")
        assert graph.ro_query("MATCH (n:Entity) RETURN n.id").result_set == [["org:new"]]
        assert graph.ro_query("MATCH (m:GraphMeta) RETURN m.kb_digest, m.datasets").result_set == [
            [replacement.digest, ["new"]]
        ]
        assert (
            "loaded, but its reload notification failed: notification connection lost"
            in caplog.text
        )
    finally:
        db.close()


@pytest.mark.parametrize("resolution", ["unverified", "absent"])
def test_person_id_collision_needs_shared_verified_account(tmp_path: Path, resolution: str):
    records = [
        (
            "person",
            {
                "id": "person:same",
                "name": "Same Name",
                "github": "gh:same",
                "github_resolution": resolution,
            },
        ),
        ("github_account", {"id": "gh:same"}),
    ]
    edges = [{"source": "person:same", "relation": "has_account", "target": "gh:same"}]
    roots = {name: write_kb(tmp_path / name, records, edges) for name in ("a", "b")}
    with pytest.raises(KbError, match=r"ambiguous person ID.*shared verified account"):
        compose_kbs(roots)


def test_each_source_must_resolve_its_own_edges(tmp_path: Path):
    first = write_kb(
        tmp_path / "a",
        [("person", {"id": "person:a"})],
        [
            {"source": "person:a", "relation": "affiliated_with", "target": "org:b"},
        ],
    )
    second = write_kb(tmp_path / "b", [("organization", {"id": "org:b"})])
    with pytest.raises(KbError, match="a: unresolved edge"):
        compose_kbs({"a": first, "b": second})


def test_guards_and_digest_cover_nonprimary_payloads(tmp_path: Path):
    roots = {
        name: write_kb(tmp_path / name, [("organization", {"id": f"org:{name}", "name": name})])
        for name in ("a", "b")
    }
    kb = compose_kbs(roots)
    path = roots["b"] / "0.yaml"
    path.write_text(path.read_text().replace("name: b", "name: Changed"))
    with pytest.raises(KbError, match="b: KB changed"):
        kb.check_unchanged()
    assert compose_kbs(roots).digest != kb.digest


def test_nested_records_and_conflicting_edge_claims_survive(tmp_path: Path):
    roots = {}
    for name in ("a", "b"):
        roots[name] = write_kb(
            tmp_path / name,
            [
                ("event", {"id": f"event:{name}", "days": [{"id": f"day:{name}", "name": name}]}),
                ("organization", {"id": "org:one"}),
                ("organization", {"id": "org:two"}),
            ],
            [{"source": "org:one", "relation": "sponsors", "target": "org:two", "tier": name}],
        )
        graph = roots[name] / "_graph"
        with (graph / "nodes.jsonl").open("a") as out:
            out.write(
                json.dumps({"id": f"day:{name}", "kind": "day", "name": name, "path": "0.yaml"})
                + "\n"
            )
        stats = json.loads((graph / "stats.json").read_text())
        stats["nodes"]["day"] = 1
        (graph / "stats.json").write_text(json.dumps(stats))
    kb = compose_kbs(roots)
    day = kb.payload_for(next(node for node in kb.nodes if node.id == "day:b"))
    assert day is not None and day["name"] == "b"
    assert [(edge.attrs["tier"], edge.attrs["_datasets"]) for edge in kb.edges] == [
        ("a", ["a"]),
        ("b", ["b"]),
    ]
