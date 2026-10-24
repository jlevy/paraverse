"""Run the browser overview's async lifecycle checks without a browser dependency."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_overview_frontend_lifecycle():
    script = Path(__file__).with_name("overview_frontend.mjs")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Overview frontend lifecycle checks passed." in result.stdout
