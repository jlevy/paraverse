"""
Read a conference softschema knowledge base: its graph export and the artifacts
behind it.

The graph export (`kb/_graph/nodes.jsonl`, `edges.jsonl`, `stats.json`) is the
authority for which nodes and edges exist, because the KB build already validates
that every edge resolves. Node properties come from each node's softschema
artifact, the only source of structured values. Markdown bodies are never read.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Each dataset is its own repository, mounted as a git submodule at `vendor/<name>/`,
# with its KB in `kb/`.
VENDOR_DIR = "vendor"
DEFAULT_DATASET = "universe2026-md"
KB_RELATIVE_PATH = Path(VENDOR_DIR, DEFAULT_DATASET, "kb")

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
_PARENT_ENVELOPE = {"day": "event", "term": "facet"}


# libyaml's parser is several times faster on the ~2,400 artifacts; its resolver is
# still the Python one, so the timestamp override below applies to both.
_BaseLoader: type[yaml.SafeLoader] = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class _PortableScalarLoader(_BaseLoader):
    """
    Safe loader that keeps date- and timestamp-shaped scalars as strings, which is
    how softschema treats them. PyYAML would otherwise turn unquoted ones into
    `datetime` objects that do not round-trip to JSON.
    """


_PortableScalarLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != _TIMESTAMP_TAG]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


class KbError(ValueError):
    """The knowledge base is missing, unreadable or inconsistent."""


@dataclass(frozen=True)
class Artifact:
    path: str
    contract: str
    envelope: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class KbNode:
    id: str
    kind: str
    name: str
    path: str


@dataclass(frozen=True)
class KbEdge:
    source: str
    relation: str
    target: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeBase:
    """
    One KB build as read. `digest` is a short hash of the `nodes.jsonl` and
    `edges.jsonl` bytes that were parsed, so it names this content even if a rebuild
    replaces the files while a load runs.
    """

    root: Path
    nodes: list[KbNode]
    edges: list[KbEdge]
    stats: dict[str, Any]
    artifacts: dict[str, Artifact]
    digest: str
    snapshot: dict[str, tuple[int, ...]] | None = field(default=None, repr=False)

    def check_unchanged(self) -> None:
        """Reject a build replaced or edited since its graph/artifact reads began."""
        if self.snapshot is not None and build_snapshot(self.root) != self.snapshot:
            raise KbError("KB changed while reading; retry after the build finishes")

    def payload_for(self, node: KbNode) -> dict[str, Any]:
        """
        The structured record for a node. Most nodes own their artifact; days and
        taxonomy terms are nested value objects inside the event and facet
        artifacts, so those are found by ID inside the parent payload.
        """
        artifact = self.artifacts.get(node.path)
        if artifact is None:
            raise KbError(f"{node.path}: no artifact for graph node `{node.id}`")
        own_id = artifact.payload.get("id")
        if isinstance(own_id, str) and (own_id == node.id or f"{node.kind}:{own_id}" == node.id):
            return artifact.payload
        payload = _find_by_id(artifact.payload, node.id)
        if payload is None:
            raise KbError(f"{node.path}: no matching payload for graph node `{node.id}`")
        return payload


def referenced_artifact_paths(root: Path) -> set[str]:
    """Every artifact path the graph export will load, regardless of its extension."""
    nodes = root / "_graph" / "nodes.jsonl"
    if not nodes.is_file():
        return set()
    return {row["path"] for row in _parse_jsonl(nodes.read_bytes(), nodes, ("id", "kind", "path"))}


def read_artifact_document(path: Path, rel_path: str) -> tuple[dict[str, Any], bool]:
    """Read portable YAML and report whether the document has Markdown frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER.match(text)
        data = yaml.load(match.group(1) if match else text, Loader=_PortableScalarLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as e:
        raise KbError(f"{rel_path}: cannot parse: {e}") from e
    if not isinstance(data, dict):
        raise KbError(f"{rel_path}: not a YAML mapping")
    return data, match is not None


def read_artifact(path: Path, rel_path: str, *, envelope_hint: str | None = None) -> Artifact:
    """
    Read a frontmatter-md or pure-yaml artifact and return its envelope payload.
    `envelope_hint` comes from the graph kind and identifies an unwrapped YAML root.
    """
    data, frontmatter = read_artifact_document(path, rel_path)
    block = data.get("softschema")
    if not isinstance(block, dict):
        raise KbError(f"{rel_path}: missing softschema block")
    if "envelope" in block:
        envelope = block["envelope"]
        payload = data.get(envelope) if isinstance(envelope, str) else None
    elif frontmatter:
        candidates = [key for key in data if key != "softschema"]
        if len(candidates) != 1:
            raise KbError(f"{rel_path}: ambiguous frontmatter envelope")
        envelope = candidates[0]
        payload = data[envelope]
    else:
        if envelope_hint is None:
            raise KbError(f"{rel_path}: unwrapped YAML needs a graph node kind")
        envelope = envelope_hint
        payload = {key: value for key, value in data.items() if key != "softschema"}
    if not isinstance(envelope, str) or not envelope.strip():
        raise KbError(f"{rel_path}: envelope must be a nonempty string")
    if envelope_hint is not None and envelope != envelope_hint:
        raise KbError(f"{rel_path}: envelope `{envelope}` is incompatible with `{envelope_hint}`")
    if not isinstance(payload, dict):
        raise KbError(f"{rel_path}: envelope `{envelope}` is not a mapping")
    # Only a nonempty string names a contract; `str()` would turn `null` into "None".
    contract = block.get("contract")
    contract = contract.strip() if isinstance(contract, str) else ""
    return Artifact(path=rel_path, contract=contract, envelope=envelope, payload=payload)


def load_kb(root: Path) -> KnowledgeBase:
    """
    Load the graph export and every artifact a node points at.
    """
    graph_dir = root / "_graph"
    for name in ("nodes.jsonl", "edges.jsonl", "stats.json"):
        if not (graph_dir / name).is_file():
            raise KbError(f"{graph_dir / name} not found; the KB graph export is incomplete")

    snapshot = build_snapshot(root)

    sha = hashlib.sha256()
    node_bytes = (graph_dir / "nodes.jsonl").read_bytes()
    edge_bytes = (graph_dir / "edges.jsonl").read_bytes()
    sha.update(node_bytes)
    sha.update(edge_bytes)

    nodes = [
        KbNode(id=row["id"], kind=row["kind"], name=row.get("name") or row["id"], path=row["path"])
        for row in _parse_jsonl(node_bytes, graph_dir / "nodes.jsonl", ("id", "kind", "path"))
    ]
    edges = [
        KbEdge(
            source=row.pop("source"),
            relation=row.pop("relation"),
            target=row.pop("target"),
            attrs=row,
        )
        for row in _parse_jsonl(
            edge_bytes, graph_dir / "edges.jsonl", ("source", "relation", "target")
        )
    ]
    stats = _read_stats(graph_dir / "stats.json")

    artifacts: dict[str, Artifact] = {}
    envelopes_by_path: dict[str, set[str]] = {}
    for node in nodes:
        envelopes_by_path.setdefault(node.path, set()).add(
            _PARENT_ENVELOPE.get(node.kind, node.kind)
        )
    for rel_path, envelopes in sorted(envelopes_by_path.items()):
        if len(envelopes) != 1:
            raise KbError(
                f"{rel_path}: incompatible graph node kinds: {', '.join(sorted(envelopes))}"
            )
        path = root / rel_path
        if not path.is_file():
            raise KbError(f"{rel_path}: referenced by the graph export but missing")
        artifacts[rel_path] = read_artifact(path, rel_path, envelope_hint=next(iter(envelopes)))
    _check_envelopes(nodes, artifacts)

    kb = KnowledgeBase(
        root=root,
        nodes=nodes,
        edges=edges,
        stats=stats,
        artifacts=artifacts,
        digest=sha.hexdigest()[:16],
        snapshot=snapshot,
    )
    for node in nodes:
        kb.payload_for(node)
    kb.check_unchanged()
    return kb


def build_snapshot(root: Path) -> dict[str, tuple[int, ...]]:
    """
    Track the root, build marker, exports, artifacts and compiled schemas. Comparing
    metadata detects edits and directory swaps during a read. The producer must
    still publish a complete build atomically: a paused partial build cannot be
    distinguished from a complete one using file metadata alone.
    """
    try:
        paths = [
            root,
            *(p for p in root.rglob("*") if p.is_file()),
        ]
        result: dict[str, tuple[int, ...]] = {}
        for path in paths:
            st = path.stat()
            result[str(path.relative_to(root))] = (
                st.st_dev,
                st.st_ino,
                st.st_size,
                st.st_mtime_ns,
                st.st_ctime_ns,
            )
        return result
    except OSError as e:
        raise KbError(f"KB changed while reading; cannot inspect {e.filename}") from e


def _check_envelopes(nodes: list[KbNode], artifacts: dict[str, Artifact]) -> None:
    """
    Each node's artifact must declare the envelope of the node's kind (a day lives in
    an event, a term in a facet) and a contract. A mismatch means the graph export
    points at the wrong file, which would otherwise load silently with the wrong data.
    """
    problems = []
    for node in nodes:
        artifact = artifacts[node.path]
        expected = _PARENT_ENVELOPE.get(node.kind, node.kind)
        if artifact.envelope != expected:
            problems.append(
                f"{node.id}: {node.path} has envelope `{artifact.envelope}`, expected `{expected}`"
            )
        elif not artifact.contract:
            problems.append(f"{node.id}: {node.path} names no softschema contract")
    if problems:
        raise KbError(
            f"{len(problems)} nodes point at the wrong artifact: " + "; ".join(problems[:5])
        )


def find_kb_root(start: Path | None = None, dataset: str = DEFAULT_DATASET) -> Path | None:
    """
    Find `vendor/<dataset>/kb` by walking up from `start` (default: the working
    directory), so the CLI works from the repository root or from `db/`. `None` when
    no such KB has a graph export, as when the submodule is not checked out.
    """
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        candidate = directory / VENDOR_DIR / dataset / "kb"
        if (candidate / "_graph" / "nodes.jsonl").is_file():
            return candidate
    return None


def _parse_jsonl(
    data: bytes, source: Path | str, required: tuple[str, ...] = ()
) -> Iterator[dict[str, Any]]:
    """
    One JSON object per non-blank line, each with the `required` keys. A malformed
    line is a `KbError` naming `source` and the line number.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise KbError(f"{source}: not UTF-8: {e}") from e
    # Split on newlines only: `splitlines()` also splits on U+2028 and similar
    # characters, which JSON allows unescaped inside strings.
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise KbError(f"{source}:{number}: not valid JSON: {e}") from e
        if not isinstance(row, dict):
            raise KbError(f"{source}:{number}: not a JSON object")
        missing = [key for key in required if key not in row]
        if missing:
            raise KbError(f"{source}:{number}: missing {', '.join(missing)}")
        yield row


def _read_stats(path: Path) -> dict[str, Any]:
    try:
        stats = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise KbError(f"{path}: not valid JSON: {e}") from e
    if not isinstance(stats, dict):
        raise KbError(f"{path}: not a JSON object")
    return stats


def _find_by_id(value: Any, wanted: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("id") == wanted:
            return value
        children = value.values()
    elif isinstance(value, list):
        children = value
    else:
        return None
    for child in children:
        found = _find_by_id(child, wanted)
        if found is not None:
            return found
    return None


## Tests


def test_frontmatter_and_portable_timestamps():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.md"
        path.write_text(
            "---\ntitle: A\nsoftschema:\n  envelope: thing\nthing:\n  id: x:a\n  when: 2026-10-28\n---\nBody\n"
        )
        artifact = read_artifact(path, "a.md")
    assert artifact.envelope == "thing"
    assert artifact.payload == {"id": "x:a", "when": "2026-10-28"}


def test_jsonl_lines_split_on_newlines_only():
    data = '{"id": "a", "bio": "one\u2028two"}\r\n\n{"id": "b"}\n'.encode()
    assert [row["id"] for row in _parse_jsonl(data, "x.jsonl")] == ["a", "b"]


def test_nested_payload_lookup():
    kb = KnowledgeBase(
        root=Path("."),
        nodes=[],
        edges=[],
        stats={},
        artifacts={
            "taxonomy/level.yaml": Artifact(
                path="taxonomy/level.yaml",
                contract="",
                envelope="facet",
                payload={"id": "level", "terms": [{"id": "term:level/100", "label": "100"}]},
            )
        },
        digest="",
    )
    facet = KbNode(id="facet:level", kind="facet", name="Level", path="taxonomy/level.yaml")
    term = KbNode(id="term:level/100", kind="term", name="100", path="taxonomy/level.yaml")
    assert kb.payload_for(facet) == kb.artifacts["taxonomy/level.yaml"].payload
    assert kb.payload_for(term) == {"id": "term:level/100", "label": "100"}


def test_envelope_must_match_the_node_kind():
    session = Artifact(path="s.md", contract="x:Session/v1", envelope="session", payload={})
    event = Artifact(path="e.md", contract="x:Event/v1", envelope="event", payload={})
    ok = [
        KbNode(id="session:a", kind="session", name="A", path="s.md"),
        KbNode(id="day:2026-10-28", kind="day", name="Day 1", path="e.md"),
    ]
    _check_envelopes(ok, {"s.md": session, "e.md": event})
    wrong = [KbNode(id="person:a", kind="person", name="A", path="s.md")]
    try:
        _check_envelopes(wrong, {"s.md": session})
    except KbError as e:
        assert "expected `person`" in str(e)
    else:
        raise AssertionError("a person node pointing at a session artifact should fail")
