"""
Dataset resolution, discovery and graph naming, on temporary `vendor/` trees.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from paraverse_graph.cli import main
from paraverse_graph.datasets import (
    KB_ENV,
    dataset_name,
    graph_name,
    list_datasets,
    resolve_dataset,
)
from paraverse_graph.kb import DEFAULT_DATASET, KbError


def _kb(kb_root: Path) -> Path:
    """
    A directory that passes for a KB: just the graph export's node file.
    """
    (kb_root / "_graph").mkdir(parents=True)
    (kb_root / "_graph" / "nodes.jsonl").write_text("")
    return kb_root


def _repo(root: Path) -> Path:
    """
    A checkout with the default dataset and `other` mounted, an uninitialized
    submodule `empty`, and a `db/` component to run from.
    """
    _kb(root / "vendor" / DEFAULT_DATASET / "kb")
    _kb(root / "vendor" / "other" / "kb")
    (root / "vendor" / "empty").mkdir()
    (root / "db").mkdir()
    return root / "db"


def test_resolution_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    start = _repo(tmp_path)
    explicit = _kb(tmp_path / "builds" / "trial" / "kb")
    from_env = _kb(tmp_path / "env-build" / "kb")
    monkeypatch.delenv(KB_ENV, raising=False)

    default = resolve_dataset(start=start)
    assert (default.name, default.kb_root, default.graph) == (
        DEFAULT_DATASET,
        tmp_path / "vendor" / DEFAULT_DATASET / "kb",
        "universe2026_md",
    )

    monkeypatch.setenv(KB_ENV, str(from_env))
    assert resolve_dataset(start=start).kb_root == from_env
    assert resolve_dataset(start=start).name == "env-build"

    named = resolve_dataset(name="other", start=start)
    assert (named.name, named.kb_root) == ("other", tmp_path / "vendor" / "other" / "kb")

    chosen = resolve_dataset(kb=explicit, name="other", start=start)
    assert (chosen.name, chosen.kb_root, chosen.require_kb()) == ("trial", explicit, explicit)


def test_missing_kb_errors_say_how_to_get_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    start = _repo(tmp_path)
    monkeypatch.delenv(KB_ENV, raising=False)
    for dataset in (
        resolve_dataset(name="empty", start=start),
        resolve_dataset(name="absent", start=start),
        resolve_dataset(start=tmp_path.parent / "nowhere"),
        resolve_dataset(kb=tmp_path / "vendor" / "empty"),
    ):
        try:
            dataset.require_kb()
        except KbError as e:
            assert "git submodule update --init" in str(e)
        else:
            raise AssertionError(f"{dataset} has no KB but was accepted")
    # A missing KB does not stop serving an already loaded graph under its name.
    assert resolve_dataset(name="absent", start=start).graph == "dataset_616273656e74"
    for bad in ("../other", "a/b", ".hidden"):
        try:
            resolve_dataset(name=bad, start=start)
        except KbError as e:
            assert "invalid dataset name" in str(e)
        else:
            raise AssertionError(f"dataset name {bad!r} was accepted")


def test_discovery_lists_checked_out_datasets_nearest_first(tmp_path: Path):
    start = _repo(tmp_path)
    nearer = _kb(tmp_path / "db" / "vendor" / "other" / "kb")
    found = {d.name: d.kb_root for d in list_datasets(start)}
    assert found == {
        DEFAULT_DATASET: tmp_path / "vendor" / DEFAULT_DATASET / "kb",
        "other": nearer,
    }
    assert list_datasets(tmp_path.parent / "nowhere") == []


def test_dataset_and_graph_names():
    assert dataset_name(Path("x/vendor/universe2026-md/kb")) == "universe2026-md"
    assert dataset_name(Path("builds/Trial Run")) == "Trial Run"
    assert dataset_name(Path("vendor/other/kb/../kb")) == "other"
    assert graph_name("universe2026-md") == "universe2026_md"
    assert graph_name("Trial Run.v2") == "dataset_547269616c2052756e2e7632"


def test_distinct_dataset_names_never_share_the_default_graph():
    names = [DEFAULT_DATASET, "universe2026_md", "foo-bar", "foo_bar", "Foo", "foo", "a.b", "a-b"]
    graphs = [graph_name(name) for name in names]
    assert len(set(graphs)) == len(names)
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", graph) for graph in graphs)


@pytest.mark.parametrize("change", ["artifact", "root", "schema", "stats"])
def test_kb_rejects_a_build_changed_while_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
):
    from paraverse_graph import kb

    root = _one_person_kb(tmp_path / "kb")
    (root / "_schemas").mkdir()
    (root / "_schemas" / "person.schema.yaml").write_text("type: object\n")
    original = kb.read_artifact

    def read_then_change(path: Path, rel_path: str) -> kb.Artifact:
        artifact = original(path, rel_path)
        if change == "root":
            replacement = tmp_path / "replacement"
            shutil.copytree(root, replacement)
            root.rename(tmp_path / "previous")
            replacement.rename(root)
        elif change == "artifact":
            # Same node/edge counts and stats, but different structured content.
            replacement = path.with_suffix(".new")
            replacement.write_text(path.read_text().replace("person:a", "person:b"))
            replacement.replace(path)
        elif change == "schema":
            (root / "_schemas" / "person.schema.yaml").write_text("type: string\n")
        else:
            stats = root / "_graph" / "stats.json"
            stats.write_text(stats.read_text() + "\n")
        return artifact

    monkeypatch.setattr(kb, "read_artifact", read_then_change)
    with pytest.raises(KbError, match="changed while reading"):
        kb.load_kb(root)


def test_datasets_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.chdir(_repo(tmp_path))
    assert main(["datasets", "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [(r["name"], r["graph"], r["default"]) for r in rows] == [
        ("other", "dataset_6f74686572", False),
        (DEFAULT_DATASET, "universe2026_md", True),
    ]
    assert rows[0]["kb"] == str(tmp_path / "vendor" / "other" / "kb")


def test_load_without_the_kb_says_how_to_get_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.chdir(_repo(tmp_path))
    monkeypatch.delenv(KB_ENV, raising=False)
    assert main(["load", "--dataset", "empty"]) == 1
    message = " ".join(capsys.readouterr().err.split())
    assert "vendor/empty/kb" in message
    assert "git submodule update --init" in message


def _one_person_kb(kb_root: Path, **broken: str | bytes) -> Path:
    """
    A loadable one-person KB, with any file replaced by the `broken` content given
    for its path (`stats.json` for `_graph/stats.json`, say).
    """
    files: dict[str, str | bytes] = {
        "_graph/nodes.jsonl": json.dumps(
            {"id": "person:a", "kind": "person", "name": "A", "path": "people/a.md"}
        )
        + "\n",
        "_graph/edges.jsonl": "",
        "_graph/stats.json": json.dumps({"nodes": {"person": 1}, "edges": {}}),
        "people/a.md": "---\nsoftschema:\n  contract: test:Person/v1\n  envelope: person\n"
        "person:\n  id: person:a\n---\n",
    }
    aliases = {"nodes": "_graph/nodes.jsonl", "stats": "_graph/stats.json", "person": "people/a.md"}
    files |= {aliases[k]: v for k, v in broken.items()}
    for rel_path, content in files.items():
        path = kb_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
    return kb_root


def test_malformed_kb_files_are_one_line_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    good_row = json.dumps({"id": "person:a", "kind": "person", "name": "A", "path": "people/a.md"})
    cases = {
        "bad-row": ({"nodes": good_row + "\n{oops\n"}, "nodes.jsonl:2"),
        "not-object": ({"nodes": "[1]\n"}, "nodes.jsonl:1"),
        "missing-key": ({"nodes": '{"id": "person:a", "kind": "person"}\n'}, "nodes.jsonl:1"),
        "bad-stats": ({"stats": "{"}, "stats.json"),
        "bad-yaml": ({"person": "---\nsoftschema: [\n---\n"}, "people/a.md"),
        "not-utf8": ({"person": b"---\nname: \xff\n---\n"}, "people/a.md"),
    }
    for name, (broken, where) in cases.items():
        kb_root = _one_person_kb(tmp_path / name / "kb", **broken)
        assert main(["load", "--kb", str(kb_root), "--db", str(tmp_path / "x.rdb")]) == 1, name
        message = " ".join(capsys.readouterr().err.split())
        assert "error:" in message, (name, message)
        assert where in message.partition("error:")[2], (name, message)
