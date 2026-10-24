"""
Describe each entity kind's fields from the KB's compiled softschema JSON Schemas.

The browser renders any record generically from these descriptions: field order,
titles, descriptions, JSON types, enums, which fields are typed references and to
which kinds, and the nested `$defs` shapes (time slots, affiliations, claims, ...).
The loader stores one description per kind in FalkorDB, so a UI reads everything,
schemas included, from the graph.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paraverse_graph.mapping import LABELS

# Typed-ID prefixes and the entity kind each one names.
PREFIX_KINDS: dict[str, str] = {
    "acct": "social_account",
    "day": "day",
    "event": "event",
    "experience": "experience",
    "facet": "facet",
    "gh": "github_account",
    "org": "organization",
    "page": "page",
    "person": "person",
    "pkg": "package",
    "profile": "profile",
    "repo": "repository",
    "room": "room",
    "session": "session",
    "site": "website",
    "software": "software",
    "term": "term",
    "venue": "venue",
}

# Kinds that are nested value objects inside another kind's artifact.
NESTED_KINDS: dict[str, tuple[str, str]] = {
    "day": ("event", "EventDay"),
    "term": ("facet", "Term"),
}

_REF_PATTERN = re.compile(r"^\^\(([a-z|]+)\):")


@dataclass(frozen=True)
class KindSchema:
    kind: str
    title: str
    description: str
    contract: str
    fields: list[dict[str, Any]]
    defs: dict[str, list[dict[str, Any]]]
    schema: dict[str, Any]


def load_kind_schemas(kb_root: Path) -> dict[str, KindSchema]:
    """
    One description per node kind. File names map to kinds (`github-account` to
    `github_account`); schemas with no node kind (`faq`, `media`) are skipped.
    """
    raw: dict[str, dict[str, Any]] = {}
    for path in sorted((kb_root / "_schemas").glob("*.schema.yaml")):
        kind = path.name.removesuffix(".schema.yaml").replace("-", "_")
        raw[kind] = yaml.safe_load(path.read_text(encoding="utf-8"))

    result: dict[str, KindSchema] = {}
    for kind, schema in raw.items():
        if kind in LABELS:
            result[kind] = _describe(kind, schema, schema)
    for kind, (parent, def_name) in NESTED_KINDS.items():
        parent_schema = raw.get(parent)
        if parent_schema and def_name in parent_schema.get("$defs", {}):
            result[kind] = _describe(kind, parent_schema["$defs"][def_name], parent_schema)
    return result


def _describe(kind: str, spec: dict[str, Any], root: dict[str, Any]) -> KindSchema:
    defs = root.get("$defs", {})
    return KindSchema(
        kind=kind,
        title=spec.get("title") or kind,
        description=(spec.get("description") or "").strip(),
        contract=str(root.get("x-softschema", {}).get("contract", "")),
        fields=describe_fields(spec),
        defs={name: describe_fields(d) for name, d in sorted(defs.items())},
        schema=spec,
    )


def describe_fields(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Field descriptions in a stable order: `id` first, then required fields, then the
    rest, each group alphabetical (compiled schemas do not keep declaration order).
    """
    required = set(spec.get("required", []))
    props: dict[str, Any] = spec.get("properties", {})
    order = sorted(props, key=lambda name: (name != "id", name not in required, name))
    return [_field(name, props[name], name in required) for name in order]


def _field(name: str, spec: dict[str, Any], required: bool) -> dict[str, Any]:
    is_list = False
    core = _non_null(spec)
    if core.get("type") == "array":
        is_list = True
        core = _non_null(core.get("items", {}))
    def_name = core["$ref"].rsplit("/", 1)[-1] if "$ref" in core else None
    field: dict[str, Any] = {
        "name": name,
        "title": spec.get("title") or name.replace("_", " ").capitalize(),
        "description": (spec.get("description") or "").strip(),
        "type": "object" if def_name else core.get("type", "any"),
        "list": is_list,
        "required": required,
    }
    ref_kinds = _ref_kinds(core)
    if ref_kinds:
        field["ref_kinds"] = ref_kinds
    if def_name:
        field["def"] = def_name
    if "enum" in core:
        field["enum"] = core["enum"]
    if core.get("pattern") == "^https?://":
        field["format"] = "url"
    return field


def _non_null(spec: dict[str, Any]) -> dict[str, Any]:
    """`X | None` compiles to `anyOf: [X, {type: null}]`; return X."""
    options = [s for s in spec.get("anyOf", []) if s.get("type") != "null"]
    return options[0] if len(options) == 1 else spec


def _ref_kinds(spec: dict[str, Any]) -> list[str]:
    match = _REF_PATTERN.match(str(spec.get("pattern", "")))
    if not match:
        return []
    return [PREFIX_KINDS[p] for p in match.group(1).split("|") if p in PREFIX_KINDS]


## Tests


def test_field_descriptions():
    spec = {
        "required": ["id", "title"],
        "properties": {
            "title": {"type": "string", "title": "Title"},
            "id": {"pattern": "^(session):x", "type": "string"},
            "github": {"anyOf": [{"pattern": "^(gh):x", "type": "string"}, {"type": "null"}]},
            "accounts": {"type": "array", "items": {"pattern": "^(gh|acct):x", "type": "string"}},
            "slots": {"type": "array", "items": {"$ref": "#/$defs/Slot"}},
            "photo_url": {"anyOf": [{"pattern": "^https?://", "type": "string"}, {"type": "null"}]},
            "basis": {"enum": ["a", "b"], "type": "string"},
        },
    }
    fields = {f["name"]: f for f in describe_fields(spec)}
    assert [f["name"] for f in describe_fields(spec)][:2] == ["id", "title"]
    assert fields["github"]["ref_kinds"] == ["github_account"]
    assert fields["accounts"]["ref_kinds"] == ["github_account", "social_account"]
    assert fields["accounts"]["list"] is True
    assert fields["slots"]["def"] == "Slot" and fields["slots"]["type"] == "object"
    assert fields["photo_url"]["format"] == "url"
    assert fields["basis"]["enum"] == ["a", "b"]
