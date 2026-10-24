"""
End-to-end tests: load the default dataset's KB into an embedded FalkorDB and
exercise the whole query catalog against it.

Expected counts come from the KB's own `_graph/stats.json` at test time, because
the KB is rebuilt from its sources and its size changes from build to build.
The swap, failure and watch tests use tiny KBs in graphs of their own, so they never
touch the shared graph.
"""

from __future__ import annotations

import json
import queue
import shutil
import threading
import time
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import pytest

from paraverse_graph.connection import delete_graph, open_db
from paraverse_graph.kb import (
    DEFAULT_DATASET,
    Artifact,
    KbEdge,
    KbError,
    KbNode,
    KnowledgeBase,
    load_kb,
)
from paraverse_graph.loader import STAGING_INFIX, LoadError, events_channel, load_graph
from paraverse_graph.mapping import LABELS
from paraverse_graph.queries import CATALOG, run_query
from paraverse_graph.review import CHECKS, ROW_LIMIT, run_check
from tests.kb_graph import GRAPH, loaded

_loaded = loaded


def _rows(name: str, **params: Any) -> list[list[Any]]:
    _, graph, _, _ = _loaded()
    return run_query(graph, name, params)["rows"]


def _first(kind: str, predicate: Any = None) -> str:
    _, _, kb, _ = _loaded()
    for node in kb.nodes:
        if node.kind == kind and (predicate is None or predicate(kb.payload_for(node) or {})):
            return node.id
    raise AssertionError(f"no {kind} in the KB")


def test_load_matches_export_counts():
    _, _, kb, report = _loaded()
    assert report.problems == []
    assert report.dataset == DEFAULT_DATASET
    assert report.nodes_by_kind == kb.stats["nodes"]
    assert report.edges_by_relation == kb.stats["edges"]
    assert set(report.nodes_by_kind) <= set(LABELS)


def test_load_judge_participation(tmp_path: Path):
    person = KbNode("person:judge", "person", "Example Judge", "people/judge.md")
    event = KbNode("event:test-2026", "event", "Test Event", "events/test-2026.md")
    evidence = [{"url": "https://example.org/event/judges"}]
    attrs = {"role": "judge", "status": "confirmed", "evidence": evidence}
    participation = {"event": event.id, **attrs}
    kb = KnowledgeBase(
        root=tmp_path,
        nodes=[person, event],
        edges=[KbEdge(person.id, "participates_in", event.id, attrs)],
        stats={"nodes": {"person": 1, "event": 1}, "edges": {"participates_in": 1}},
        artifacts={
            person.path: Artifact(
                person.path, "", "person", {"id": person.id, "participations": [participation]}
            ),
            event.path: Artifact(event.path, "", "event", {"id": event.id, "name": event.name}),
        },
        digest="judge-test",
    )
    db = open_db(tmp_path / "judge.rdb")
    try:
        report = load_graph(db, kb, "judge_test")
        assert report.problems == []
        rows = (
            db.select_graph("judge_test")
            .ro_query(
                "MATCH (p:Person:Judge:Entity)-[r:PARTICIPATES_IN]->(e:Event) "
                "RETURN p.id, p.participation_roles, p.participation_statuses, "
                "r.role, r.status, r.evidence_json, e.id"
            )
            .result_set
        )
        assert len(rows) == 1
        assert rows[0][:5] == [person.id, ["judge"], ["confirmed"], "judge", "confirmed"]
        assert json.loads(rows[0][5]) == evidence
        assert rows[0][6] == event.id
    finally:
        db.close()


def _staging_graphs(db: Any, graph_name: str) -> set[str]:
    return {g for g in db.list_graphs() if g.startswith(graph_name + STAGING_INFIX)}


def _tiny_kb(root: Path, people: int, digest: str) -> KnowledgeBase:
    """
    An in-memory KB of `people` person nodes. `root` supplies the `_schemas`.
    """
    nodes = [
        KbNode(id=f"person:p{i}", kind="person", name=f"P{i}", path=f"people/p{i}.md")
        for i in range(people)
    ]
    return KnowledgeBase(
        root=root,
        nodes=nodes,
        edges=[],
        stats={"nodes": {"person": people} if people else {}, "edges": {}},
        artifacts={
            n.path: Artifact(n.path, "", "person", {"id": n.id, "name": n.name}) for n in nodes
        },
        digest=digest,
    )


def _write_kb(kb_dir: Path, people: int, *, stats: str | None = None) -> None:
    """
    A tiny KB on disk, laid out like a KB build's output.
    """
    (kb_dir / "_graph").mkdir(parents=True)
    (kb_dir / "people").mkdir()
    rows = []
    for i in range(people):
        rows.append(
            {"id": f"person:p{i}", "kind": "person", "name": f"P{i}", "path": f"people/p{i}.md"}
        )
        (kb_dir / "people" / f"p{i}.md").write_text(
            f"---\nsoftschema:\n  contract: test:Person/v1\n  envelope: person\nperson:\n  id: person:p{i}\n  name: P{i}\n---\n"
        )
    (kb_dir / "_graph" / "nodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (kb_dir / "_graph" / "edges.jsonl").write_text("")
    default_stats = {"nodes": {"person": people} if people else {}, "edges": {}}
    (kb_dir / "_graph" / "stats.json").write_text(stats or json.dumps(default_stats))


def _swap_in_build(kb_dir: Path, people: int, *, stats: str | None = None) -> None:
    """
    Replace `kb_dir` the way a KB build does: build a sibling staging tree, then
    rename the old tree away and the new one into place.
    """
    staging = Path(mkdtemp(prefix=".kb-", dir=kb_dir.parent))
    shutil.rmtree(staging)
    _write_kb(staging, people, stats=stats)
    previous = kb_dir.with_name(f".{kb_dir.name}-previous")
    kb_dir.rename(previous)
    staging.rename(kb_dir)
    shutil.rmtree(previous)


def test_live_graph_has_indexes_and_unique_ids():
    db, graph, kb, _ = _loaded()
    assert _staging_graphs(db, GRAPH) == set()
    indexed = {
        row[0] for row in graph.ro_query("CALL db.indexes() YIELD label RETURN label").result_set
    }
    assert indexed >= set(LABELS.values()) | {"Entity"}
    constraints = graph.ro_query(
        "CALL db.constraints() YIELD type, label, properties, status RETURN type, label, properties, status"
    ).result_set
    assert ["UNIQUE", "Entity", ["id"], "OPERATIONAL"] in constraints
    # The constraint survived the RENAME swap and enforces uniqueness.
    existing = kb.nodes[0].id
    try:
        graph.query("CREATE (:Entity {id: $id})", {"id": existing})
    except Exception as e:
        assert "unique constraint" in str(e)
    else:
        graph.query(
            "MATCH (n:Entity {id: $id}) WHERE n.entity_kind IS NULL DELETE n", {"id": existing}
        )
        raise AssertionError("the live graph accepted a duplicate Entity.id")
    hits = graph.ro_query(
        "CALL db.idx.fulltext.queryNodes('Entity', 'copilot') YIELD node RETURN count(node)"
    ).result_set[0][0]
    assert hits > 0


def test_every_kind_has_a_schema_and_relationship_stats():
    _, graph, kb, _ = _loaded()
    rows = graph.ro_query("MATCH (s:Schema) RETURN s.kind, s.fields_json").result_set
    schemas = {kind: json.loads(fields) for kind, fields in rows}
    assert set(kb.stats["nodes"]) <= set(schemas)
    for kind, fields in schemas.items():
        names = [f["name"] for f in fields]
        assert names[0] == "id", kind
    meta = graph.ro_query("MATCH (m:GraphMeta) RETURN m.rel_stats_json").result_set[0][0]
    stats = json.loads(meta)
    assert sum(s["count"] for s in stats) == sum(kb.stats["edges"].values())


def test_reload_is_never_visible_to_readers_and_publishes_an_event():
    db, graph, kb, _ = _loaded()
    total = sum(kb.stats["nodes"].values())
    pubsub = db.connection.pubsub()
    pubsub.subscribe(events_channel(GRAPH))
    pubsub.get_message(timeout=1)  # The subscribe confirmation.

    # Read the live graph throughout a full reload: with an atomic swap every read
    # succeeds and sees the whole graph.
    counts: list[int] = []
    errors: list[Exception] = []
    done = threading.Event()

    def read() -> None:
        while not done.is_set():
            try:
                counts.append(graph.ro_query("MATCH (n:Entity) RETURN count(n)").result_set[0][0])
            except Exception as e:
                errors.append(e)

    reader = threading.Thread(target=read)
    reader.start()
    try:
        report = load_graph(db, kb, GRAPH)
    finally:
        done.set()
        reader.join()
    message = pubsub.get_message(timeout=5)
    pubsub.close()

    assert errors == []
    assert counts and set(counts) == {total}
    assert message
    event = json.loads(message["data"])
    assert event["type"] == "graph.loaded" and event["kb_digest"] == kb.digest
    meta = graph.ro_query("MATCH (m:GraphMeta) RETURN m.kb_digest, m.loaded_at").result_set
    assert meta == [[report.kb_digest, event["loaded_at"]]]
    assert report.kb_digest == kb.digest
    assert _staging_graphs(db, GRAPH) == set()


def test_every_property_doc_round_trips_to_the_artifact():
    _, graph, kb, _ = _loaded()
    rows = graph.ro_query("MATCH (n:Entity) RETURN n.id, n.doc").result_set
    docs = dict(rows)
    for node in kb.nodes:
        assert json.loads(docs[node.id]) == kb.payload_for(node)


def test_failed_loads_leave_the_live_graph_untouched():
    db, _, kb, _ = _loaded()
    live = f"{GRAPH}_swap"
    load_graph(db, _tiny_kb(kb.root, 2, "good"), live)
    graph = db.select_graph(live)

    def state() -> list[list[Any]]:
        return graph.ro_query(
            "MATCH (m:GraphMeta) OPTIONAL MATCH (n:Person) RETURN m.kb_digest, m.loaded_at, count(n)"
        ).result_set

    before = state()
    pubsub = db.connection.pubsub()
    pubsub.subscribe(events_channel(live))
    pubsub.get_message(timeout=1)  # The subscribe confirmation.

    real_execute = db.connection.execute_command

    def failing(command: str) -> Callable[..., Any]:
        def execute(*args: Any, **kwargs: Any) -> Any:
            if args and args[0] == command:
                raise RuntimeError(f"simulated {command} failure")
            return real_execute(*args, **kwargs)

        return execute

    # A count mismatch, a unique constraint that fails, and a failed swap: each one
    # leaves the live graph as it was and keeps its own staging graph.
    mismatch = _tiny_kb(kb.root, 3, "bad")
    mismatch.stats = {"nodes": {"person": 2}, "edges": {}}
    cases = [
        (mismatch, None, "does not match the KB"),
        (_tiny_kb(kb.root, 3, "bad"), "GRAPH.CONSTRAINT", "simulated GRAPH.CONSTRAINT"),
        (_tiny_kb(kb.root, 3, "bad"), "RENAME", "simulated RENAME"),
    ]
    try:
        for bad_kb, command, expected in cases:
            if command:
                db.connection.execute_command = failing(command)
            try:
                load_graph(db, bad_kb, live)
            except RuntimeError as e:  # `LoadError` included.
                assert expected in str(e), e
            else:
                raise AssertionError(f"load should fail: {command or 'count mismatch'}")
            finally:
                db.connection.execute_command = real_execute
            assert state() == before, command
        assert len(_staging_graphs(db, live)) == len(cases)
        assert pubsub.get_message(timeout=0.5) is None
    finally:
        pubsub.close()
        for name in _staging_graphs(db, live):
            delete_graph(db, name)

    # Two loads at once each write their own staging graph, so neither breaks the other.
    reports: list[Any] = []
    loads = [
        threading.Thread(
            target=lambda d=d: reports.append(load_graph(db, _tiny_kb(kb.root, 4, d), live))
        )
        for d in ("c1", "c2")
    ]
    for t in loads:
        t.start()
    for t in loads:
        t.join()
    try:
        assert sorted(r.kb_digest for r in reports) == ["c1", "c2"]
        assert state()[0][0] in {"c1", "c2"} and state()[0][2] == 4
        assert _staging_graphs(db, live) == set()
    finally:
        delete_graph(db, live)


def test_failed_watch_reloads_delete_their_staging_graphs():
    from paraverse_graph import cli

    db, _, _, _ = _loaded()
    name = f"{GRAPH}_watch_fail"
    kb_dir = Path(mkdtemp(prefix="paraverse-graph-watch-")) / "kb"
    _write_kb(kb_dir, 1, stats=json.dumps({"nodes": {"person": 2}, "edges": {}}))
    try:
        # Each failed reload of a broken build would otherwise leave a full graph copy.
        for _ in range(2):
            try:
                cli._reload(db, kb_dir, name)  # pyright: ignore[reportPrivateUsage]
            except LoadError as e:
                assert "does not match the KB" in str(e)
            else:
                raise AssertionError("a count mismatch should fail the reload")
        assert _staging_graphs(db, name) == set()
        assert name not in db.list_graphs()
    finally:
        for graph in _staging_graphs(db, name):
            delete_graph(db, graph)


def test_watch_reloads_after_the_build_swaps_kb_by_rename():
    from paraverse_graph import cli

    db, _, _, _ = _loaded()
    name = f"{GRAPH}_watch"
    kb_dir = Path(mkdtemp(prefix="paraverse-graph-watch-")) / "kb"
    _write_kb(kb_dir, 1)
    attempts: queue.Queue[Exception | None] = queue.Queue()

    def reload() -> None:
        try:
            load_graph(db, load_kb(kb_dir), name)
        except Exception as e:
            attempts.put(e)
            raise
        attempts.put(None)

    stop = threading.Event()
    watcher = threading.Thread(
        target=cli.watch_kb,
        args=(kb_dir, stop, reload),
        kwargs={"seen": cli.kb_signature(kb_dir), "debounce_ms": 100, "poll_ms": 200},
        daemon=True,
    )
    watcher.start()
    try:
        # A broken build fails to load; the watch logs it and keeps going.
        _swap_in_build(kb_dir, 1, stats="{")
        assert isinstance(attempts.get(timeout=10), KbError)
        _swap_in_build(kb_dir, 2)
        assert attempts.get(timeout=10) is None
        assert watcher.is_alive()
        graph = db.select_graph(name)
        meta = graph.ro_query(
            "MATCH (m:GraphMeta) MATCH (p:Person) RETURN m.kb_digest, count(p)"
        ).result_set
        assert meta == [[load_kb(kb_dir).digest, 2]]
        assert attempts.empty()
    finally:
        stop.set()
        watcher.join(timeout=5)
        delete_graph(db, name)
    assert not watcher.is_alive()


def test_watch_retries_a_build_that_failed_to_load():
    from paraverse_graph import cli

    db, _, _, _ = _loaded()
    name = f"{GRAPH}_watch_retry"
    kb_dir = Path(mkdtemp(prefix="paraverse-graph-watch-")) / "kb"
    _write_kb(kb_dir, 1)
    attempts: queue.Queue[Exception | None] = queue.Queue()

    def reload() -> None:
        try:
            cli._reload(db, kb_dir, name)  # pyright: ignore[reportPrivateUsage]
        except Exception as e:
            attempts.put(e)
            raise
        attempts.put(None)

    stop = threading.Event()
    watcher = threading.Thread(
        target=cli.watch_kb,
        args=(kb_dir, stop, reload),
        kwargs={"seen": cli.kb_signature(kb_dir), "debounce_ms": 100, "poll_ms": 200},
        daemon=True,
    )
    watcher.start()
    try:
        # The watch reads a build whose `stats.json` landed before the rest of it.
        _swap_in_build(kb_dir, 1, stats=json.dumps({"nodes": {"person": 2}, "edges": {}}))
        assert isinstance(attempts.get(timeout=10), LoadError)
        # The rest lands in place, with no further `stats.json` change to wake the watch.
        complete = Path(mkdtemp(prefix="paraverse-graph-watch-")) / "kb"
        _write_kb(complete, 2)
        shutil.copytree(complete / "people", kb_dir / "people", dirs_exist_ok=True)
        shutil.copy(complete / "_graph" / "nodes.jsonl", kb_dir / "_graph" / "nodes.jsonl")
        while (result := attempts.get(timeout=10)) is not None:
            assert isinstance(result, (KbError, LoadError)), result
        graph = db.select_graph(name)
        assert graph.ro_query("MATCH (p:Person) RETURN count(p)").result_set == [[2]]
    finally:
        stop.set()
        watcher.join(timeout=5)
        delete_graph(db, name)
    assert not watcher.is_alive()


def test_watch_backs_off_from_a_build_that_keeps_failing(tmp_path: Path):
    from paraverse_graph import cli

    kb_dir = tmp_path / "kb"
    _write_kb(kb_dir, 1)
    calls: list[float] = []

    def reload() -> None:
        calls.append(time.monotonic())
        raise RuntimeError("simulated broken build")

    stop = threading.Event()
    watcher = threading.Thread(
        target=cli.watch_kb,
        args=(kb_dir, stop, reload),
        kwargs={"seen": None, "debounce_ms": 50, "poll_ms": 100},
        daemon=True,
    )
    watcher.start()
    time.sleep(2.5)
    stop.set()
    watcher.join(timeout=5)
    assert not watcher.is_alive()
    # Retried, but at doubling intervals (0.1, 0.2, 0.4, 0.8 s ...), not on every poll.
    assert 3 <= len(calls) <= 8, calls
    gaps = [b - a for a, b in pairwise(calls)]
    assert gaps[-1] > 2 * gaps[0], gaps


def test_reload_rejects_schema_changes_before_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from paraverse_graph import loader
    from paraverse_graph.schemas import load_kind_schemas

    db, _, _, _ = _loaded()
    name = f"{GRAPH}_schema_changed"
    root = tmp_path / "kb"
    _write_kb(root, 1)
    load_graph(db, load_kb(root), name)
    original = load_kind_schemas

    def read_then_change(kb_root: Path) -> Any:
        schemas = original(kb_root)
        (kb_root / "_schemas").mkdir()
        (kb_root / "_schemas" / "person.schema.yaml").write_text("type: object\n")
        return schemas

    monkeypatch.setattr(loader, "load_kind_schemas", read_then_change)
    try:
        with pytest.raises(KbError, match="changed while reading"):
            load_graph(db, load_kb(root), name, keep_failed=False)
        assert db.select_graph(name).ro_query("MATCH (p:Person) RETURN count(p)").result_set == [
            [1]
        ]
        assert not _staging_graphs(db, name)
    finally:
        delete_graph(db, name)


def test_every_catalog_query_runs():
    person = _first("person", lambda p: p.get("sessions"))
    term = _first("term")
    day = _first("day")
    org = _first("organization", lambda p: "sponsor" in p.get("roles", []))
    params: dict[str, dict[str, Any]] = {
        "entity": {"id": person},
        "neighborhood": {"id": person},
        "search": {"q": "copilot"},
        "schedule": {"day": day},
        "sessions_for_term": {"term": term},
        "person_card": {"id": person},
        "person_repositories": {"id": person},
        "similar_people": {"id": person},
        "connecting_paths": {"a": person, "b": org},
        "organization_card": {"id": org},
    }
    _, graph, _, _ = _loaded()
    for name in CATALOG:
        result = run_query(graph, name, params.get(name, {}))
        assert result["columns"], name


def test_person_card_graph_matches_the_artifact():
    person = _first("person", lambda p: p.get("sessions"))
    _, graph, kb, _ = _loaded()
    payload = next(kb.payload_for(n) for n in kb.nodes if n.id == person) or {}
    result = run_query(graph, "person_card", {"id": person})
    linked = {
        link["target"] for link in result["graph"]["links"] if link["relationship"] == "PRESENTS"
    }
    assert linked == {s["session"] for s in payload["sessions"]}


def test_schedule_is_ordered_and_complete():
    _, _, kb, _ = _loaded()
    for day in (n.id for n in kb.nodes if n.kind == "day"):
        rows = _rows("schedule", day=day)
        expected = sum(1 for e in kb.edges if e.relation == "scheduled_on" and e.target == day)
        assert len(rows) == expected
        starts = [row[0] for row in rows]
        assert starts == sorted(starts)


def test_similar_people_only_suggests_people_the_event_published():
    _, graph, _, _ = _loaded()
    person = _first("person", lambda p: p.get("sessions"))
    rows = _rows("similar_people", id=person, limit=50)
    assert rows
    for row in rows:
        basis = graph.ro_query(
            "MATCH (p:Person {id: $id}) RETURN p.inclusion_basis", {"id": row[0]}
        ).result_set[0][0]
        assert basis == "published_by_event"


def test_connecting_paths_avoid_hubs():
    person = _first("person", lambda p: p.get("sessions"))
    org = _first("organization", lambda p: "sponsor" in p.get("roles", []))
    _, graph, _, _ = _loaded()
    result = run_query(graph, "connecting_paths", {"a": person, "b": org, "limit": 25})
    hubs = {"Event", "Day", "Facet"}
    for node in result["graph"]["nodes"]:
        assert not hubs & set(node["labels"])


def test_review_checks_bind_the_row_limit_and_link_to_entities():
    _, graph, _, _ = _loaded()
    ids = {row[0] for row in graph.ro_query("MATCH (n:Entity) RETURN n.id").result_set}
    for check in CHECKS:
        assert check.cypher.endswith("LIMIT $limit"), check.name
        result = run_check(graph, check)
        assert len(result["rows"]) == result["count"] <= ROW_LIMIT, check.name
        assert {row["id"] for row in result["rows"]} <= ids, check.name


def test_org_prefix_check_pairs_names_that_extend_at_a_separator():
    db, _, _, _ = _loaded()
    graph = db.select_graph(f"{GRAPH}_orgs")
    orgs = [
        ["org:otto", "Otto"],
        ["org:otto-gmbh", "Otto GmbH & Co KG"],
        ["org:ottoman", "Ottoman Holdings"],
        ["org:pendo", "Pendo"],
        ["org:pendo-io", "pendo.io"],
        ["org:cathay", "Cathay Pacific"],
        ["org:cathay-airways", "Cathay Pacific Airways"],
        ["org:acme", "Acme"],
        ["org:acme-inc", "Acme, Inc."],
        ["org:acme-labs", "Acme Labs"],
    ]
    graph.query(
        "UNWIND $orgs AS o CREATE (:Organization:Entity {id: o[0], name: o[1]})", {"orgs": orgs}
    )
    graph.query(
        "MATCH (a:Organization {id: 'org:acme'}), (b:Organization {id: 'org:acme-labs'}) "
        "CREATE (a)-[:RELATED_TO]->(b)"
    )
    graph.query(
        "CREATE (p:Person:Entity {id: 'person:x'}) WITH p MATCH (o:Organization) "
        "WHERE o.id IN ['org:otto', 'org:otto-gmbh'] CREATE (p)-[:AFFILIATED_WITH]->(o)"
    )
    check = next(c for c in CHECKS if c.name == "org_name_prefix_duplicates")
    try:
        rows = run_check(graph, check)["rows"]
    finally:
        graph.delete()
    assert {r["id"]: r["detail"] for r in rows} == {
        "org:acme-inc": "possible duplicate of org:acme (Acme); people affiliated with both: 0",
        "org:cathay-airways": "possible duplicate of org:cathay (Cathay Pacific); people affiliated with both: 0",
        "org:otto-gmbh": "possible duplicate of org:otto (Otto); people affiliated with both: 1",
        "org:pendo-io": "possible duplicate of org:pendo (Pendo); people affiliated with both: 0",
    }


@pytest.mark.parametrize("missing", ["root", "nested"])
def test_unresolved_node_payload_cannot_replace_the_live_graph(missing: str, tmp_path: Path):
    root = tmp_path / "kb"
    (root / "_schemas").mkdir(parents=True)
    (root / "_schemas/person.schema.yaml").write_text(
        json.dumps(
            {
                "type": "object",
                "title": "Person",
                "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
            }
        )
    )
    db = open_db(tmp_path / "live.rdb")
    live = "unresolved_payload_test"
    load_graph(db, _tiny_kb(root, 1, "good"), live)
    graph = db.select_graph(live)

    def state() -> list[list[Any]]:
        return graph.ro_query(
            "MATCH (m:GraphMeta) OPTIONAL MATCH (n:Entity) RETURN m.kb_digest, count(n)"
        ).result_set

    before = state()
    bad = _tiny_kb(root, 1, "bad")
    if missing == "root":
        bad.artifacts["people/p0.md"].payload["id"] = "person:other"
    else:
        node = KbNode("term:level/missing", "term", "Missing", "taxonomy/level.yaml")
        bad.nodes.append(node)
        bad.artifacts[node.path] = Artifact(
            node.path,
            "test:Facet/v1",
            "facet",
            {"id": "level", "terms": [{"id": "term:level/known", "label": "Known"}]},
        )
        bad.stats["nodes"]["term"] = 1
    try:
        with pytest.raises(KbError, match="no matching payload"):
            load_graph(db, bad, live, keep_failed=False)
        assert state() == before
        assert _staging_graphs(db, live) == set()
    finally:
        delete_graph(db, live)


@pytest.mark.parametrize("form", ["explicit", "inferred", "unwrapped", "yaml_marker"])
def test_load_kb_accepts_the_supported_softschema_forms(form: str, tmp_path: Path):
    kb_dir = tmp_path / "kb"
    _write_kb(kb_dir, 1)
    metadata = "softschema:\n  contract: test:Person/v1\n"
    payload = "  id: person:p0\n  name: P0\n"
    if form == "explicit":
        text = f"---\n{metadata}  envelope: person\nperson:\n{payload}---\n"
    elif form == "inferred":
        text = f"---\n{metadata}person:\n{payload}---\n"
    else:
        text = metadata + "id: person:p0\nname: P0\n"
        if form == "yaml_marker":
            text = "---\n" + text
        (kb_dir / "people/p0.md").rename(kb_dir / "people/p0.yaml")
        nodes = kb_dir / "_graph/nodes.jsonl"
        nodes.write_text(nodes.read_text().replace("p0.md", "p0.yaml"))
    path = kb_dir / ("people/p0.md" if form in {"explicit", "inferred"} else "people/p0.yaml")
    path.write_text(text)
    kb = load_kb(kb_dir)
    assert kb.payload_for(kb.nodes[0]) == {"id": "person:p0", "name": "P0"}
    assert kb.artifacts[kb.nodes[0].path].envelope == "person"


@pytest.mark.parametrize("ambiguity", ["frontmatter", "graph_kinds"])
def test_load_kb_rejects_ambiguous_implicit_payloads(ambiguity: str, tmp_path: Path):
    kb_dir = tmp_path / "kb"
    _write_kb(kb_dir, 1)
    if ambiguity == "frontmatter":
        (kb_dir / "people/p0.md").write_text(
            "---\nsoftschema:\n  contract: test:Person/v1\ntitle: P0\n"
            "person:\n  id: person:p0\n  name: P0\n---\n"
        )
    else:
        nodes = kb_dir / "_graph/nodes.jsonl"
        extra = {"id": "org:o0", "kind": "organization", "path": "people/p0.md"}
        nodes.write_text(nodes.read_text() + json.dumps(extra) + "\n")
    with pytest.raises(KbError, match=r"ambiguous|incompatible"):
        load_kb(kb_dir)
