"""
Softschema validation of KB artifacts: a valid artifact passes, each kind of breakage
is reported with its path, real artifacts pass, and `paraverse-graph load --validate`
refuses to load a KB with a broken artifact, however the dataset is named.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from paraverse_graph.cli import main
from paraverse_graph.connection import graph_exists, open_db
from paraverse_graph.datasets import KB_ENV, graph_name
from paraverse_graph.kb import DEFAULT_DATASET, KB_RELATIVE_PATH, find_kb_root
from paraverse_graph.validation import artifact_paths, validate_artifacts

SAMPLE = "sessions/1809k.md"


def _real_kb() -> Path:
    root = find_kb_root(Path(__file__).parent)
    if root is None or not (root / SAMPLE).is_file():
        pytest.skip(f"{KB_RELATIVE_PATH} is not checked out; run `git submodule update --init`")
    return root


def _one_artifact_kb(tmp: Path) -> Path:
    """A KB holding one real session and its compiled schema."""
    real = _real_kb()
    kb = tmp / "kb"
    (kb / "sessions").mkdir(parents=True)
    (kb / "_schemas").mkdir()
    shutil.copy(real / SAMPLE, kb / SAMPLE)
    shutil.copy(real / "_schemas" / "session.schema.yaml", kb / "_schemas")
    return kb


def _break(kb: Path, old: str, new: str) -> None:
    path = kb / SAMPLE
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def test_a_valid_artifact_passes():
    with TemporaryDirectory() as tmp:
        report = validate_artifacts(_one_artifact_kb(Path(tmp)))
        assert report.ok and report.checked == 1
        assert [c.split(":")[-1].split("/")[0] for c in report.contracts] == ["Session"]


def test_each_kind_of_breakage_is_reported():
    breakages = {
        "wrong type": ("  sponsored: false\n", "  sponsored: maybe\n"),
        "missing required field": ("  code: ", "  former_code: "),
        "extra field in a closed nested shape": ("  - start: ", "  - surprise: 1\n    start: "),
        "schema pointer escapes": (
            "schema: ../_schemas/session.schema.yaml",
            "schema: ../../../x.yaml",
        ),
        "no softschema block": ("softschema:\n", "not_softschema:\n"),
    }
    for name, (old, new) in breakages.items():
        with TemporaryDirectory() as tmp:
            kb = _one_artifact_kb(Path(tmp))
            _break(kb, old, new)
            report = validate_artifacts(kb)
            assert not report.ok, name
            assert report.problems[0].path == SAMPLE and report.problems[0].errors, name


def test_real_artifacts_pass():
    real = _real_kb()
    # A spread across every directory keeps this fast; `paraverse-graph load --validate`
    # checks all of them.
    paths = artifact_paths(real)
    sample = paths[:: max(1, len(paths) // 300)]
    report = validate_artifacts(real, sample)
    assert report.ok, report.problems[:3]
    assert len(report.contracts) >= 10


@pytest.mark.parametrize("source", ["--kb", "--dataset", KB_ENV, "default"])
def test_load_validate_refuses_a_broken_kb(
    source: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    name = DEFAULT_DATASET if source == "default" else "broken"
    kb = _one_artifact_kb(tmp_path / "vendor" / name)
    (kb / "_graph").mkdir()
    (kb / "_graph" / "nodes.jsonl").write_text("")
    _break(kb, "  sponsored: false\n", "  sponsored: maybe\n")
    db_file = tmp_path / "test.rdb"
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    args = ["load", "--validate", "--db", str(db_file)]
    if source == "--kb":
        args += ["--kb", str(kb)]
    elif source == "--dataset":
        args += ["--dataset", name]
    elif source == KB_ENV:
        monkeypatch.setenv(KB_ENV, str(kb))
    assert main(args) == 1
    assert "failed validation" in " ".join(capsys.readouterr().err.split())
    assert not graph_exists(open_db(db_file), graph_name(name))


_MALFORMED = {
    "bad-flow.md": "---\nsoftschema: {contract: x\n---\n",
    "tab-indent.md": "---\nsoftschema:\n\tcontract: x\n---\n",
    "unclosed.md": "---\nsoftschema:\n  contract: x\n",
    "list-frontmatter.md": "---\n- a\n- b\n---\n",
    "bad-quote.yaml": 'softschema:\n  contract: "x\n',
    "list-root.yaml": "- a\n- b\n",
    "scalar-root.yaml": "just a string\n",
}


@pytest.mark.parametrize(("name", "text"), _MALFORMED.items(), ids=list(_MALFORMED))
def test_a_malformed_document_is_reported_not_raised(name: str, text: str, tmp_path: Path):
    """Bad YAML, or YAML that is not a mapping, is one more failed artifact."""
    (tmp_path / "kb" / "sessions").mkdir(parents=True)
    (tmp_path / "kb" / "sessions" / name).write_text(text)
    report = validate_artifacts(tmp_path / "kb")
    assert report.checked == 1 and not report.ok
    [problem] = report.problems
    assert problem.path == f"sessions/{name}" and problem.errors
