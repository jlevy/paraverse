from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from paraverse_curation.cli import main
from paraverse_curation.people import COLUMNS


def write_list(root: Path, rows: list[dict[str, str]] | None = None) -> Path:
    path = root / "curation" / "example-data" / "additional-people.csv"
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


def test_build_hands_empty_lists_to_the_dataset_with_its_own_uv_config(tmp_path: Path) -> None:
    path = write_list(tmp_path)
    pipeline = tmp_path / "vendor/example-data/pipeline"
    pipeline.mkdir(parents=True)
    (pipeline / "pyproject.toml").write_text("[project]\nname = 'example'\n")
    (pipeline / "uv.toml").write_text("exclude-newer = '14 days'\n")
    with patch("paraverse_curation.cli.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 7)
        assert main(["--root", str(path.parents[1]), "build", "--dataset", "example-data"]) == 7
        call = run.call_args
        assert call is not None
        assert call.args[0] == ["uv", "run", "universe-kb", "build"]
        assert call.kwargs["cwd"] == pipeline
        assert call.kwargs["env"]["UV_CONFIG_FILE"] == str(pipeline / "uv.toml")


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
        assert main(["--root", str(path.parents[1]), "build", "--dataset", "example-data"]) == 1
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
