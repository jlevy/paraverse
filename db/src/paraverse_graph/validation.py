"""
Validate knowledge base artifacts with softschema before loading them.

Each artifact is checked the way a stock consumer checks it (`softschema validate
<artifact>` with no flags): against the compiled schema that its own `softschema:`
block names, at the status it declares. The KB build also checks its records with its
own Pydantic models; this check needs nothing from the build's code, so it works on any
copy of the KB. It is opt-in (`paraverse-graph load --validate`) because it takes tens
of seconds on the full KB, against about two seconds for a load.
"""

from __future__ import annotations

import contextlib
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import softschema

from paraverse_graph.kb import read_artifact_document, referenced_artifact_paths

# Generated or derived files that are not artifacts.
_SKIP_DIRS = frozenset({"_graph", "_schemas", "_search"})


@dataclass(frozen=True)
class ArtifactProblem:
    path: str
    errors: list[str]

    def line(self, max_errors: int = 3) -> str:
        """The path and its first `max_errors` errors, on one line."""
        shown = [" ".join(e.split()) for e in self.errors[:max_errors]]
        if len(self.errors) > max_errors:
            shown.append(f"and {len(self.errors) - max_errors} more")
        return f"{self.path}: {'; '.join(shown)}"


@dataclass
class ValidationReport:
    checked: int = 0
    contracts: Counter[str] = field(default_factory=Counter)
    problems: list[ArtifactProblem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.checked > 0 and not self.problems


def artifact_paths(kb_root: Path) -> list[str]:
    """Discovered artifacts and every graph-referenced path, relative to the KB."""
    paths = {
        str(p.relative_to(kb_root))
        for p in kb_root.rglob("*")
        if p.is_file()
        and p.suffix in (".md", ".yaml", ".yml")
        and p.name != "README.md"
        and not _SKIP_DIRS & set(p.relative_to(kb_root).parts)
    }
    paths.update(referenced_artifact_paths(kb_root))
    return sorted(paths)


def validate_artifacts(kb_root: Path, paths: Iterable[str] | None = None) -> ValidationReport:
    """
    Validate `paths` (default: every artifact) under `kb_root`. Runs from the KB's
    parent directory because softschema only follows a schema pointer that stays inside
    the artifact's directory or the working directory, and the KB's `_schemas/` is a
    sibling of the artifact directories.
    """
    root = kb_root.resolve()
    report = ValidationReport()
    with contextlib.chdir(root.parent):
        for rel in paths if paths is not None else artifact_paths(root):
            report.checked += 1
            doc_path = Path(root.name) / rel
            try:
                contract_id, errors = _validate_one(doc_path)
            except (OSError, ValueError) as e:
                contract_id, errors = None, [f"unreadable: {e}"]
            if contract_id:
                report.contracts[contract_id] += 1
            if errors:
                report.problems.append(ArtifactProblem(path=rel, errors=errors))
    return report


def _validate_one(doc_path: Path) -> tuple[str | None, list[str]]:
    document, frontmatter = read_artifact_document(doc_path, str(doc_path))
    profile = (
        softschema.SchemaProfile.frontmatter_md
        if frontmatter
        else softschema.SchemaProfile.pure_yaml
    )
    meta = softschema.parse_schema_metadata((document or {}).get("softschema"))
    if meta is None or not meta.contract_id or not meta.envelope or not meta.schema_ref:
        return None, [
            "not self-describing: the softschema block needs contract, schema and envelope"
        ]
    contract = softschema.Contract(
        id=meta.contract_id,
        envelope_key=meta.envelope,
        status=meta.status or softschema.SchemaStatus.soft,
        profile=profile,
    )
    result = softschema.validate_artifact(doc_path, contract=contract, document=document)
    errors = [_message(e) for e in result.structural.errors]
    if result.structural.skipped_reason:
        errors.append(f"structural check skipped: {result.structural.skipped_reason}")
    if result.outcome != "valid" and not errors:
        errors.append(f"outcome {result.outcome}")
    return meta.contract_id, errors


def _message(error: Any) -> str:
    if isinstance(error, dict):
        where = error.get("path") or error.get("instance_path") or ""
        text = error.get("message") or error.get("kind") or str(error)
        return f"{where}: {text}" if where else str(text)
    return str(error)
