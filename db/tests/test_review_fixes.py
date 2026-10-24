"""Regression coverage for review findings using synthetic, isolated graphs."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pytest
from starlette.testclient import TestClient

from paraverse_graph.browser import create_app
from paraverse_graph.queries import run_query
from paraverse_graph.review import CHECKS, run_check
from tests.kb_graph import GRAPH, loaded


def _graph(suffix: str) -> Any:
    db, _, _, _ = loaded()
    name = f"{GRAPH}_review_{suffix}"
    if name in db.list_graphs():
        db.select_graph(name).delete()
    return db.select_graph(name)


def _catalog(graph: Any, kind: str, label: str) -> None:
    graph.query(
        "CREATE (:GraphMeta {kb_digest: 'v1', loaded_at: '1', stats_json: $stats, "
        "rel_stats_json: '[]'}) "
        "CREATE (:Schema {kind: $kind, label: $label, title: 'Version 1', description: '', "
        "contract: '', fields_json: $fields, defs_json: '{}'})",
        {
            "stats": json.dumps({"nodes": {kind: 3}, "edges": {}}),
            "kind": kind,
            "label": label,
            "fields": json.dumps([{"name": "id", "type": "string", "list": False}]),
        },
    )


def test_session_time_sort_uses_epochs_across_offsets():
    graph = _graph("time_sort")
    _catalog(graph, "session", "Session")
    times = ["2026-10-28T10:00:00+02:00", "2026-10-28T09:00:00Z", None]
    for i, start in enumerate(times):
        graph.query(
            "CREATE (:Session:Entity {id: $id, display_name: $id, start: $start, end: $start, "
            "start_epoch: $epoch, end_epoch: $epoch})",
            {
                "id": f"session:s{i}",
                "start": start,
                "epoch": int(datetime.fromisoformat(start).timestamp()) if start else None,
            },
        )
    client = TestClient(create_app(graph, extra_hosts=frozenset({"testserver"})))
    try:
        for field in ("start", "end"):
            for order, expected in (("asc", [0, 1, 2]), ("desc", [1, 0, 2])):
                response = client.get(f"/api/rows/session?cols=id&sort={field}&order={order}")
                assert response.status_code == 200, response.text
                assert [r["id"] for r in response.json()["rows"]] == [
                    f"session:s{i}" for i in expected
                ]
    finally:
        graph.delete()


def test_placeholder_capacity_starts_at_catalog_sentinel():
    graph = _graph("capacity")
    graph.query(
        "UNWIND [4999, 5000, 9998, 9999, 1000000] AS n "
        "CREATE (:Room:Entity {id: 'room:r' + toString(n), capacity: n})"
    )
    check = next(c for c in CHECKS if c.name == "placeholder_capacity")
    try:
        assert {r["id"] for r in run_check(graph, check)["rows"]} == {"room:r9999", "room:r1000000"}
    finally:
        graph.delete()


def test_sponsors_count_distinct_sessions_once_at_the_best_tier():
    graph = _graph("sponsors")
    graph.query(
        "CREATE (o:Sponsor:Organization:Entity {id: 'org:example', display_name: 'Example'}) "
        "CREATE (o)-[:SPONSORS {tier: 'gold'}]->(:Event) "
        "CREATE (o)-[:SPONSORS {tier: 'gold'}]->(:Event) "
        "CREATE (o)-[:SPONSORS {tier: 'silver'}]->(:Event) "
        "CREATE (o)-[:HOSTS]->(:Session {id: 'session:a'}) "
        "CREATE (o)-[:HOSTS]->(:Session {id: 'session:b'})"
    )
    try:
        assert run_query(graph, "sponsors", {})["rows"] == [["org:example", "Example", "gold", 2]]
    finally:
        graph.delete()


@pytest.mark.parametrize("endpoint", ["schema", "rows", "card", "review"])
def test_cached_endpoints_notice_reload_without_a_pubsub_event(endpoint: str):
    graph = _graph(f"fresh_{endpoint}")
    _catalog(graph, "room", "Room")
    graph.query(
        "CREATE (:Room:Entity {id: 'room:a', entity_kind: 'room', display_name: 'A', "
        "capacity: 10000, doc: '{}'})"
    )
    client = TestClient(create_app(graph, extra_hosts=frozenset({"testserver"})))
    paths = {
        "schema": "/api/schema/room",
        "rows": "/api/rows/room?cols=id",
        "card": "/api/card/room:a",
        "review": "/api/review/placeholder_capacity",
    }
    try:
        assert client.get(paths[endpoint]).status_code == 200
        graph.query(
            "MATCH (m:GraphMeta), (s:Schema), (r:Room) "
            "SET m.kb_digest = 'v2', m.loaded_at = '2', s.title = 'Version 2', "
            "s.fields_json = $fields, r.capacity = 10, r.doc = $doc",
            {
                "fields": json.dumps(
                    [
                        {"name": name, "type": "string", "list": False}
                        for name in ("id", "new_field")
                    ]
                ),
                "doc": json.dumps({"new_field": "fresh"}),
            },
        )
        path = paths[endpoint] if endpoint != "rows" else "/api/rows/room?cols=new_field"
        response = client.get(path)
        assert response.status_code == 200, response.text
        body = response.json()
        if endpoint in ("schema", "card"):
            assert body["title"] == "Version 2"
        elif endpoint == "rows":
            assert body["rows"][0]["cells"]["new_field"] == "fresh"
        else:
            assert body["count"] == 0
    finally:
        graph.delete()


def test_schedule_limits_sessions_after_aggregating_types_and_rooms():
    graph = _graph("schedule_multiplicity")
    graph.query(
        "CREATE (d:Day {id: 'day:test'}) "
        "CREATE (a:Session {id: 'session:a', code: 'A', title: 'A'}) "
        "CREATE (b:Session {id: 'session:b', code: 'B', title: 'B'}) "
        "CREATE (a)-[:SCHEDULED_ON {start: '09:00', start_epoch: 1}]->(d) "
        "CREATE (b)-[:SCHEDULED_ON {start: '10:00', start_epoch: 2}]->(d) "
        "CREATE (a)-[:HAS_TYPE]->(:Term {label: 'Workshop'}) "
        "CREATE (a)-[:HAS_TYPE]->(:Term {label: 'Talk'}) "
        "CREATE (a)-[:HELD_IN {start: '09:00'}]->(:Room {name: 'Room B'}) "
        "CREATE (a)-[:HELD_IN {start: '09:00'}]->(:Room {name: 'Room A'}) "
        "CREATE (:Person {display_name: 'Speaker A'})-[:PRESENTS]->(a)"
    )
    try:
        result = run_query(graph, "schedule", {"day": "day:test", "limit": 2})
        rows = [dict(zip(result["columns"], row, strict=True)) for row in result["rows"]]
        assert [row["session"] for row in rows] == ["session:a", "session:b"]
        assert rows[0]["type"] == "Talk"
        assert rows[0]["room"] == "Room A"
        assert rows[0]["speakers"] == ["Speaker A"]
    finally:
        graph.delete()


def test_size_review_includes_larger_bounded_ranges_and_skips_open_ended():
    graph = _graph("larger_sizes")
    graph.query(
        "UNWIND [{id: 'over', size: '51-200 employees', count: 201}, "
        "{id: 'equal', size: '51-200 employees', count: 200}, "
        "{id: 'commas', size: 'LinkedIn size range: 1,001-5,000 employees', count: 5001}, "
        "{id: 'open', size: 'LinkedIn size range: 10,001+ employees', count: 2}] AS item "
        "CREATE (o:Organization {id: 'org:' + item.id, name: item.id, size: item.size}) "
        "WITH o, item UNWIND range(1, item.count) AS n "
        "CREATE (:Person {id: o.id + ':' + toString(n)})-[:AFFILIATED_WITH {current: true}]->(o)"
    )
    graph.query(
        "CREATE (:Sponsor:Organization {id: 'org:tiny', name: 'Tiny', size: 'LinkedIn size range: 2-10 employees'})"
    )
    check = next(c for c in CHECKS if c.name == "org_size_implausible")
    try:
        assert {row["id"] for row in run_check(graph, check)["rows"]} == {
            "org:over",
            "org:commas",
            "org:tiny",
        }
    finally:
        graph.delete()
