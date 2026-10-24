"""Refresh failures and slow builds keep the active browser selection usable."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from redis.exceptions import RedisError
from starlette.testclient import TestClient

from paraverse_graph import selection as selection_module
from paraverse_graph.browser import create_app
from paraverse_graph.composition import compose_kbs
from paraverse_graph.connection import open_db
from paraverse_graph.kb import KbError
from paraverse_graph.loader import LoadError, load_graph
from paraverse_graph.selection import DatasetSelection, SelectionError
from tests.test_frontend_review import HARNESS, WEB
from tests.test_selection import source


def publish_build(root: Path, build: str) -> None:
    stats_path = root / "_graph/stats.json"
    stats = json.loads(stats_path.read_text())
    stats["build"] = build
    stats_path.write_text(json.dumps(stats))


def test_unchanged_invalid_build_is_attempted_once_until_source_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    attempts = []

    def compose(*args: Any, **kwargs: Any) -> Any:
        attempts.append(True)
        return compose_kbs(*args, **kwargs)

    monkeypatch.setattr(selection_module, "compose_kbs", compose)
    monkeypatch.setattr(selection_module, "load_graph", lambda *_args, **_kwargs: None)
    selection = DatasetSelection(None, {"alpha": root}, "browser")
    selection.select(["alpha"])
    nodes_path = root / "_graph/nodes.jsonl"
    original_nodes = nodes_path.read_text()
    nodes_path.write_text("invalid JSON\n")
    publish_build(root, "invalid")

    with pytest.raises(SelectionError):
        selection.refresh_if_changed()
    assert len(attempts) == 2
    for _ in range(4):
        assert not selection.refresh_if_changed()
    assert len(attempts) == 2
    assert selection.describe()["selected"] == ["alpha"]

    nodes_path.write_text(original_nodes)
    publish_build(root, "repaired")
    assert selection.refresh_if_changed()
    assert len(attempts) == 3
    assert not selection.refresh_if_changed()


@pytest.mark.parametrize("failure_type", [RedisError, OSError, LoadError])
def test_transient_refresh_failures_back_off_and_recover_without_source_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    now = [0.0]
    attempts = []
    unavailable = [False]

    def load(*_args: Any, **_kwargs: Any) -> None:
        attempts.append(now[0])
        if unavailable[0]:
            raise failure_type("temporarily unavailable")

    monkeypatch.setattr(selection_module, "load_graph", load)
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    selection = DatasetSelection(None, {"alpha": root}, "browser")
    selection.select(["alpha"])
    publish_build(root, "new-build")
    unavailable[0] = True

    for attempt_time, next_time in ((0, 30), (30, 90), (90, 210), (210, 450), (450, 750)):
        now[0] = attempt_time
        with pytest.raises(SelectionError):
            selection.refresh_if_changed()
        attempts_before = len(attempts)
        now[0] = next_time - 1
        assert not selection.refresh_if_changed()
        assert len(attempts) == attempts_before
    unavailable[0] = False
    now[0] = 750
    assert selection.refresh_if_changed()
    assert attempts == [0, 0, 30, 90, 210, 450, 750]
    assert not selection.refresh_if_changed()


def test_wrapped_source_io_failure_is_retried_without_source_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    now = [0.0]
    unavailable = [False]

    def compose(*args: Any, **kwargs: Any) -> Any:
        if unavailable[0]:
            io_error = OSError("source filesystem is temporarily unavailable")
            inner = KbError("KB changed while reading; cannot inspect source")
            inner.__cause__ = io_error
            raise KbError("alpha: KB changed while reading") from inner
        return compose_kbs(*args, **kwargs)

    monkeypatch.setattr(selection_module, "compose_kbs", compose)
    monkeypatch.setattr(selection_module, "load_graph", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    selection = DatasetSelection(None, {"alpha": root}, "browser")
    selection.select(["alpha"])
    publish_build(root, "new-build")
    unavailable[0] = True
    with pytest.raises(SelectionError):
        selection.refresh_if_changed()
    unavailable[0] = False
    assert not selection.refresh_if_changed()
    now[0] = 30
    assert selection.refresh_if_changed()


def test_describe_and_active_roots_do_not_wait_for_a_slow_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alpha, beta = source(tmp_path / "alpha", "alpha"), source(tmp_path / "beta", "beta")
    entered, release = threading.Event(), threading.Event()
    slow = [False]

    def load(*_args: Any, **_kwargs: Any) -> None:
        if slow[0]:
            entered.set()
            assert release.wait(5)

    monkeypatch.setattr(selection_module, "load_graph", load)
    selection = DatasetSelection(None, {"alpha": alpha, "beta": beta}, "browser")
    selection.select(["alpha"])
    slow[0] = True

    with ThreadPoolExecutor(max_workers=2) as pool:
        building = pool.submit(selection.select, ["alpha", "beta"])
        try:
            assert entered.wait(5)
            reading = pool.submit(lambda: (selection.describe(), selection.active_roots()))
            description, roots = reading.result(timeout=1)
            assert description["selected"] == ["alpha"]
            assert roots == (alpha,)
        finally:
            release.set()
        assert building.result(timeout=5)["selected"] == ["alpha", "beta"]
    assert selection.active_roots() == (alpha, beta)


def test_selection_notifies_after_commit_even_when_the_new_load_was_already_seen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed to verify the reload notification listener")
    alpha, beta = source(tmp_path / "alpha", "alpha"), source(tmp_path / "beta", "beta")
    db = open_db(tmp_path / "notification.rdb")
    entered, release = threading.Event(), threading.Event()
    notices = []
    try:
        selection = DatasetSelection(db, {"alpha": alpha, "beta": beta}, "notification")
        selection.select(["alpha"])
        app = create_app(
            db.select_graph("notification"),
            extra_hosts=frozenset({"testserver"}),
            selection=selection,
        )

        def publish(event: dict[str, Any]) -> None:
            notices.append((event, selection.describe()["selected"]))

        def pause_after_graph_publish(*args: Any, **kwargs: Any) -> Any:
            report = load_graph(*args, **kwargs)
            entered.set()
            assert release.wait(10)
            return report

        monkeypatch.setattr(app.state.bus, "publish", publish)
        monkeypatch.setattr(selection_module, "load_graph", pause_after_graph_publish)
        with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
            choosing = pool.submit(
                client.post, "/api/datasets/select", json={"datasets": ["alpha", "beta"]}
            )
            try:
                assert entered.wait(10)
                early_meta = client.get("/api/meta").json()
                assert early_meta["dataset"] == "alpha + beta"
                assert client.get("/api/datasets").json()["selected"] == ["alpha"]
            finally:
                release.set()
            assert choosing.result(timeout=10).status_code == 200
            assert client.get("/api/meta").json()["load_id"] == early_meta["load_id"]
        assert notices == [({"type": "graph.loaded"}, ["alpha", "beta"])]
    finally:
        release.set()
        db.close()

    # A reader that consumed the early graph stamp must still refresh its choices.
    script = r"""
const listeners = new Map();
context.EventSource = class {
  constructor() { this.readyState = 1; }
  addEventListener(type, listener) { listeners.set(type, listener); }
  close() {}
};
let selectorReads = 0;
context.refreshDatasetSelector = () => { selectorReads++; };
run('connectEvents()');
const versionBefore = {...state.meta};
await listeners.get(notice.type)({data:JSON.stringify(notice)});
assert.equal(calls.meta, 1);
assert.equal(selectorReads, 1);
assert.equal(calls.render.length, 1);
assert.deepEqual(state.meta, versionBefore, 'the forced refresh needs no new load stamp');
"""
    result = subprocess.run(
        [
            node,
            "--input-type=module",
            "--eval",
            HARNESS + "\nconst notice = " + json.dumps(notices[0][0]) + ";\n" + script,
            str(WEB),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
