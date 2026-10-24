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
import yaml
from redis.exceptions import RedisError
from starlette.testclient import TestClient

from paraverse_graph import cli
from paraverse_graph import selection as selection_module
from paraverse_graph.browser import create_app
from paraverse_graph.composition import compose_kbs
from paraverse_graph.connection import open_db
from paraverse_graph.kb import KbError
from paraverse_graph.loader import LoadError, load_graph
from paraverse_graph.selection import DatasetSelection, SelectionError
from tests.test_frontend_review import HARNESS, WEB
from tests.test_selection import source


@pytest.mark.parametrize("invalid_row", [[], None, 42])
def test_unselected_non_mapping_export_does_not_prevent_serving_valid_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid_row: Any
) -> None:
    alpha = source(tmp_path / "alpha", "alpha")
    broken = source(tmp_path / "broken", "broken")
    (broken / "_graph/nodes.jsonl").write_text(json.dumps(invalid_row) + "\n")
    monkeypatch.setattr(selection_module, "load_graph", lambda *_args, **_kwargs: None)
    selection = DatasetSelection(None, {"alpha": alpha, "broken": broken}, "browser")
    selection.select(["alpha"])
    description = selection.describe()
    assert description["selected"] == ["alpha"]
    assert {row["id"]: row["name"] for row in description["datasets"]} == {
        "alpha": "Event alpha",
        "broken": "broken",
    }


def publish_build(root: Path, build: str) -> None:
    stats_path = root / "_graph/stats.json"
    stats = json.loads(stats_path.read_text())
    stats["build"] = build
    stats_path.write_text(json.dumps(stats))


def rename_event_build(root: Path, title: str) -> None:
    path = root / "0.yaml"
    record = yaml.safe_load(path.read_text())
    record["event"]["name"] = title
    path.write_text(yaml.safe_dump(record))
    path = root / "_graph/nodes.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["name"] = title
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    publish_build(root, title)


def test_labels_commit_the_loaded_source_snapshot_and_survive_failed_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    db = open_db(tmp_path / "labels.rdb")

    def load_then_publish_newer_source(*args: Any, **kwargs: Any) -> Any:
        result = load_graph(*args, **kwargs)
        rename_event_build(root, "Newer unloaded title")
        return result

    try:
        selection = DatasetSelection(db, {"alpha": root}, "labels")
        selection.select(["alpha"])
        rename_event_build(root, "Loaded snapshot title")
        monkeypatch.setattr(selection_module, "load_graph", load_then_publish_newer_source)
        assert selection.refresh_if_changed()
        assert selection.describe()["datasets"][0]["name"] == "Loaded snapshot title"
        assert db.select_graph("labels").ro_query(
            "MATCH (e:Event) RETURN e.display_name"
        ).result_set == [["Loaded snapshot title"]]

        def fail(*_args: Any, **_kwargs: Any) -> None:
            raise LoadError("staging graph did not pass its checks")

        monkeypatch.setattr(selection_module, "load_graph", fail)
        with pytest.raises(SelectionError):
            selection.refresh_if_changed()
        assert selection.describe()["datasets"][0]["name"] == "Loaded snapshot title"
        monkeypatch.setattr(selection_module, "load_graph", load_graph)
        selection.select(["alpha"])
        assert selection.describe()["datasets"][0]["name"] == "Newer unloaded title"
    finally:
        db.close()


@pytest.mark.parametrize("notification_failure", [False, True])
def test_watcher_notifies_after_labels_commit_and_notification_failure_keeps_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    notification_failure: bool,
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    db = open_db(tmp_path / "watch-notify.rdb")
    notices = []

    class OneTick:
        def __init__(self) -> None:
            self.calls: int = 0

        def wait(self, _seconds: float) -> bool:
            self.calls += 1
            return self.calls > 1

    try:
        selection = DatasetSelection(db, {"alpha": root}, "watch_notify")
        selection.select(["alpha"])
        rename_event_build(root, "New loaded title")

        def publish(_channel: str, message: str) -> int:
            notices.append(
                (json.loads(message)["type"], selection.describe()["datasets"][0]["name"])
            )
            if len(notices) == 2 and notification_failure:
                raise RedisError("notification connection unavailable")
            return 0

        monkeypatch.setattr(db.connection, "publish", publish)
        stop: Any = OneTick()
        cli.watch_selection(selection, stop)
        assert notices == [
            ("graph.loaded", "Event alpha"),
            ("graph.loaded", "New loaded title"),
        ]
        assert not selection.refresh_if_changed()
        if notification_failure:
            assert "notification connection unavailable" in capsys.readouterr().err
    finally:
        db.close()


def test_deterministic_load_failure_waits_for_a_new_build_even_after_retry_delay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    now = [0.0]
    attempts = []
    invalid = [False]

    def load(*_args: Any, **_kwargs: Any) -> None:
        attempts.append(True)
        if invalid[0]:
            raise LoadError("staging graph counts do not match source stats")

    monkeypatch.setattr(selection_module, "load_graph", load)
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    selection = DatasetSelection(None, {"alpha": root}, "browser")
    selection.select(["alpha"])
    publish_build(root, "bad-stats")
    invalid[0] = True
    with pytest.raises(SelectionError):
        selection.refresh_if_changed()
    invalid[0] = False
    now[0] = 100_000
    assert not selection.refresh_if_changed()
    assert len(attempts) == 2
    publish_build(root, "corrected-stats")
    assert selection.refresh_if_changed()
    assert len(attempts) == 3


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


@pytest.mark.parametrize("failure_type", [RedisError, OSError])
@pytest.mark.parametrize("wrapped", [False, True])
def test_transient_refresh_failures_back_off_and_recover_without_source_edits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
    wrapped: bool,
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    now = [0.0]
    attempts = []
    unavailable = [False]

    def load(*_args: Any, **_kwargs: Any) -> None:
        attempts.append(now[0])
        if unavailable[0]:
            error = failure_type("temporarily unavailable")
            if wrapped:
                raise LoadError("loader could not reach the database or source") from error
            raise error

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


def test_close_waits_for_an_active_build_and_prevents_graph_recreation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = source(tmp_path / "alpha", "alpha")
    db = open_db(tmp_path / "close.rdb")
    entered, release, closing_started = threading.Event(), threading.Event(), threading.Event()
    try:
        selection = DatasetSelection(db, {"alpha": root}, "closing_browser")
        selection.select(["alpha"])

        def delayed_load(*args: Any, **kwargs: Any) -> Any:
            entered.set()
            assert release.wait(5)
            return load_graph(*args, **kwargs)

        def close() -> None:
            closing_started.set()
            selection.close()

        monkeypatch.setattr(selection_module, "load_graph", delayed_load)
        with ThreadPoolExecutor(max_workers=2) as pool:
            building = pool.submit(selection.select, ["alpha"])
            try:
                assert entered.wait(5)
                closing = pool.submit(close)
                assert closing_started.wait(5)
                assert not closing.done()
            finally:
                release.set()
            building.result(timeout=5)
            closing.result(timeout=5)
        assert "closing_browser" not in db.list_graphs()
        with pytest.raises(SelectionError, match="shutting down"):
            selection.select(["alpha"])
        assert not selection.refresh_if_changed()
        assert "closing_browser" not in db.list_graphs()
    finally:
        release.set()
        db.close()


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
