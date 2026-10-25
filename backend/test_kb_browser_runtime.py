from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import patch

import kb_browser_runtime


class BrowserRuntimeTests(unittest.TestCase):
    def test_expected_identity_uses_same_all_dataset_composition_as_server(self):
        root = Path("/synthetic/repository")
        datasets = [
            SimpleNamespace(name=name, require_kb=lambda name=name: root / name / "kb")
            for name in ["two", "one"]
        ]
        with (
            patch("paraverse_graph.datasets.list_datasets", return_value=datasets) as discover,
            patch(
                "paraverse_graph.composition.compose_kbs",
                return_value=SimpleNamespace(digest="content-digest"),
            ) as compose,
        ):
            self.assertEqual(
                kb_browser_runtime.expected_selection(root),
                dict(selected=["one", "two"], kb_digest="content-digest"),
            )
            discover.assert_called_once_with(root / "db")
            compose.assert_called_once_with({"two": root / "two/kb", "one": root / "one/kb"})

    def test_early_close_and_reopen_reap_owned_redis_without_stopping_other_server(self):
        import psutil
        from redislite.falkordb_client import FalkorDB

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = FalkorDB(str(root / "unrelated.rdb"))
            package = root / "paraverse_graph"
            package.mkdir()
            (package / "__init__.py").write_text("")
            (package / "cli.py").write_text(
                dedent("""
                import json, os, time
                from pathlib import Path
                from redislite.falkordb_client import FalkorDB
                def open_db(db_file=None, url=None):
                    return FalkorDB(os.environ['OWNED_DB'])
                def main(argv):
                    db = open_db()
                    Path(os.environ['READY']).write_text(json.dumps({'pid': db.client.pid}))
                    time.sleep(90)
                    return 0
            """)
            )
            try:
                for iteration in range(2):
                    ready = root / f"ready-{iteration}.json"
                    environment = dict(
                        os.environ,
                        PYTHONPATH=str(root),
                        OWNED_DB=str(root / "owned.rdb"),
                        READY=str(ready),
                    )
                    process = subprocess.Popen(
                        [sys.executable, str(Path(kb_browser_runtime.__file__)), "serve"],
                        env=environment,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    redis_pid = None
                    try:
                        deadline = time.monotonic() + 15
                        while (
                            not ready.exists()
                            and process.poll() is None
                            and time.monotonic() < deadline
                        ):
                            time.sleep(0.02)
                        self.assertTrue(
                            ready.exists(),
                            "The owned Redis must be running before early close; no HTTP server has started",
                        )
                        redis_pid = json.loads(ready.read_text())["pid"]
                        self.assertTrue(psutil.pid_exists(redis_pid))
                        process.terminate()
                        process.wait(timeout=35)
                        self.assertEqual(process.returncode, 143)
                        self.assertFalse(
                            psutil.pid_exists(redis_pid)
                            and psutil.Process(redis_pid).status() != psutil.STATUS_ZOMBIE,
                            "Early close must reap the detached owned Redis",
                        )
                        self.assertTrue(
                            unrelated.client.ping(), "An unrelated Redis instance must stay alive"
                        )
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                        if redis_pid and psutil.pid_exists(redis_pid):
                            child = psutil.Process(redis_pid)
                            if child.status() != psutil.STATUS_ZOMBIE:
                                child.kill()
            finally:
                unrelated.close()

    def test_ready_close_reaps_owned_redis_and_preserves_unrelated_server(self):
        import http.client
        import socket

        import psutil
        import redis
        from redislite.falkordb_client import FalkorDB

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Portable two-dataset input exercises the actual CLI, Uvicorn and
            # Redis pubsub lifecycle without requiring checked-out submodules.
            for name in ("one", "two"):
                kb = root / name
                (kb / "_graph").mkdir(parents=True)
                (kb / "_schemas").mkdir()
                (kb / "event.yaml").write_text(
                    f"softschema:\n  contract: example:event/v1\n  envelope: event\nevent:\n  id: event:{name}\n  name: {name}\n"
                )
                (kb / "_graph/nodes.jsonl").write_text(
                    json.dumps(
                        {"id": f"event:{name}", "kind": "event", "name": name, "path": "event.yaml"}
                    )
                    + "\n"
                )
                (kb / "_graph/edges.jsonl").write_text("")
                (kb / "_graph/stats.json").write_text(
                    json.dumps({"nodes": {"event": 1}, "edges": {}})
                )
                (kb / "_schemas/event.schema.yaml").write_text(
                    "type: object\nproperties:\n  id: {type: string}\n  name: {type: string}\n"
                )
            with socket.socket() as reserved:
                reserved.bind(("127.0.0.1", 0))
                port = reserved.getsockname()[1]
            marker = root / "ready.json"
            child_source = dedent("""
                import json
                import sys
                from pathlib import Path
                import paraverse_graph.cli as cli
                original_open = cli.open_db
                def traced(*args, **kwargs):
                    db = original_open(*args, **kwargs)
                    Path(sys.argv[1]).write_text(json.dumps({
                        "pid": db.client.pid, "socket": db.client.socket_file,
                    }))
                    return db
                cli.open_db = traced
                original_main = cli.main
                cli.main = lambda _argv: original_main(sys.argv[2:])
                from kb_browser_runtime import serve
                raise SystemExit(serve())
            """)
            repo = Path(__file__).resolve().parents[1]
            environment = dict(
                os.environ,
                PYTHONPATH=os.pathsep.join((str(repo / "backend"), str(repo / "db/src"))),
            )
            environment.pop("PARAVERSE_KB", None)
            unrelated = FalkorDB(str(root / "unrelated.rdb"))
            unrelated_pid = unrelated.client.pid
            process = None
            observer = None
            redis_process = None
            try:
                with (root / "server.log").open("w") as log:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            child_source,
                            str(marker),
                            "serve",
                            "--select-all",
                            "--watch",
                            "--kb",
                            str(root / "one"),
                            "--include-kb",
                            f"two={root / 'two'}",
                            "--db",
                            str(root / "owned.rdb"),
                            "--port",
                            str(port),
                        ],
                        env=environment,
                        cwd=root,
                        stdout=log,
                        stderr=log,
                    )
                    deadline = time.monotonic() + 30
                    ready = False
                    while process.poll() is None and time.monotonic() < deadline:
                        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                        try:
                            connection.request("GET", "/api/meta")
                            response = connection.getresponse()
                            payload = response.read()
                            ready = (
                                response.status == 200 and json.loads(payload)["node_total"] == 2
                            )
                            if ready:
                                break
                        except (OSError, http.client.HTTPException):
                            pass
                        finally:
                            connection.close()
                        time.sleep(0.02)
                    self.assertTrue(ready, (root / "server.log").read_text()[-2000:])
                    info = json.loads(marker.read_text())
                    redis_process = psutil.Process(info["pid"])
                    observer = redis.Redis(unix_socket_path=info["socket"], socket_timeout=1)
                    self.assertEqual(observer.info("server")["process_id"], info["pid"])
                    # The observer must not cause redislite's shared-client guard.
                    observer.close()
                    observer.connection_pool.disconnect()
                    process.terminate()
                    process.wait(timeout=35)
                    self.assertEqual(process.returncode, 143)
                    deadline = time.monotonic() + 2
                    while redis_process.is_running() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertFalse(
                        redis_process.is_running(), "Ready close must reap owned Redis"
                    )
                    self.assertEqual(unrelated.client.info("server")["process_id"], unrelated_pid)
                    self.assertTrue(unrelated.client.ping())
            finally:
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                # Clean up only the exact private daemon from this test on RED.
                if observer is not None and redis_process is not None:
                    try:
                        if (
                            redis_process.is_running()
                            and observer.info("server")["process_id"] == redis_process.pid
                        ):
                            observer.shutdown(nosave=True)
                    except redis.RedisError:
                        pass
                    observer.close()
                    observer.connection_pool.disconnect()
                unrelated.client.connection_pool.disconnect()
                unrelated.close()
