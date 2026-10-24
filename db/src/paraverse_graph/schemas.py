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
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from paraverse_graph.kb import KbError
from paraverse_graph.kb import KindSchema as KindSchema
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


def load_kind_schemas(kb_root: Path) -> dict[str, KindSchema]:
    """
    One description per node kind. File names map to kinds (`github-account` to
    `github_account`); schemas with no node kind (`faq`, `media`) are skipped.
    """
    raw: dict[str, dict[str, Any]] = {}
    for path in sorted((kb_root / "_schemas").glob("*.schema.yaml")):
        kind = path.name.removesuffix(".schema.yaml").replace("-", "_")
        try:
            schema = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as e:
            raise KbError(f"{path}: cannot parse: {e}") from e
        if not isinstance(schema, dict):
            raise KbError(f"{path}: not a YAML mapping")
        raw[kind] = schema

    result: dict[str, KindSchema] = {}
    for kind, schema in raw.items():
        if kind in LABELS:
            result[kind] = _describe(kind, schema, schema)
    for kind, (parent, def_name) in NESTED_KINDS.items():
        parent_schema = raw.get(parent)
        if parent_schema and def_name in parent_schema.get("$defs", {}):
            result[kind] = _describe(kind, parent_schema["$defs"][def_name], parent_schema)
    return result


def merge_kind_schemas(
    sources: Mapping[str, Mapping[str, KindSchema]],
) -> dict[str, KindSchema]:
    """Union record fields and enum choices; only shared requirements stay required.

    Descriptions retain distinct source wording. Conflicting validation constraints
    become alternatives, while display titles use the first dataset alphabetically.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for name in sorted(sources):
        for kind, description in sources[name].items():
            if kind not in NESTED_KINDS:
                grouped.setdefault(kind, []).append(description.schema)
    raw = {kind: _union_schema(specs) for kind, specs in sorted(grouped.items())}
    result = {kind: _describe(kind, schema, schema) for kind, schema in raw.items()}
    for kind, (parent, def_name) in NESTED_KINDS.items():
        root = raw.get(parent, {})
        spec = root.get("$defs", {}).get(def_name)
        if spec is not None:
            result[kind] = _describe(kind, spec, root)
    return result


def _union_schema(specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge compatible schema shapes without discarding a source's accepted values."""
    result = deepcopy(specs[0])
    for spec in specs[1:]:
        if spec == result:
            continue
        # An enum-only schema and a nullable alternative can share all of the
        # scalar constraints below. Keep both rather than dropping one side's anyOf.
        if ("anyOf" in result) != ("anyOf" in spec):
            return {"anyOf": deepcopy(specs)}
        # Differing scalar constraints describe genuinely different alternatives.
        constraints = ("type", "$ref", "pattern", "const", "minimum", "maximum")
        if any(result.get(key) != spec.get(key) for key in constraints):
            return {"anyOf": deepcopy(specs)}
        for key in ("properties", "$defs"):
            if any(key in s for s in (result, spec)):
                left, right = result.get(key, {}), spec.get(key, {})
                result[key] = {
                    name: _union_schema([s[name] for s in (left, right) if name in s])
                    for name in sorted(left.keys() | right.keys())
                }
        if "required" in result or "required" in spec:
            result["required"] = sorted(
                set(result.get("required", [])) & set(spec.get("required", []))
            )
        if "enum" in result and "enum" in spec:
            result["enum"] = list(dict.fromkeys([*result["enum"], *spec["enum"]]))
        elif "enum" in result:
            del result["enum"]
        if "items" in result and "items" in spec:
            result["items"] = _union_schema([result["items"], spec["items"]])
        if "anyOf" in result and "anyOf" in spec:
            # Nullable fields use one value branch and one null branch. Merge the
            # value branches so the browser can still describe their enum or ref.
            left, right = result["anyOf"], spec["anyOf"]
            if len(left) == len(right) and all(
                a.get("type") == b.get("type") for a, b in zip(left, right, strict=True)
            ):
                result["anyOf"] = [_union_schema([a, b]) for a, b in zip(left, right, strict=True)]
            else:
                result["anyOf"] = left + [s for s in right if s not in left]
        description = spec.get("description")
        if description and description != result.get("description"):
            result["description"] = "\n\n".join(
                str(s) for s in (result.get("description"), description) if s
            )
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
    display = core
    if core.get("type") == "array":
        is_list = True
        core = _non_null(core.get("items", {}))
    def_name = core["$ref"].rsplit("/", 1)[-1] if "$ref" in core else None
    field: dict[str, Any] = {
        "name": name,
        "title": spec.get("title") or display.get("title") or name.replace("_", " ").capitalize(),
        "description": (spec.get("description") or display.get("description") or "").strip(),
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
    """Derive compatible display hints without changing validation alternatives."""
    options = _value_options(spec)
    if len(options) == 1:
        return options[0]
    if not options:
        return spec
    core = {
        key: value
        for key, value in options[0].items()
        if all(option.get(key) == value for option in options[1:])
    }
    core["anyOf"] = options
    titles = [option["title"] for option in options if option.get("title")]
    if titles:
        core["title"] = titles[0]
    descriptions = list(
        dict.fromkeys(option["description"] for option in options if option.get("description"))
    )
    if descriptions:
        core["description"] = "\n\n".join(descriptions)
    if all(option.get("type") == "array" for option in options):
        core["items"] = {"anyOf": [option.get("items", {}) for option in options]}
    if all("enum" in option for option in options):
        core["enum"] = list(dict.fromkeys(value for option in options for value in option["enum"]))
    return core


def _value_options(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if "anyOf" in spec:
        return [value for option in spec["anyOf"] for value in _value_options(option)]
    return [] if spec.get("type") == "null" else [spec]


def _ref_kinds(spec: dict[str, Any]) -> list[str]:
    if "anyOf" in spec:
        alternatives = [_ref_kinds(option) for option in _value_options(spec)]
        # A generic string or another scalar alternative is not always a typed ref.
        if not alternatives or not all(alternatives):
            return []
        return list(dict.fromkeys(kind for kinds in alternatives for kind in kinds))
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


def test_unreadable_schema_is_a_kb_error():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        (Path(tmp) / "_schemas").mkdir()
        (Path(tmp) / "_schemas" / "person.schema.yaml").write_text("properties: [\n")
        try:
            load_kind_schemas(Path(tmp))
        except KbError as e:
            assert "person.schema.yaml" in str(e)
        else:
            raise AssertionError("a broken schema file should be a KbError")
