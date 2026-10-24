"""
Browser API tests against the real KB: every kind is browsable, filters and paging
behave, record views resolve every reference, errors are JSON with fitting statuses,
reloads decode with the new build's names, and load events reach SSE clients.
"""

from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
from importlib.resources import files
from typing import Any
from urllib.parse import quote

import httpx2
import uvicorn
from starlette.testclient import TestClient

from paraverse_graph.browser import COMPUTED_COLUMNS, MAX_LIMIT, create_app, redis_subscriber
from paraverse_graph.loader import events_channel
from paraverse_graph.mapping import LABELS
from paraverse_graph.review import CHECKS
from tests.kb_graph import GRAPH, loaded

# Starlette's TestClient sends `Host: testserver`, which production does not allow.
TEST_HOSTS = frozenset({"testserver"})


def _client(**kwargs: Any) -> TestClient:
    _, graph, _, _ = loaded()
    return TestClient(create_app(graph, extra_hosts=TEST_HOSTS, **kwargs))


def _get(client: TestClient, path: str) -> Any:
    response = client.get(path)
    assert response.status_code == 200, (path, response.text)
    return response.json()


def _error(client: TestClient, path: str, status: int) -> str:
    response = client.get(path)
    assert response.status_code == status, (path, response.status_code, response.text)
    assert response.headers["content-type"] == "application/json", path
    return response.json()["error"]


def _scratch_graph(name: str, *cypher: str) -> Any:
    """A small graph of its own in the test server, emptied first."""
    db, _, _, _ = loaded()
    if name in db.list_graphs():
        db.select_graph(name).delete()
    for statement in cypher:
        db.select_graph(name).query(statement)
    return db.select_graph(name)


def test_meta_lists_every_kind_with_counts():
    _, _, kb, _ = loaded()
    meta = _get(_client(), "/api/meta")
    kinds = {k["kind"]: k["count"] for group in meta["groups"] for k in group["kinds"]}
    assert kinds == kb.stats["nodes"]
    assert meta["node_total"] == sum(kb.stats["nodes"].values())


def test_every_kind_has_a_schema_and_a_first_page():
    _, _, kb, _ = loaded()
    client = _client()
    for kind, count in kb.stats["nodes"].items():
        schema = _get(client, f"/api/schema/{kind}")
        assert schema["fields"][0]["name"] == "id", kind
        for rel in schema["relationships"]:
            assert "kind" not in rel and rel["kinds"] == sorted(set(rel["kinds"])), (kind, rel)
        page = _get(client, f"/api/rows/{kind}?limit=5")
        assert page["total"] == count, kind
        assert len(page["rows"]) == min(5, count), kind
        for column in page["columns"]:
            assert column in page["rows"][0]["cells"], (kind, column)


def test_relationship_columns_list_every_target_kind():
    _, graph, _, _ = loaded()
    schema = _get(_client(), "/api/schema/person")
    accounts = next(r for r in schema["relationships"] if r["name"] == "out:HAS_ACCOUNT")
    targets = graph.ro_query(
        "MATCH (:Person)-[:HAS_ACCOUNT]->(m:Entity) RETURN DISTINCT m.entity_kind"
    ).result_set
    assert accounts["kinds"] == sorted(k for (k,) in targets)
    assert len(accounts["kinds"]) > 1


def test_every_kind_fits_on_one_page():
    _, _, kb, _ = loaded()
    client = _client()
    largest = max(kb.stats["nodes"], key=kb.stats["nodes"].get)
    assert kb.stats["nodes"][largest] <= MAX_LIMIT
    page = _get(client, f"/api/rows/{largest}?limit={MAX_LIMIT}")
    assert len(page["rows"]) == page["total"] == kb.stats["nodes"][largest]
    assert len({row["id"] for row in page["rows"]}) == page["total"]
    assert _get(client, f"/api/rows/{largest}?limit={MAX_LIMIT * 10}")["limit"] == MAX_LIMIT


def test_paging_and_sorting_are_stable():
    client = _client()
    first = _get(client, "/api/rows/repository?sort=stars&order=desc&limit=50")
    second = _get(client, "/api/rows/repository?sort=stars&order=desc&limit=50&offset=50")
    ids = [r["id"] for r in first["rows"] + second["rows"]]
    assert len(ids) == len(set(ids)) == 100
    stars = [r["cells"]["stars"] for r in first["rows"]]
    assert stars == sorted(stars, reverse=True)


def test_string_sorts_ignore_case_and_keep_nulls_last():
    client = _client()
    for order in ("asc", "desc"):
        page = _get(client, f"/api/rows/github_account?sort=login&order={order}&limit=500")
        logins = [r["cells"]["login"] for r in page["rows"]]
        assert len(logins) == page["total"]
        folded = [login.lower() for login in logins]
        assert folded == sorted(folded, reverse=order == "desc")
        # The logins mix cases, so a case-sensitive sort would order them differently.
        assert logins != sorted(logins, reverse=order == "desc")
        names = [
            r["cells"]["name"]
            for r in _get(
                client, f"/api/rows/github_account?sort=name&order={order}&cols=name&limit=500"
            )["rows"]
        ]
        present = [n for n in names if n is not None]
        assert 0 < len(present) < len(names)
        assert names[len(present) :] == [None] * (len(names) - len(present))


def test_relationship_filter_returns_only_linked_rows():
    _, graph, _, _ = loaded()
    person = graph.ro_query(
        "MATCH (p:Person)-[:PRESENTS]->(s:Session) RETURN p.id, count(s) ORDER BY count(s) DESC LIMIT 1"
    ).result_set[0]
    page = _get(_client(), f"/api/rows/session?rel=in:PRESENTS:{person[0]}&limit=500")
    assert page["total"] == person[1]
    linked = {
        row[0]
        for row in graph.ro_query(
            "MATCH (:Person {id: $id})-[:PRESENTS]->(s:Session) RETURN s.id", {"id": person[0]}
        ).result_set
    }
    assert {r["id"] for r in page["rows"]} == linked


def test_field_and_text_filters():
    _, graph, _, _ = loaded()
    client = _client()
    sessions = graph.ro_query(
        "MATCH (s:Session) RETURN s.id, s.sponsored, s.search_text"
    ).result_set
    sponsored = _get(client, "/api/rows/session?f.sponsored=true&cols=sponsored&limit=500")
    assert sponsored["total"] == sum(1 for _, flag, _ in sessions if flag is True) > 0
    assert all(r["cells"]["sponsored"] is True for r in sponsored["rows"])
    titled = _get(client, "/api/rows/session?q=CoPilot&limit=500")
    matching = {i for i, _, text in sessions if "copilot" in (text or "").lower()}
    assert titled["total"] == len(matching) > 0
    assert {r["id"] for r in titled["rows"]} == matching


def test_filters_use_the_stored_types():
    _, graph, _, _ = loaded()
    client = _client()

    def stored(label: str, prop: str) -> list[Any]:
        return [v for (v,) in graph.ro_query(f"MATCH (n:{label}) RETURN n.{prop}").result_set]

    cases = (
        ("session?f.in_person=true", [v is True for v in stored("Session", "in_person")]),
        ("session?f.virtual=FALSE", [v is False for v in stored("Session", "virtual")]),
        ("session?f.slot_count=2", [v == 2 for v in stored("Session", "slot_count")]),
        (
            "person?f.participation_roles=speaker",
            ["speaker" in (v or []) for v in stored("Person", "participation_roles")],
        ),
        (
            "organization?f.roles=sponsor",
            ["sponsor" in (v or []) for v in stored("Organization", "roles")],
        ),
    )
    for path, hits in cases:
        assert _get(client, f"/api/rows/{path}&limit=1")["total"] == sum(hits) > 0, path


def test_computed_column_types_match_stored_values():
    _, graph, _, _ = loaded()
    python_types = {"string": str, "integer": int, "boolean": bool}
    for kind, columns in COMPUTED_COLUMNS.items():
        for name, computed in columns.items():
            values = [
                v
                for (v,) in graph.ro_query(
                    f"MATCH (n:{LABELS[kind]}) WHERE n.{name} IS NOT NULL RETURN n.{name}"
                ).result_set
            ]
            assert values, (kind, name)
            for value in values:
                assert isinstance(value, list) == computed.is_list, (kind, name, value)
                items = value if isinstance(value, list) else [value]
                assert all(type(i) is python_types[computed.type] for i in items), (kind, value)


def test_unfilterable_fields_and_bad_values_are_rejected():
    client = _client()
    for query in (
        "f.hosts=org:github",
        "f.slots=x",
        "f.event=event:universe-2026",
        "f.sponsored=banana",
        "f.sponsored=1",
        "f.slot_count=two",
        "f.slot_count=99999999999999999999999",
        "f.bogus=1",
    ):
        assert _error(client, f"/api/rows/session?{query}", 400), query
    assert "rel=" in _error(client, "/api/rows/session?f.hosts=org:github", 400)


def test_rows_fetch_only_what_the_cells_need():
    _, graph, _, _ = loaded()
    app = create_app(graph, extra_hosts=TEST_HOSTS)
    client = TestClient(app)
    catalog = app.state.catalog
    queries: list[str] = []
    make_reader = catalog.reader

    class Recorder:
        def __init__(self) -> None:
            self.reader: Any = make_reader()

        def ro_query(self, q: str, params: Any = None, timeout: int | None = None) -> Any:
            queries.append(q)
            return self.reader.ro_query(q, params, timeout)

    catalog.reader = Recorder
    stored = {
        i: (title, in_person, slots)
        for i, title, in_person, slots in graph.ro_query(
            "MATCH (s:Session) RETURN s.id, s.title, s.in_person, s.slot_count"
        ).result_set
    }
    page = _get(client, "/api/rows/session?cols=in_person,slot_count,out:HELD_IN,in_person")
    assert page["columns"] == ["in_person", "slot_count", "out:HELD_IN"]
    [page_query] = [q for q in queries if "SKIP" in q]
    assert "doc" not in page_query and "properties(" not in page_query
    for row in page["rows"]:
        assert [row["cells"]["in_person"], row["cells"]["slot_count"]] == list(
            stored[row["id"]][1:]
        )
    queries.clear()
    page = _get(client, "/api/rows/session?cols=title,hosts")
    [page_query] = [q for q in queries if "SKIP" in q]
    assert "n.doc" in page_query and "properties(" not in page_query
    assert all(row["cells"]["title"] == stored[row["id"]][0] for row in page["rows"])


def test_entity_and_card_resolve_every_kind():
    _, graph, _, _ = loaded()
    client = _client()
    sample = graph.ro_query(
        "MATCH (n:Entity) WITH n.entity_kind AS kind, collect(n.id)[0] AS id RETURN id"
    ).result_set
    for (entity_id,) in sample:
        body = _get(client, f"/api/entity/{entity_id}")
        assert body["id"] == entity_id and body["doc"]
        for ref, info in body["refs"].items():
            assert info["kind"] is not None or ref.split(":")[0] == "org", ref
        for group in body["relationships"]["out"] + body["relationships"]["in"]:
            assert group["count"] >= len(group["items"]) > 0
        card = _get(client, f"/api/card/{entity_id}")
        assert card["id"] == entity_id and card["kind"] == body["kind"] and card["title"]


def test_card_and_search():
    client = _client()
    card = _get(client, "/api/card/org:github")
    assert card["name"] and card["kind"] == "organization"
    hits = _get(client, "/api/search?q=copilot&limit=10")["hits"]
    assert hits and all(h["id"] and h["kind"] for h in hits)
    sessions_only = _get(client, "/api/search?q=copilot&kinds=session")["hits"]
    assert sessions_only and {h["kind"] for h in sessions_only} == {"session"}


def test_search_text_never_breaks_the_query():
    client = _client()
    plain = [h["id"] for h in _get(client, "/api/search?q=copilot&limit=50")["hits"]]
    assert plain
    # Syntax around a word is ignored, including `-`, which would otherwise negate it.
    for q in (
        "copilot -",
        "-copilot",
        '"copilot"',
        "(copilot)",
        "copilot|",
        "@copilot",
        "copilot%",
    ):
        hits = _get(client, f"/api/search?q={quote(q)}&limit=50")["hits"]
        assert [h["id"] for h in hits] == plain, q
    for q in ('"', "(", "|", "-", "%", "{", "*", "\\", "'", "😀", "x:y", "$x", "~x", "\x00"):
        assert isinstance(_get(client, f"/api/search?q={quote(q)}")["hits"], list), q
        response = client.get(f"/api/query/search?q={quote(q)}")
        assert response.status_code in (200, 400), (q, response.text)
    named = _get(client, f"/api/query/search?q={quote('copilot -')}&limit=50")
    assert [row[0] for row in named["rows"]] == plain
    assert "nothing to search for" in _error(client, f"/api/query/search?q={quote('(')}", 400)


def test_review_runs_once_per_load():
    _, graph, _, _ = loaded()
    app = create_app(graph, extra_hosts=TEST_HOSTS)
    client = TestClient(app)
    catalog = app.state.catalog
    checks = _get(client, "/api/review")["checks"]
    assert {c["name"] for c in checks} == {c.name for c in CHECKS}
    cached = catalog.review()
    # A second page view, with its load-stamp check, reuses the same results.
    _get(client, "/api/review")
    assert catalog.review() is cached
    for check in checks:
        body = _get(client, f"/api/review/{check['name']}")
        assert body["count"] == len(body["rows"])
        assert {k: v for k, v in body.items() if k != "rows"} == check
    catalog.invalidate()
    assert catalog.review() is not cached


def test_slow_queries_time_out_as_503():
    _, graph, _, _ = loaded()
    hubs = graph.ro_query(
        """
        MATCH (n:Entity)--(m) WHERE NOT n:Event AND NOT n:Day AND NOT n:Facet
        RETURN n.id, count(m) AS degree ORDER BY degree DESC LIMIT 2
        """
    ).result_set
    path = f"/api/query/connecting_paths?a={hubs[0][0]}&b={hubs[1][0]}"
    assert "1 ms" in _error(_client(query_timeout_ms=1), path, 503)
    assert _get(_client(), path)["rows"]


def test_bad_input_is_400_json():
    client = _client()
    for path in (
        "/api/rows/nope",
        "/api/rows/session?cols=doc",
        "/api/rows/session?sort=abstract%20DESC",
        "/api/rows/session?sort=hosts",
        "/api/rows/session?rel=in:NOT_A_TYPE:x",
        "/api/rows/session?rel=garbage",
        "/api/rows/session?rel=in:PRESENTS",
        "/api/rows/session?rel=out:PRESENTS:person:x",
        "/api/rows/session?q=%00",
        "/api/entity/%00",
        "/api/card/x%00y",
        "/api/query/entity?id=%00",
        "/api/query/nope",
        "/api/search",
        "/api/review/nope",
    ):
        assert _error(client, path, 400), path


def test_other_errors_are_json_with_fitting_statuses():
    db, graph, _, _ = loaded()
    client = _client()
    assert "nobody" in _error(client, "/api/entity/person:nobody-at-all", 404)
    _error(client, "/api/nope", 404)
    _error(client, "/static/nope.js", 404)
    response = client.post("/api/meta")
    assert response.status_code == 405 and response.json()["error"]

    # `testserver` is a test-only name; production accepts only loopback hosts.
    for foreign in (
        TestClient(create_app(graph)),
        TestClient(create_app(graph), base_url="http://evil.example"),
    ):
        assert "not permitted" in _error(foreign, "/api/meta", 421)
    assert _get(TestClient(create_app(graph), base_url="http://127.0.0.1:8766"), "/api/meta")

    if "scratch_never_loaded" in db.list_graphs():
        db.select_graph("scratch_never_loaded").delete()
    missing = TestClient(
        create_app(db.select_graph("scratch_never_loaded"), extra_hosts=TEST_HOSTS)
    )
    assert "not loaded" in _error(missing, "/api/meta", 503)
    no_meta = _scratch_graph("scratch_no_meta", "CREATE (:Session:Entity {id: 'session:a'})")
    no_meta_client = TestClient(create_app(no_meta, extra_hosts=TEST_HOSTS))
    assert "GraphMeta" in _error(no_meta_client, "/api/meta", 503)
    assert "GraphMeta" in _error(no_meta_client, "/api/events", 503)
    no_meta.delete()

    # Any other database error is a 500 that names no FalkorDB internals.
    db.connection.set("scratch_plain_key", "not a graph")
    try:
        wrong = TestClient(
            create_app(db.select_graph("scratch_plain_key"), extra_hosts=TEST_HOSTS),
            raise_server_exceptions=False,
        )
        assert _error(wrong, "/api/meta", 500) == "database error"
    finally:
        db.connection.delete("scratch_plain_key")


def test_reloaded_graph_decodes_with_the_new_names():
    """
    falkordb-py maps label, property-key and relationship-type IDs to names with a
    cache on the `Graph` object. A reload in which other kinds come first renumbers
    all three, so a handle kept across it would mislabel every node and edge.
    """
    build = (
        "CREATE (:Session:Entity {id: 'session:a', title: 'T', abstract: 'A'})"
        "-[:HOSTS]->(:Room:Entity {id: 'room:r'})",
        "CREATE (:Person:Entity {id: 'person:x', bio: 'B'})-[:MENTIONS]->(:Room:Entity {id: 'room:q'})",
    )
    graph = _scratch_graph("scratch_reload", *build)
    client = TestClient(create_app(graph, extra_hosts=TEST_HOSTS))

    def neighborhood() -> tuple[set[str], dict[str, Any], list[str]]:
        body = _get(client, "/api/query/neighborhood?id=session:a")
        node = body["rows"][0][0]
        return (
            set(node["labels"]),
            node["data"],
            [link["relationship"] for link in body["graph"]["links"]],
        )

    expected = (
        {"Session", "Entity"},
        {"id": "session:a", "title": "T", "abstract": "A"},
        ["HOSTS"],
    )
    assert neighborhood() == expected
    assert _get(client, "/api/query/entity?id=session:a")["rows"][0][0]["data"] == expected[1]
    _scratch_graph("scratch_reload", *reversed(build))
    assert neighborhood() == expected
    assert _get(client, "/api/query/entity?id=session:a")["rows"][0][0]["data"] == expected[1]
    entity = _get(client, "/api/entity/session:a")
    assert set(entity["labels"]) == expected[0] and entity["properties"] == expected[1]
    graph.delete()


def test_identifiers_read_back_from_the_graph_are_not_interpolated():
    rel_stats = [
        {"from": "session", "type": "HELD_IN", "to": "room", "count": 1},
        {"from": "session", "type": "X]-() DETACH DELETE n //", "to": "room", "count": 1},
    ]
    graph = _scratch_graph(
        "scratch_forged",
        "CREATE (:Session:Entity {id: 'session:a', display_name: 'A', entity_kind: 'session'})",
    )
    graph.query(
        """
        CREATE (:GraphMeta {graph: 'g', kb_digest: 'd', loaded_at: 't', stats_json: $stats,
                            rel_stats_json: $rels})
        CREATE (:Schema {kind: 'session', label: 'Session) DETACH DELETE (x', title: 'S',
                         description: '', contract: '', fields_json: $fields, defs_json: '{}'})
        """,
        {
            "stats": json.dumps({"nodes": {"session": 1}}),
            "rels": json.dumps(rel_stats),
            "fields": json.dumps([{"name": "id", "type": "string", "list": False}]),
        },
    )
    client = TestClient(create_app(graph, extra_hosts=TEST_HOSTS))
    names = [r["name"] for r in _get(client, "/api/schema/session")["relationships"]]
    assert names == ["out:HELD_IN"]
    page = _get(client, "/api/rows/session?cols=id")
    assert [r["id"] for r in page["rows"]] == ["session:a"]
    _error(client, f"/api/rows/session?rel={quote('out:X]-() DETACH DELETE n //:x')}", 400)
    graph.delete()


def test_index_versions_assets_by_content():
    html = _client().get("/").text
    for name in ("app.js", "style.css"):
        digest = hashlib.sha256((files("paraverse_graph") / "web" / name).read_bytes()).hexdigest()
        assert f'"/static/{name}?v={digest[:12]}"' in html


def test_load_events_reach_sse_clients():
    db, graph, _, _ = loaded()
    app = create_app(graph, subscribe=redis_subscriber(db.connection, GRAPH))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    channel = events_channel(GRAPH)
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        names: list[str] = []
        events: list[dict[str, Any]] = []
        with httpx2.stream("GET", f"http://127.0.0.1:{port}/api/events", timeout=10) as response:
            for line in response.iter_lines():
                if line.startswith("event: "):
                    names.append(line.removeprefix("event: "))
                if not line.startswith("data: "):
                    continue
                events.append(json.loads(line.removeprefix("data: ")))
                if events[-1]["type"] != "hello":
                    break
                # Malformed or unknown messages are dropped without closing the stream.
                for junk in (
                    "[1, 2]",
                    "not json",
                    json.dumps({"type": "spoofed"}),
                    json.dumps({"type": 'graph.loaded\ndata: {"type": "spoofed"}\n\nevent: x'}),
                ):
                    db.connection.publish(channel, junk)
                db.connection.publish(
                    channel,
                    json.dumps(
                        {"type": "graph.loaded", "kb_digest": "x", "loaded_at": "t", "z": 1}
                    ),
                )
        meta = app.state.catalog.meta()
        assert events == [
            {"type": "hello", "kb_digest": meta["kb_digest"], "loaded_at": meta["loaded_at"]},
            {"type": "graph.loaded", "kb_digest": "x", "loaded_at": "t"},
        ]
        assert names == ["hello", "graph.loaded"]
        deadline = time.monotonic() + 5
        while app.state.bus.clients and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not app.state.bus.clients
    finally:
        server.should_exit = True
        thread.join(timeout=5)
