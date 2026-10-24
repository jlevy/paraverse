"""Overview behavior over a synthetic load, including provenance and reloads."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from paraverse_graph.browser import create_app
from paraverse_graph.connection import delete_graph, open_db
from paraverse_graph.kb import Artifact, KbEdge, KbNode, KnowledgeBase
from paraverse_graph.loader import load_graph
from paraverse_graph.overview import build_overview
from paraverse_graph.review import Check, run_check
from paraverse_graph.selection import DatasetSelection
from tests.test_selection import source


def _kb(root: Path, *, updated: bool = False, extra_person: bool = False) -> KnowledgeBase:
    root.mkdir(exist_ok=True)
    records: dict[str, tuple[str, dict[str, Any]]] = {
        "event:one": (
            "event",
            {
                "name": "Example Conference",
                "edition": "2026",
                "start": "2026-10-01T17:00:00-07:00",
                "end": "2026-10-02T17:00:00-07:00",
                "sources": [
                    {
                        "system": "event_api",
                        "url": "https://example.org/program",
                        "retrieved_at": "2026-01-01T23:00:00-08:00",
                        "snapshot": "excluded-source-location",
                    }
                ],
            },
        ),
        "event:two": ("event", {"name": "Example Conference", "edition": "2025"}),
        "session:one": (
            "session",
            {
                # The graph export, rather than a conflicting payload, assigns editions.
                "event": "event:two",
                "slots": [{"start": "2026-10-01T09:00:00Z", "end": "2026-10-01T10:00:00Z"}],
                "sources": [
                    {
                        "system": "event_api",
                        "url": "https://example.org/program",
                        "retrieved_at": "2026-01-02T06:30:00Z",
                    },
                    {"system": "event_api", "retrieved_at": "invalid-date"},
                ],
            },
        ),
        "session:two": (
            "session",
            {
                "slots": [{"start": "2026-10-01T09:00:00Z"}],
                "sources": [
                    {"system": "github", "retrieved_at": "2026-01-03T00:00:00Z"},
                    {},
                    "malformed-citation",
                ],
            },
        ),
        "session:three": ("session", {"sources": {"system": "github"}}),
        "session:four": (
            "session",
            {
                "slots": [{"start": "2026-10-01T09:00:00Z", "end": "2026-10-01T10:00:00Z"}],
                "sources": [],
            },
        ),
        "person:one": (
            "person",
            {
                "inclusion_basis": "published_by_event",
                "private_note": "excluded-payload-text",
                "sources": [
                    {"system": "github", "url": "https://example.org/work"},
                    {"system": "github", "url": "https://example.org/work"},
                ],
            },
        ),
        "person:two": ("person", {"inclusion_basis": "public_self_report"}),
        "person:three": ("person", {}),
        "person:four": ("person", {"inclusion_basis": "curated"}),
        "profile:one": (
            "profile",
            {"brief_bio": {"text": "Example professional bio.", "stale": False}},
        ),
        "profile:two": (
            "profile",
            {
                "brief_bio": {"text": "Example professional bio.", "stale": True},
                "expertise": [{"label": "Example expertise"}],
            },
        ),
        "profile:three": (
            "profile",
            {"brief_bio": {"text": "Example professional bio."}, "interests": []},
        ),
        "profile:four": ("profile", {"brief_bio": {"text": "  "}}),
        "acct:one": ("social_account", {"details_fetched": True}),
        "acct:two": ("social_account", {"details_fetched": updated}),
        "acct:three": ("social_account", {}),
        "acct:four": ("social_account", {"details_fetched": "true"}),
        "day:one": ("day", {}),
        "org:one": ("organization", {}),
    }
    if updated:
        records["person:three"] = ("person", {"inclusion_basis": "opted_in"})
    if extra_person:
        records["person:five"] = ("person", {"inclusion_basis": "curated"})
    nodes = [
        KbNode(id=id_, kind=kind, name=id_, path=f"records/{index}.yaml")
        for index, (id_, (kind, _)) in enumerate(records.items())
    ]
    artifacts = {
        node.path: Artifact(
            node.path, "example:v1", node.kind, {"id": node.id, **records[node.id][1]}
        )
        for node in nodes
    }
    edges = [
        KbEdge(f"session:{name}", "part_of", f"event:{edition}")
        for name, edition in (("one", "one"), ("two", "one"), ("three", "two"), ("four", "two"))
    ] + [
        KbEdge("person:one", "presents", "session:one"),
        KbEdge("person:one", "has_account", "acct:one"),
        KbEdge("org:one", "has_account", "acct:four"),
    ]
    return KnowledgeBase(
        root=root,
        nodes=nodes,
        edges=edges,
        stats={
            "nodes": dict(Counter(node.kind for node in nodes)),
            "edges": dict(Counter(edge.relation for edge in edges)),
        },
        artifacts=artifacts,
        # Payloads can change while the node/edge export identity stays the same.
        digest="synthetic-export-plus" if extra_person else "synthetic-export",
    )


def _get(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/overview")
    assert response.status_code == 200, response.text
    return response.json()


def test_overview_summarizes_counts_provenance_and_explicit_coverage(
    tmp_path: Path, monkeypatch: Any
):
    import paraverse_graph.browser as browser

    def unexpected_review(*_: Any) -> None:
        raise AssertionError("Overview must not run the quality checks")

    monkeypatch.setattr(browser, "run_check", unexpected_review)
    db = open_db(tmp_path / "overview.rdb")
    graph = db.select_graph("overview")
    try:
        load_graph(db, _kb(tmp_path / "kb"), graph.name)
        result = _get(TestClient(create_app(graph, extra_hosts=frozenset({"testserver"}))))
        assert result["totals"] == {
            "entities": 20,
            "relationships": 7,
            "entity_kinds": 7,
            "relationship_types": 3,
        }
        entities = {row["kind"]: row for row in result["entities"]}
        assert entities["person"] == {
            "kind": "person",
            "title": "Person",
            "group": "People",
            "count": 4,
        }
        assert entities["session"]["group"] == "Program"
        relationships = {row["type"]: row for row in result["relationships"]}
        assert relationships["HAS_ACCOUNT"] == {
            "type": "HAS_ACCOUNT",
            "count": 2,
            "from": ["organization", "person"],
            "to": ["social_account"],
        }
        assert {row["id"]: row["sessions"] for row in result["editions"]} == {
            "event:one": 2,
            "event:two": 2,
        }
        edition = next(row for row in result["editions"] if row["id"] == "event:one")
        assert edition["edition"] == "2026"
        assert edition["start"] == "2026-10-01T17:00:00-07:00"
        assert edition["end"] == "2026-10-02T17:00:00-07:00"
        sources = result["sources"]
        assert sources["entities_with_sources"] == 4
        assert sources["entities_without_sources"] == 16
        assert sources["source_references"] == 6
        assert sources["unique_urls"] == 2
        assert sources["latest_retrieved_at"] == "2026-01-03T00:00:00Z"
        assert sources["providers"] == [
            {
                "source": "event_api",
                "entities": 2,
                "references": 3,
                "latest_retrieved_at": "2026-01-02T07:00:00Z",
            },
            {
                "source": "github",
                "entities": 2,
                "references": 3,
                "latest_retrieved_at": "2026-01-03T00:00:00Z",
            },
        ]
        coverage = {row["key"]: row for row in result["coverage"]}
        assert coverage["source_citations"]["unknown"] == 2
        assert {
            key: coverage["profile_brief_bio"][key]
            for key in ("total", "present", "missing", "stale", "unknown")
        } == {"total": 4, "present": 3, "missing": 1, "stale": 1, "unknown": 1}
        assert {
            key: coverage["social_details"][key]
            for key in ("total", "present", "missing", "not_fetched", "unknown")
        } == {"total": 4, "present": 1, "missing": 3, "not_fetched": 1, "unknown": 2}
        assert coverage["session_schedule"]["present"] == 2
        assert coverage["session_schedule"]["missing"] == 2
        assert result["participation"] == [
            {"basis": "curated", "count": 1},
            {"basis": "public_self_report", "count": 1},
            {"basis": "published_by_event", "count": 1},
            {"basis": "unknown", "count": 1},
        ]
        serialized = str(result)
        assert all(
            value not in serialized
            for value in (
                str(tmp_path),
                "excluded-payload-text",
                "excluded-source-location",
                "https://example.org",
                "Example professional bio.",
            )
        )
        assert set(result["load"]) == {"graph", "dataset", "kb_digest", "loaded_at", "load_id"}
    finally:
        delete_graph(db, graph.name)


def test_overview_accepts_offset_free_dates_and_times_as_utc(tmp_path: Path):
    kb = _kb(tmp_path / "kb")
    payloads = {artifact.payload["id"]: artifact.payload for artifact in kb.artifacts.values()}
    # Conflicting labels ensure dates, rather than edition labels, determine order.
    payloads["event:one"].update(edition="9999", start="2025-12-30", end="2025-12-31")
    payloads["event:two"].update(edition="0000", start="2026-01-01T09:00:00", end="2026-02-30")
    payloads["session:one"]["sources"] = [
        {"system": "event_api", "retrieved_at": "2026-01-02T07:30:00"},
        {"system": "event_api", "retrieved_at": "2026-02-30"},
    ]
    payloads["session:two"]["sources"].extend(
        [
            {"system": "github", "retrieved_at": "2026-01-04"},
            {"system": "github", "retrieved_at": 20260105},
        ]
    )
    payloads["session:one"]["slots"] = [
        {"start": "2026-10-01T09:00:00", "end": "2026-10-01T10:00:00Z"}
    ]
    payloads["session:two"]["slots"] = [{"start": "2026-10-01", "end": "2026-10-02"}]
    payloads["session:three"]["slots"] = [
        {"start": "2026-10-01T09:00:00", "end": "2026-10-01T09:00:00Z"},
        {"start": "2026-02-30", "end": "2026-10-01"},
        {"start": None, "end": "2026-10-01"},
    ]
    payloads["session:four"]["slots"] = [{"start": "2026-10-02", "end": "2026-10-01"}]
    db = open_db(tmp_path / "dates.rdb")
    graph = db.select_graph("overview_dates")
    try:
        load_graph(db, kb, graph.name)
        result = _get(TestClient(create_app(graph, extra_hosts=frozenset({"testserver"}))))
        observed = {
            "editions": [(row["id"], row["start"], row["end"]) for row in result["editions"]],
            "providers": {
                row["source"]: row["latest_retrieved_at"] for row in result["sources"]["providers"]
            },
            "latest": result["sources"]["latest_retrieved_at"],
            "scheduled": next(
                row["present"] for row in result["coverage"] if row["key"] == "session_schedule"
            ),
        }
        assert observed == {
            "editions": [
                ("event:two", "2026-01-01T09:00:00", None),
                ("event:one", "2025-12-30", "2025-12-31"),
            ],
            "providers": {"event_api": "2026-01-02T07:30:00Z", "github": "2026-01-04T00:00:00Z"},
            "latest": "2026-01-04T00:00:00Z",
            "scheduled": 2,
        }
    finally:
        delete_graph(db, graph.name)


def test_overview_caches_per_load_and_refreshes_without_a_pubsub_event(
    tmp_path: Path, monkeypatch: Any
):
    import paraverse_graph.browser as browser

    class FixedClock:
        @staticmethod
        def now(_tz: Any) -> datetime:
            return datetime(2026, 1, 1, tzinfo=UTC)

    monkeypatch.setattr("paraverse_graph.loader.datetime", FixedClock)
    db = open_db(tmp_path / "cache.rdb")
    graph = db.select_graph("overview_cache")
    try:
        load_graph(db, _kb(tmp_path / "kb"), graph.name)
        calls = 0
        aggregate = build_overview

        def counted(*args: Any) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return aggregate(*args)

        monkeypatch.setattr(browser, "build_overview", counted)
        app = create_app(graph, extra_hosts=frozenset({"testserver"}))
        client = TestClient(app)
        first = _get(client)
        assert _get(client) == first
        assert calls == 1
        load_graph(db, _kb(tmp_path / "kb", updated=True), graph.name)
        second = _get(client)
        assert calls == 2
        assert second["load"]["load_id"] != first["load"]["load_id"]
        assert second["load"]["kb_digest"] == first["load"]["kb_digest"]
        assert second["load"]["loaded_at"] == first["load"]["loaded_at"]
        assert second["totals"]["entities"] == 20
        assert (
            next(row for row in second["coverage"] if row["key"] == "social_details")["present"]
            == 2
        )
        assert {row["basis"]: row["count"] for row in second["participation"]}["opted_in"] == 1
        assert _get(client) == second
        assert calls == 2
        app.state.catalog.invalidate()
        assert _get(client) == second
        assert calls == 3
    finally:
        delete_graph(db, graph.name)


def test_overview_retries_a_reload_and_rejects_continuous_invalidation(
    tmp_path: Path, monkeypatch: Any
):
    import paraverse_graph.browser as browser

    db = open_db(tmp_path / "race.rdb")
    graph = db.select_graph("overview_race")
    try:
        load_graph(db, _kb(tmp_path / "kb"), graph.name)
        aggregate = build_overview
        calls = 0

        def counted(*args: Any) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return aggregate(*args)

        read_query = browser.GraphReader.ro_query
        reloaded = False

        def reload_after_payloads(
            reader: Any, query: str, params: Any = None, timeout: Any = None
        ) -> Any:
            nonlocal reloaded
            result = read_query(reader, query, params, timeout)
            if "n.doc" in query and not reloaded:
                reloaded = True
                # The edition query now reads the new graph while the already-read
                # payloads and metadata still describe the old graph.
                load_graph(db, _kb(tmp_path / "kb", updated=True, extra_person=True), graph.name)
            return result

        monkeypatch.setattr(browser.GraphReader, "ro_query", reload_after_payloads)
        monkeypatch.setattr(browser, "build_overview", counted)
        app = create_app(graph, extra_hosts=frozenset({"testserver"}))
        client = TestClient(app)
        result = _get(client)
        assert calls == 2
        assert result["totals"]["entities"] == 21
        assert result["sources"]["entities_without_sources"] == 17
        assert {row["basis"]: row["count"] for row in result["participation"]}["opted_in"] == 1
        assert result["load"]["load_id"] == client.get("/api/meta").json()["load_id"]

        def invalidating(*args: Any) -> dict[str, Any]:
            result = aggregate(*args)
            app.state.catalog.invalidate()
            return result

        app.state.catalog.invalidate()
        monkeypatch.setattr(browser, "build_overview", invalidating)
        response = client.get("/api/overview")
        assert response.status_code == 503
        assert "retry" in response.json()["error"]
    finally:
        delete_graph(db, graph.name)


def test_review_returns_checks_and_identity_from_one_stable_load(tmp_path: Path, monkeypatch: Any):
    import paraverse_graph.browser as browser

    checks = (
        Check(
            "people_snapshot",
            "People",
            "info",
            "Synthetic count.",
            "MATCH (n:Person) RETURN n.id, n.display_name, 'synthetic' ORDER BY n.id LIMIT $limit",
        ),
        Check(
            "accounts_snapshot",
            "Fetched accounts",
            "info",
            "Synthetic count.",
            "MATCH (n:SocialAccount) WHERE n.details_fetched = true RETURN n.id, n.display_name, 'synthetic' ORDER BY n.id LIMIT $limit",
        ),
    )
    monkeypatch.setattr(browser, "CHECKS", checks)
    db = open_db(tmp_path / "review-race.rdb")
    graph = db.select_graph("review_race")
    try:
        load_graph(db, _kb(tmp_path / "kb"), graph.name)
        calls = 0

        def reload_after_check(reader: Any, check: Check) -> dict[str, Any]:
            nonlocal calls
            result = run_check(reader, check)
            calls += 1
            if calls == 1:
                load_graph(db, _kb(tmp_path / "kb", updated=True, extra_person=True), graph.name)
            return result

        monkeypatch.setattr(browser, "run_check", reload_after_check)
        app = create_app(graph, extra_hosts=frozenset({"testserver"}))
        client = TestClient(app)
        response = client.get("/api/review")
        assert response.status_code == 200, response.text
        result = response.json()
        assert calls == 4
        assert {row["name"]: row["count"] for row in result["checks"]} == {
            "people_snapshot": 5,
            "accounts_snapshot": 2,
        }
        assert result["load"] == _get(client)["load"]
        assert client.get("/api/review").json() == result
        detail = client.get("/api/review/people_snapshot").json()
        assert detail["count"] == 5
        assert "person:five" in {row["id"] for row in detail["rows"]}
        assert calls == 4

        def invalidating(reader: Any, check: Check) -> dict[str, Any]:
            result = run_check(reader, check)
            app.state.catalog.invalidate()
            return result

        app.state.catalog.invalidate()
        monkeypatch.setattr(browser, "run_check", invalidating)
        for path in ("/api/review", "/api/review/people_snapshot"):
            response = client.get(path)
            assert response.status_code == 503
            assert "retry" in response.json()["error"]
    finally:
        delete_graph(db, graph.name)


def test_overview_tracks_dataset_selection_and_combined_view(tmp_path: Path):
    alpha = source(tmp_path / "alpha", "alpha")
    beta = source(tmp_path / "beta", "beta")
    db = open_db(tmp_path / "selection.rdb")
    try:
        selection = DatasetSelection(db, {"alpha": alpha, "beta": beta}, "overview_selection")
        selection.select(["alpha"])
        client = TestClient(
            create_app(
                db.select_graph(selection.graph_name),
                selection=selection,
                extra_hosts=frozenset({"testserver"}),
            )
        )
        first = _get(client)
        assert first["load"]["dataset"] == "alpha"
        assert first["totals"]["entities"] == 2
        assert {row["id"] for row in first["editions"]} == {"event:alpha"}
        assert client.get("/api/review").json()["load"] == first["load"]

        response = client.post("/api/datasets/select", json={"datasets": ["beta", "alpha"]})
        assert response.status_code == 200, response.text
        combined = _get(client)
        assert combined["load"]["dataset"] == "alpha + beta"
        assert combined["load"]["load_id"] != first["load"]["load_id"]
        assert combined["totals"]["entities"] == 4
        assert combined["totals"]["relationships"] == 2
        assert {row["id"] for row in combined["editions"]} == {"event:alpha", "event:beta"}
        assert client.get("/api/review").json()["load"] == combined["load"]
        meta = client.get("/api/meta").json()
        assert combined["load"] == {key: meta[key] for key in combined["load"]}

        response = client.post("/api/datasets/select", json={"datasets": ["beta"]})
        assert response.status_code == 200, response.text
        final = _get(client)
        assert final["load"]["dataset"] == "beta"
        assert final["totals"]["entities"] == 2
        assert {row["id"] for row in final["editions"]} == {"event:beta"}
        assert client.get("/api/review").json()["load"] == final["load"]
    finally:
        db.close()
