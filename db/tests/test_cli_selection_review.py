"""Serve preserves explicit graph targets and keeps selected source builds current."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import uvicorn
import yaml
from starlette.testclient import TestClient

from paraverse_graph import cli
from paraverse_graph.browser import create_app
from paraverse_graph.connection import open_db
from paraverse_graph.datasets import KB_ENV, Dataset
from paraverse_graph.kb import load_kb
from paraverse_graph.loader import load_graph
from paraverse_graph.selection import DatasetSelection
from tests.test_selection import source


@pytest.mark.parametrize(
    "target_options",
    [
        ["--graph", "preloaded"],
        ["--url", "redis://example.invalid:6379"],
        ["--graph", "preloaded", "--url", "redis://example.invalid:6379"],
    ],
)
def test_serve_explicit_target_uses_loaded_graph_without_rebuilding_from_local_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_options: list[str]
) -> None:
    local = source(tmp_path / "local", "local")
    initial = source(tmp_path / "initial", "initial")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    db = open_db(tmp_path / "preloaded.rdb")
    target = "preloaded" if "--graph" in target_options else Dataset("local", local).graph
    load_graph(db, load_kb(initial), target)
    original_graphs = db.list_graphs()
    connections = []

    def connect(db_file: Path | None, url: str | None) -> Any:
        connections.append((db_file, url))
        return db

    def serve(app: Any, **_kwargs: Any) -> None:
        with TestClient(app) as client:
            assert client.get("/api/meta").json()["graph"] == target
            assert not client.get("/api/datasets").json()["selection_enabled"]
            assert client.get("/api/rows/event").json()["rows"][0]["id"] == "event:initial"

    monkeypatch.setattr(cli, "open_db", connect)
    monkeypatch.setattr(uvicorn, "run", serve)
    monkeypatch.setattr(
        cli,
        "create_app",
        lambda graph, **kwargs: create_app(graph, extra_hosts=frozenset({"testserver"}), **kwargs),
    )
    try:
        assert cli.main(["serve", "--kb", str(local), *target_options]) == 0
        assert db.list_graphs() == original_graphs
        assert connections == [
            (None, "redis://example.invalid:6379" if "--url" in target_options else None)
        ]
    finally:
        db.close()


@pytest.mark.parametrize("opt_in", ["--select-all", "--include-kb"])
def test_explicit_selector_request_can_compose_into_an_explicit_remote_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, opt_in: str
) -> None:
    local = source(tmp_path / "local", "local")
    extra = source(tmp_path / "extra", "extra")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    db = open_db(tmp_path / "explicit-selection.rdb")
    monkeypatch.setattr(cli, "open_db", lambda *_args: db)
    monkeypatch.setattr(
        cli,
        "create_app",
        lambda graph, **kwargs: create_app(graph, extra_hosts=frozenset({"testserver"}), **kwargs),
    )
    expected = ["local"]

    def serve(app: Any, **_kwargs: Any) -> None:
        with TestClient(app) as client:
            assert client.get("/api/meta").json()["graph"].startswith("preloaded__browser_8766_")
            choices = client.get("/api/datasets").json()
            assert choices["selection_enabled"]
            assert choices["selected"] == expected

    monkeypatch.setattr(uvicorn, "run", serve)
    options = [opt_in] if opt_in == "--select-all" else [opt_in, f"extra={extra}"]
    try:
        assert (
            cli.main(
                [
                    "serve",
                    "--kb",
                    str(local),
                    "--graph",
                    "preloaded",
                    "--url",
                    "redis://example.invalid:6379",
                    *options,
                ]
            )
            == 0
        )
    finally:
        db.close()


@pytest.mark.parametrize("include_second", [False, True])
def test_explicit_include_chooses_included_sources_when_the_default_kb_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, include_second: bool
) -> None:
    custom = source(tmp_path / "custom", "custom")
    second = source(tmp_path / "second", "second")
    source(tmp_path / "vendor/unrelated/kb", "unrelated")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    db = open_db(tmp_path / "included-only.rdb")

    def serve(app: Any, **_kwargs: Any) -> None:
        with TestClient(app) as client:
            choices = client.get("/api/datasets").json()
            assert choices["selection_enabled"]
            assert choices["selected"] == (["custom", "second"] if include_second else ["custom"])
            assert client.get("/api/rows/event").json()["total"] == (2 if include_second else 1)

    monkeypatch.setattr(cli, "open_db", lambda *_args: db)
    monkeypatch.setattr(
        cli,
        "create_app",
        lambda graph, **kwargs: create_app(graph, extra_hosts=frozenset({"testserver"}), **kwargs),
    )
    monkeypatch.setattr(uvicorn, "run", serve)
    argv = ["serve", "--graph", "custom", "--include-kb", f"custom={custom}"]
    if include_second:
        argv += ["--include-kb", f"second={second}"]
    try:
        assert cli.main(argv) == 0
    finally:
        db.close()


@pytest.mark.parametrize("exit_mode", ["normal", "interrupt", "bind-failure", "app-failure"])
def test_generated_browser_graph_is_cleaned_while_source_graphs_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_mode: str
) -> None:
    local = source(tmp_path / "local", "local")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    db = open_db(tmp_path / "cleanup.rdb")
    load_graph(db, load_kb(local), Dataset("local", local).graph)
    load_graph(db, load_kb(local), "preloaded_explicit_graph")
    original_graphs = set(db.list_graphs())
    generated = []

    def make_app(graph: Any, **kwargs: Any) -> Any:
        added = set(db.list_graphs()) - original_graphs
        assert len(added) == 1
        generated.extend(added)
        if exit_mode == "app-failure":
            raise RuntimeError("application could not initialize")
        return create_app(graph, extra_hosts=frozenset({"testserver"}), **kwargs)

    def serve(_app: Any, **_kwargs: Any) -> None:
        if exit_mode == "interrupt":
            raise KeyboardInterrupt
        if exit_mode == "bind-failure":
            raise SystemExit(1)

    monkeypatch.setattr(cli, "open_db", lambda *_args: db)
    monkeypatch.setattr(cli, "create_app", make_app)
    monkeypatch.setattr(uvicorn, "run", serve)
    try:
        if exit_mode == "app-failure":
            with pytest.raises(RuntimeError, match="could not initialize"):
                cli.main(["serve", "--kb", str(local)])
        elif exit_mode == "bind-failure":
            with pytest.raises(SystemExit):
                cli.main(["serve", "--kb", str(local)])
        else:
            assert cli.main(["serve", "--kb", str(local)]) == (
                130 if exit_mode == "interrupt" else 0
            )
        assert len(generated) == 1
        assert set(db.list_graphs()) == original_graphs
    finally:
        db.close()


def test_failed_second_launch_on_the_same_port_preserves_running_browser_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = source(tmp_path / "local", "local")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    db = open_db(tmp_path / "same-port.rdb")
    load_graph(db, load_kb(local), Dataset("local", local).graph)
    original_graphs = set(db.list_graphs())
    running = []
    argv = ["serve", "--kb", str(local)]

    def serve(app: Any, **_kwargs: Any) -> None:
        with TestClient(app) as client:
            graph_name = client.get("/api/meta").json()["graph"]
            if running:
                assert graph_name != running[0]
                raise SystemExit(1)
            running.append(graph_name)
            with pytest.raises(SystemExit):
                cli.main(argv)
            assert set(db.list_graphs()) == original_graphs | set(running)
            assert client.get("/api/rows/event").json()["total"] == 1

    monkeypatch.setattr(cli, "open_db", lambda *_args: db)
    monkeypatch.setattr(
        cli,
        "create_app",
        lambda graph, **kwargs: create_app(graph, extra_hosts=frozenset({"testserver"}), **kwargs),
    )
    monkeypatch.setattr(uvicorn, "run", serve)
    try:
        assert cli.main(argv) == 0
        assert set(db.list_graphs()) == original_graphs
    finally:
        db.close()


def test_selector_refreshes_after_manual_source_reload_without_watch_option(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = source(tmp_path / "local", "local")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    db = open_db(tmp_path / "automatic-refresh.rdb")
    started, finished = threading.Event(), threading.Event()
    original_watch = cli.watch_selection

    def watch(selection: DatasetSelection, stop: threading.Event) -> None:
        class FastStop:
            def wait(self, _seconds: float) -> bool:
                return stop.wait(0.02)

        started.set()
        try:
            fast_stop: Any = FastStop()
            original_watch(selection, fast_stop)
        finally:
            finished.set()

    def serve(app: Any, **_kwargs: Any) -> None:
        assert started.wait(2)
        with TestClient(app) as client:
            name = client.get("/api/rows/event").json()["rows"][0]["name"]
            assert name == "Event local"
            record_path = local / "0.yaml"
            record = yaml.safe_load(record_path.read_text())
            record["event"]["name"] = "Rebuilt source event"
            record_path.write_text(yaml.safe_dump(record))
            nodes_path = local / "_graph/nodes.jsonl"
            rows = [json.loads(line) for line in nodes_path.read_text().splitlines()]
            rows[0]["name"] = "Rebuilt source event"
            nodes_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            stats_path = local / "_graph/stats.json"
            stats = json.loads(stats_path.read_text())
            stats["build"] = "rebuilt"
            stats_path.write_text(json.dumps(stats))
            load_graph(db, load_kb(local), Dataset("local", local).graph)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                name = client.get("/api/rows/event").json()["rows"][0]["name"]
                if name == "Rebuilt source event":
                    break
                time.sleep(0.02)
            assert name == "Rebuilt source event"

    monkeypatch.setattr(cli, "open_db", lambda *_args: db)
    monkeypatch.setattr(cli, "watch_selection", watch)
    monkeypatch.setattr(uvicorn, "run", serve)
    monkeypatch.setattr(
        cli,
        "create_app",
        lambda graph, **kwargs: create_app(graph, extra_hosts=frozenset({"testserver"}), **kwargs),
    )
    try:
        assert cli.main(["serve", "--kb", str(local)]) == 0
        assert finished.wait(2)
    finally:
        db.close()
