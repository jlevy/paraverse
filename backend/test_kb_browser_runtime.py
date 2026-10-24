from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import kb_browser_runtime


class BrowserRuntimeTests(unittest.TestCase):
    def test_expected_identity_uses_same_all_dataset_composition_as_server(self):
        root = Path('/synthetic/repository')
        datasets = [SimpleNamespace(name=name, require_kb=lambda name=name: root / name / 'kb') for name in ['two', 'one']]
        with patch('paraverse_graph.datasets.list_datasets', return_value=datasets) as discover, patch('paraverse_graph.composition.compose_kbs', return_value=SimpleNamespace(digest='content-digest')) as compose:
            self.assertEqual(kb_browser_runtime.expected_selection(root), dict(selected=['one', 'two'], kb_digest='content-digest'))
            discover.assert_called_once_with(root / 'db')
            compose.assert_called_once_with({'two': root / 'two/kb', 'one': root / 'one/kb'})

    def test_early_close_and_reopen_reap_owned_redis_without_stopping_other_server(self):
        import psutil
        from redislite.falkordb_client import FalkorDB

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = FalkorDB(str(root / 'unrelated.rdb'))
            package = root / 'paraverse_graph'; package.mkdir()
            (package / '__init__.py').write_text('')
            (package / 'cli.py').write_text('''import json,os,time
from pathlib import Path
from redislite.falkordb_client import FalkorDB
def main(argv):
 db=FalkorDB(os.environ['OWNED_DB'])
 Path(os.environ['READY']).write_text(json.dumps({'pid':db.client.pid}))
 time.sleep(90)
 return 0
''')
            try:
                for iteration in range(2):
                    ready = root / f'ready-{iteration}.json'
                    environment = dict(os.environ, PYTHONPATH=str(root), OWNED_DB=str(root / 'owned.rdb'), READY=str(ready))
                    process = subprocess.Popen([sys.executable, str(Path(kb_browser_runtime.__file__)), 'serve'], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    redis_pid = None
                    try:
                        deadline = time.monotonic() + 15
                        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                            time.sleep(.02)
                        self.assertTrue(ready.exists(), 'The owned Redis must be running before early close; no HTTP server has started')
                        redis_pid = json.loads(ready.read_text())['pid']
                        self.assertTrue(psutil.pid_exists(redis_pid))
                        process.terminate()
                        process.wait(timeout=35)
                        self.assertEqual(process.returncode, 143)
                        self.assertFalse(psutil.pid_exists(redis_pid) and psutil.Process(redis_pid).status() != psutil.STATUS_ZOMBIE, 'Early close must reap the detached owned Redis')
                        self.assertTrue(unrelated.client.ping(), 'An unrelated Redis instance must stay alive')
                    finally:
                        if process.poll() is None:
                            process.kill(); process.wait()
                        if redis_pid and psutil.pid_exists(redis_pid):
                            child = psutil.Process(redis_pid)
                            if child.status() != psutil.STATUS_ZOMBIE: child.kill()
            finally:
                unrelated.close()
