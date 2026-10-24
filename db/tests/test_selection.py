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
