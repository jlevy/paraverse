from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from paraverse_curation.cli import main
from paraverse_curation.people import COLUMNS


def write_list(
    root: Path, rows: list[dict[str, str]] | None = None, *, dataset: str = "universe2026-md"
) -> Path:
    path = root / "curation" / dataset / "additional-people.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows or [])
    path.write_text(out.getvalue())
    return path


def test_check_reports_invalid_data_without_echoing_cell_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_list(tmp_path, [{"name": "Example Person"}])
    assert main(["--root", str(path.parents[1]), "check"]) == 1
    captured = capsys.readouterr()
    assert "source_url: is required" in captured.err
    assert "Example Person" not in captured.err


def test_build_hands_empty_lists_to_the_dataset_with_its_own_uv_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UV_EXCLUDE_NEWER", "14 days")
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path / "cache"))
    path = write_list(tmp_path)
    pipeline = tmp_path / "vendor/universe2026-md/pipeline"
    pipeline.mkdir(parents=True)
    (pipeline / "pyproject.toml").write_text("[project]\nname = 'example'\n")
    (pipeline / "uv.toml").write_text("exclude-newer = '14 days'\n")
    with patch("paraverse_curation.cli.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 7)
        assert main(["--root", str(path.parents[1]), "build", "--dataset", "universe2026-md"]) == 7
        call = run.call_args
        assert call is not None
        assert call.args[0] == ["uv", "run", "--locked", "universe-kb", "build"]
        assert call.kwargs["cwd"] == pipeline
        assert call.kwargs["env"]["UV_CONFIG_FILE"] == str(pipeline / "uv.toml")
        assert "UV_EXCLUDE_NEWER" not in call.kwargs["env"]
        assert call.kwargs["env"]["UV_CACHE_DIR"] == str(tmp_path / "cache")


def test_build_refuses_invalid_dataset_or_unimplemented_populated_intake(tmp_path: Path) -> None:
    path = write_list(
        tmp_path,
        [
            {
                "name": "Example Person",
                "reason": "Maintains the example project",
                "relation": "maintainer",
                "source_url": "https://example.org/team",
                "github": "example-person",
                "added_by": "example-editor",
                "added_on": "2026-10-24",
            }
        ],
    )
    with patch("paraverse_curation.cli.subprocess.run") as run:
        assert main(["--root", str(path.parents[1]), "build", "--dataset", "../other"]) == 1
        assert main(["--root", str(path.parents[1]), "build", "--dataset", "universe2026-md"]) == 1
        run.assert_not_called()


@pytest.mark.parametrize(
    "header",
    [
        "example@example.org",
        "unexpected-private-cell",
        "202-555-0100",
    ],
)
def test_invalid_header_diagnostics_do_not_echo_untrusted_cells(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    header: str,
) -> None:
    path = write_list(tmp_path)
    out = io.StringIO(newline="")
    csv.writer(out).writerow([*COLUMNS, header])
    path.write_text(out.getvalue())
    assert main(["--root", str(path.parents[1]), "check"]) == 1
    captured = capsys.readouterr()
    assert header not in captured.err + captured.out
    assert "unexpected" in captured.err
    assert "17" in captured.err


def test_make_build_treats_dataset_as_one_argument_without_executing_it(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(f"#!{sys.executable}\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    uv.chmod(0o755)
    marker = tmp_path / "shell-injection-marker"
    dataset = f"example'; touch {marker}; #"
    result = subprocess.run(
        [
            "make",
            "-s",
            "-f",
            str(Path(__file__).parents[1] / "Makefile"),
            "build",
            f"DATASET={dataset}",
        ],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert not marker.exists(), "the dataset value was evaluated as shell code"
    assert result.returncode == 0, result.stderr
    invocations = [json.loads(line) for line in result.stdout.splitlines()]
    assert invocations[-1] == ["run", "paraverse-curation", "build", "--dataset", dataset]


def test_build_rejects_unconfigured_dataset_before_running_its_pipeline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_list(tmp_path, dataset="ptc2026-md")
    pipeline = tmp_path / "vendor/ptc2026-md/pipeline"
    pipeline.mkdir(parents=True)
    (pipeline / "pyproject.toml").write_text("[project]\nname = 'example'\n")
    (pipeline / "uv.toml").write_text("exclude-newer = '14 days'\n")
    with patch("paraverse_curation.cli.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0)
        assert main(["--root", str(path.parents[1]), "build", "--dataset", "ptc2026-md"]) == 1
        run.assert_not_called()
    assert "No build handoff is configured" in capsys.readouterr().err
