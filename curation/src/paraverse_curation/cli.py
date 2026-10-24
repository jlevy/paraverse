"""Check curation lists and rebuild a dataset from its existing supported inputs."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from paraverse_curation.people import ListReport, check_list, find_lists

# A dataset handoff needs its own known entry point; mounted datasets are not
# automatically compatible with the universe2026 pipeline command.
_BUILD_COMMANDS: dict[str, tuple[str, ...]] = {"universe2026-md": ("universe-kb", "build")}


def reports(root: Path, paths: list[Path]) -> list[ListReport]:
    selected = paths or find_lists(root)
    if not selected:
        raise ValueError("No <dataset>/additional-people.csv lists found under the curation root")
    return [
        check_list(path, str(path.relative_to(root)) if path.is_relative_to(root) else str(path))
        for path in selected
    ]


def show_reports(checked: list[ListReport]) -> bool:
    for report in checked:
        for problem in report.problems:
            print(problem, file=sys.stderr)
    if any(report.problems for report in checked):
        return False
    print(f"Checked {len(checked)} list(s), {sum(r.rows for r in checked)} row(s).")
    return True


def build_dataset(root: Path, dataset: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", dataset):
        raise ValueError("Dataset must be a single directory name")
    command = _BUILD_COMMANDS.get(dataset)
    if command is None:
        raise ValueError(
            "No build handoff is configured for this dataset; supported: "
            + ", ".join(_BUILD_COMMANDS)
        )
    checked = reports(root, [root / dataset / "additional-people.csv"])
    if not show_reports(checked):
        return 1
    if checked[0].rows:
        raise ValueError(
            "Populated additional-people intake is not implemented by this handoff; "
            "no dataset build was run. See README.md for the ingestion follow-up."
        )
    pipeline = root.parent / "vendor" / dataset / "pipeline"
    if not (pipeline / "pyproject.toml").is_file() or not (pipeline / "uv.toml").is_file():
        raise ValueError(
            f"Dataset pipeline is unavailable at vendor/{dataset}/pipeline; "
            "initialize the dataset submodule first"
        )
    env = dict(os.environ)
    # The curation Makefile exports its lock cutoff. Let the dataset's own config
    # choose its cutoff, and require its existing lock instead of rewriting it.
    env.pop("UV_EXCLUDE_NEWER", None)
    env["UV_CONFIG_FILE"] = str(pipeline / "uv.toml")
    if env.get("UV_PROJECT_ENVIRONMENT"):
        env["UV_PROJECT_ENVIRONMENT"] = str(
            Path(env["UV_PROJECT_ENVIRONMENT"]).resolve().parent / f"{dataset}-pipeline-venv"
        )
    return subprocess.run(
        ["uv", "run", "--locked", *command], cwd=pipeline, env=env, check=False
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Curation directory.")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Check every list, or selected CSV files.")
    check.add_argument("files", nargs="*", type=Path)
    build = commands.add_parser(
        "build", help="Build a dataset after checking its empty intake list."
    )
    build.add_argument("--dataset", default="universe2026-md")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "check":
            return 0 if show_reports(reports(root, args.files)) else 1
        return build_dataset(root, args.dataset)
    except (OSError, ValueError) as error:
        print(f"curation: {error}", file=sys.stderr)
        return 1
