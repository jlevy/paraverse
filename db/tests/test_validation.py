"""
Softschema validation of KB artifacts: a valid artifact passes, each kind of breakage
is reported with its path, real artifacts pass, and `paraverse-graph load --validate`
refuses to load a KB with a broken artifact, however the dataset is named.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from paraverse_graph import validation
from paraverse_graph.cli import main
from paraverse_graph.connection import graph_exists, open_db
from paraverse_graph.datasets import KB_ENV, graph_name
from paraverse_graph.kb import DEFAULT_DATASET, KB_RELATIVE_PATH, KbError, find_kb_root, load_kb
from paraverse_graph.validation import (
    ArtifactProblem,
    ValidationReport,
    artifact_paths,
    validate_artifacts,
)

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


def test_load_validate_lists_every_failed_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """Each failure gets a line of its own with its path, however many there are."""
    kb = tmp_path / "many" / "kb"
    (kb / "_graph").mkdir(parents=True)
    (kb / "_graph" / "nodes.jsonl").write_text("")
    (kb / "sessions").mkdir()
    paths = [f"sessions/s{i}.md" for i in range(7)]
    for path in paths:
        (kb / path).write_text("---\ntitle: no softschema block\n---\n")
    # Error text is printed as is, not read as Rich markup.
    paths.append("sessions/markup.md")
    (kb / paths[-1]).write_text(
        "---\nsoftschema:\n  contract: test:Session/v1\n  envelope: session\n"
        "  schema: '[red].yaml'\n  status: enforced\nsession: {}\n---\n"
    )
    db_file = tmp_path / "test.rdb"
    assert main(["load", "--validate", "--kb", str(kb), "--db", str(db_file)]) == 1
    lines = capsys.readouterr().err.splitlines()
    for path in paths:
        assert sum(line.startswith(f"  {path}: ") for line in lines) == 1, path
    assert any("[red]" in line for line in lines)
    assert "8 of 8 artifacts failed validation" in " ".join(" ".join(lines).split())
    assert not graph_exists(open_db(db_file), graph_name("many"))


def test_a_problem_line_bounds_its_errors():
    errors = ["first\n  wrapped", "second", "third", "fourth", "fifth"]
    line = ArtifactProblem(path="sessions/a.md", errors=errors).line()
    assert line == "sessions/a.md: first wrapped; second; third; and 2 more"


def _one_person_kb(kb: Path, contract_line: str) -> None:
    """A KB with one person node, whose artifact has `contract_line` in its block."""
    (kb / "_graph").mkdir(parents=True)
    (kb / "people").mkdir()
    node = {"id": "person:p0", "kind": "person", "name": "P0", "path": "people/p0.md"}
    (kb / "_graph" / "nodes.jsonl").write_text(json.dumps(node) + "\n")
    (kb / "_graph" / "edges.jsonl").write_text("")
    (kb / "_graph" / "stats.json").write_text('{"nodes": {"person": 1}, "edges": {}}')
    (kb / "people" / "p0.md").write_text(
        f"---\nsoftschema:\n{contract_line}  envelope: person\n"
        "person:\n  id: person:p0\n  name: P0\n---\n"
    )


_NO_CONTRACT = {
    "missing": "",
    "null": "  contract: null\n",
    "tilde": "  contract: ~\n",
    "empty": "  contract: ''\n",
    "blank": "  contract: '   '\n",
    "number": "  contract: 5\n",
}


@pytest.mark.parametrize("contract_line", _NO_CONTRACT.values(), ids=list(_NO_CONTRACT))
def test_an_ordinary_load_needs_a_contract_name(
    contract_line: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """Without `--validate`, a node's artifact must still name a contract."""
    kb = tmp_path / "nocontract" / "kb"
    _one_person_kb(kb, contract_line)
    with pytest.raises(KbError, match="names no softschema contract"):
        load_kb(kb)
    db_file = tmp_path / "test.rdb"
    assert main(["load", "--kb", str(kb), "--db", str(db_file)]) == 1
    assert "names no softschema contract" in " ".join(capsys.readouterr().err.split())
    assert not graph_exists(open_db(db_file), graph_name("nocontract"))


def test_an_ordinary_load_reads_a_contract_name(tmp_path: Path):
    kb = tmp_path / "kb"
    _one_person_kb(kb, "  contract: test:Person/v1\n")
    assert load_kb(kb).artifacts["people/p0.md"].contract == "test:Person/v1"


@pytest.mark.parametrize("replacement", ["after_validation", "before_read"])
@pytest.mark.parametrize("suffix", [".md", ".yml", ".record"])
def test_validate_refuses_an_artifact_replaced_after_validation(
    replacement: str,
    suffix: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    kb = tmp_path / "race" / "kb"
    _synthetic_schema_kb(kb)
    (kb / "people/p0.md").rename(kb / f"people/p0{suffix}")
    nodes = kb / "_graph/nodes.jsonl"
    nodes.write_text(nodes.read_text().replace("people/p0.md", f"people/p0{suffix}"))
    assert validate_artifacts(kb).ok

    def replace_artifact(root: Path) -> None:
        artifact = root / f"people/p0{suffix}"
        artifact.write_text(
            artifact.read_text().replace("  name: P0\n", "  name: P0\n  surprise: true\n")
        )
        assert not validate_artifacts(root).ok

    def replace_after_validation(root: Path) -> ValidationReport:
        report = validate_artifacts(root)
        replace_artifact(root)
        return report

    def replace_before_read(root: Path) -> Any:
        replace_artifact(root)
        return load_kb(root)

    if replacement == "after_validation":
        monkeypatch.setattr(validation, "validate_artifacts", replace_after_validation)
    else:
        monkeypatch.setattr("paraverse_graph.cli.load_kb", replace_before_read)
    db_file = tmp_path / "race.rdb"
    assert main(["load", "--validate", "--kb", str(kb), "--db", str(db_file)]) == 1
    assert "KB changed while reading" in capsys.readouterr().err
    assert not graph_exists(open_db(db_file), graph_name("race"))


def _synthetic_schema_kb(kb: Path) -> None:
    _one_person_kb(
        kb,
        "  contract: test:Person/v1\n  schema: ../_schemas/person.schema.yaml\n  status: enforced\n",
    )
    (kb / "_schemas").mkdir()
    (kb / "_schemas/person.schema.yaml").write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                "required": ["id", "name"],
                "additionalProperties": False,
                "x-softschema": {"contract": "test:Person/v1"},
            }
        )
    )


@pytest.mark.parametrize(
    ("suffix", "frontmatter"), [(".yml", False), (".record", False), (".record", True)]
)
def test_validation_covers_graph_references_of_every_extension(
    suffix: str,
    frontmatter: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    kb = tmp_path / "extended" / "kb"
    _synthetic_schema_kb(kb)
    rel = f"people/p1{suffix}"
    node = {"id": "person:p1", "kind": "person", "name": "P1", "path": rel}
    with (kb / "_graph/nodes.jsonl").open("a") as stream:
        stream.write(json.dumps(node) + "\n")
    document = (
        "softschema:\n  contract: test:Person/v1\n  envelope: person\n"
        "  schema: ../_schemas/person.schema.yaml\n  status: enforced\n"
        "person:\n  id: person:p1\n  name: P1\n"
    )
    (kb / rel).write_text(f"---\n{document}---\n" if frontmatter else document)
    assert rel in load_kb(kb).artifacts
    report = validate_artifacts(kb)
    assert report.ok and report.checked == 2
    (kb / rel).write_text((kb / rel).read_text().replace("  name: P1\n", "  name: 7\n"))
    report = validate_artifacts(kb)
    assert not report.ok and report.checked == 2
    assert [problem.path for problem in report.problems] == [rel]

    def must_not_open_graph(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Invalid artifacts must be rejected before opening the graph")

    monkeypatch.setattr("paraverse_graph.cli._open_graph", must_not_open_graph)
    assert main(["load", "--validate", "--kb", str(kb)]) == 1
    assert rel in capsys.readouterr().err


def test_validation_discovers_an_unreferenced_yml_artifact(tmp_path: Path):
    kb = tmp_path / "kb"
    _synthetic_schema_kb(kb)
    (kb / "people/invalid.yml").write_text(
        "softschema:\n  contract: test:Person/v1\n  envelope: person\n"
        "  schema: ../_schemas/person.schema.yaml\n  status: enforced\n"
        "person:\n  id: person:p1\n  name: 7\n"
    )
    report = validate_artifacts(kb)
    assert report.checked == 2 and not report.ok
    assert [problem.path for problem in report.problems] == ["people/invalid.yml"]


def test_empty_kb_validation_reports_no_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    kb = tmp_path / "empty" / "kb"
    (kb / "_graph").mkdir(parents=True)
    (kb / "_graph/nodes.jsonl").write_text("")

    def must_not_open_graph(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Empty KBs must be rejected before opening the graph")

    monkeypatch.setattr("paraverse_graph.cli._open_graph", must_not_open_graph)
    assert main(["load", "--validate", "--kb", str(kb)]) == 1
    error = " ".join(capsys.readouterr().err.split()).lower()
    assert "no artifacts found" in error
    assert "0 of 0" not in error


@pytest.mark.parametrize("frontmatter", [False, True])
@pytest.mark.parametrize(
    "replacement",
    ["  name: *name\n", "  <<: {name: P0}\n"],
)
def test_validation_rejects_nonportable_yaml(frontmatter: bool, replacement: str, tmp_path: Path):
    kb = tmp_path / "portable" / "kb"
    _synthetic_schema_kb(kb)
    artifact = kb / "people/p0.md"
    text = artifact.read_text()
    text = text.replace("  name: P0\n", replacement)
    if "*name" in replacement:
        text = text.replace("  id: person:p0\n", "  id: &name person:p0\n")
    if not frontmatter:
        text = text.split("---\n", 2)[1]
    artifact.write_text(text)
    report = validate_artifacts(kb)
    assert not report.ok
    assert len(report.problems) == 1
    assert "not supported" in report.problems[0].errors[0]
