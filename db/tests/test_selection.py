"""Dataset selection changes only the browser view, preserving the last valid load."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from starlette.testclient import TestClient

from paraverse_graph import selection as selection_module
from paraverse_graph.browser import create_app
from paraverse_graph.connection import open_db
from paraverse_graph.loader import load_graph
from paraverse_graph.selection import DatasetSelection
from tests.test_composition import write_kb


def source(root: Path, name: str) -> Path:
    event = f"event:{name}"
    person = f"person:{name}"
    result = write_kb(
        root,
        [
            ("event", {"id": event, "name": f"Event {name}"}),
            (
                "person",
                {
                    "id": person,
                    "name": f"Person {name}",
                    "participations": [
                        {"event": event, "role": "judge", "status": "confirmed"},
                    ],
                },
            ),
        ],
        [
            {
                "source": person,
                "relation": "participates_in",
                "target": event,
                "role": "judge",
                "status": "confirmed",
            }
        ],
        role="judge",
    )
    (result / "_schemas/event.schema.yaml").write_text(
        yaml.safe_dump(
            {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
            }
        )
    )
    return result


def test_selection_api_combines_sources_and_keeps_last_valid_view(tmp_path: Path):
    first, second = source(tmp_path / "alpha", "alpha"), source(tmp_path / "beta", "beta")
    db = open_db(tmp_path / "selection.rdb")
    try:
        selection = DatasetSelection(db, {"alpha": first, "beta": second}, "browser_selection")
        selection.select(["alpha"])
        app = create_app(
            db.select_graph("browser_selection"),
            extra_hosts=frozenset({"testserver"}),
            selection=selection,
        )
        with TestClient(app) as client:
            choices = client.get("/api/datasets").json()
            assert choices["selected"] == ["alpha"]
            assert {item["name"] for item in choices["datasets"]} == {"Event alpha", "Event beta"}
            assert client.get("/api/rows/event").json()["total"] == 1
            response = client.post("/api/datasets/select", json={"datasets": ["beta", "alpha"]})
            assert response.status_code == 200, response.text
            assert response.json()["selected"] == ["alpha", "beta"]
            assert client.get("/api/rows/event").json()["total"] == 2
            assert client.get("/api/rows/person").json()["total"] == 2
            for invalid in ([], ["unregistered"], ["../alpha"]):
                assert (
                    client.post("/api/datasets/select", json={"datasets": invalid}).status_code
                    == 400
                )
            assert (
                client.post(
                    "/api/datasets/select",
                    json={"datasets": ["alpha"]},
                    headers={"Origin": "https://example.org"},
                ).status_code
                == 400
            )
            (second / "_graph/nodes.jsonl").write_text("invalid source JSON\n")
            assert (
                client.post("/api/datasets/select", json={"datasets": ["beta"]}).status_code == 400
            )
            assert client.get("/api/datasets").json()["selected"] == ["alpha", "beta"]
            assert client.get("/api/rows/event").json()["total"] == 2
    finally:
        db.close()


def test_watch_does_not_acknowledge_a_build_that_arrives_after_loading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = source(tmp_path / "alpha", "alpha")
    calls = []

    def load(*_args: Any, **_kwargs: Any) -> None:
        calls.append(True)
        if len(calls) == 1:
            path = root / "_graph/stats.json"
            stats = json.loads(path.read_text())
            stats["build"] = "arrived after graph replacement"
            path.write_text(json.dumps(stats))

    monkeypatch.setattr(selection_module, "load_graph", load)
    selection = DatasetSelection(None, {"alpha": root}, "watch_selection")
    selection.select(["alpha"])
    assert selection.refresh_if_changed()
    assert len(calls) == 2
    assert not selection.refresh_if_changed()


def test_restart_reuses_unchanged_view_without_parsing_or_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = source(tmp_path / "alpha", "alpha")
    db = open_db(tmp_path / "reuse.rdb")
    try:
        DatasetSelection(db, {"alpha": root}, "cached_view").select(["alpha"])

        def unexpected(*_args: Any, **_kwargs: Any) -> None:
            pytest.fail("an unchanged persisted view must not be rebuilt")

        monkeypatch.setattr(selection_module, "compose_kbs", unexpected)
        monkeypatch.setattr(selection_module, "load_graph", unexpected)
        restarted = DatasetSelection(db, {"alpha": root}, "cached_view")
        restarted.select(["alpha"])
        assert restarted.describe()["selected"] == ["alpha"]
        assert not restarted.refresh_if_changed()
        assert db.select_graph("cached_view").ro_query(
            "MATCH (p:Person) RETURN p.name"
        ).result_set == [["Person alpha"]]
    finally:
        db.close()


@pytest.mark.parametrize("changed", ["record", "schema", "code", "damaged_graph"])
def test_cached_view_is_rebuilt_when_inputs_or_graph_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str
):
    root = source(tmp_path / "alpha", "alpha")
    db = open_db(tmp_path / "invalidate.rdb")
    try:
        DatasetSelection(db, {"alpha": root}, "cached_view").select(["alpha"])
        graph = db.select_graph("cached_view")
        original_load = graph.ro_query("MATCH (m:GraphMeta) RETURN m.load_id").result_set
        stats = (root / "_graph/stats.json").read_bytes()
        if changed == "record":
            path = next(path for path in root.rglob("*.yaml") if "Person alpha" in path.read_text())
            path.write_text(path.read_text().replace("Person alpha", "Updated person"))
        elif changed == "schema":
            path = root / "_schemas/event.schema.yaml"
            schema = yaml.safe_load(path.read_text())
            schema["description"] = "Updated schema description"
            path.write_text(yaml.safe_dump(schema))
        elif changed == "code":
            monkeypatch.setattr(selection_module, "_CACHE_CODE_DIGEST", "new-loader-version")
        else:
            graph.query("MATCH (p:Person) DETACH DELETE p")

        DatasetSelection(db, {"alpha": root}, "cached_view").select(["alpha"])
        assert graph.ro_query("MATCH (m:GraphMeta) RETURN m.load_id").result_set != original_load
        assert graph.ro_query("MATCH (p:Person) RETURN p.name").result_set == [
            ["Updated person" if changed == "record" else "Person alpha"]
        ]
        # Record/schema edits invalidate reuse even without a producer stats rewrite.
        assert (root / "_graph/stats.json").read_bytes() == stats
    finally:
        db.close()


def test_source_change_during_cache_probe_is_reloaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = source(tmp_path / "alpha", "alpha")
    db = open_db(tmp_path / "raced.rdb")
    try:
        DatasetSelection(db, {"alpha": root}, "cached_view").select(["alpha"])
        restarted = DatasetSelection(db, {"alpha": root}, "cached_view")
        probe = restarted._cached_graph_matches  # pyright: ignore[reportPrivateUsage]

        def change_after_probe(key: str) -> bool:
            matched = probe(key)
            path = next(path for path in root.rglob("*.yaml") if "Person alpha" in path.read_text())
            path.write_text(path.read_text().replace("Person alpha", "Newer person"))
            return matched

        monkeypatch.setattr(restarted, "_cached_graph_matches", change_after_probe)
        restarted.select(["alpha"])
        assert db.select_graph("cached_view").ro_query(
            "MATCH (p:Person) RETURN p.name"
        ).result_set == [["Newer person"]]
    finally:
        db.close()


def test_competing_load_cannot_stamp_another_datasets_graph_as_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    first = source(tmp_path / "alpha", "alpha")
    second = source(tmp_path / "beta", "beta")
    db = open_db(tmp_path / "competing.rdb")
    original_load = load_graph
    loads = []

    def competing_load(*args: Any, **kwargs: Any) -> Any:
        report = original_load(*args, **kwargs)
        loads.append(report.dataset)
        if len(loads) == 1:
            DatasetSelection(db, {"beta": second}, "shared_view").select(["beta"])
        return report

    monkeypatch.setattr(selection_module, "load_graph", competing_load)
    try:
        DatasetSelection(db, {"alpha": first}, "shared_view").select(["alpha"])
        assert db.select_graph("shared_view").ro_query(
            "MATCH (p:Person) RETURN p.name"
        ).result_set == [["Person beta"]]
        DatasetSelection(db, {"alpha": first}, "shared_view").select(["alpha"])
        assert len(loads) == 3
        assert db.select_graph("shared_view").ro_query(
            "MATCH (p:Person) RETURN p.name"
        ).result_set == [["Person alpha"]]
    finally:
        db.close()
