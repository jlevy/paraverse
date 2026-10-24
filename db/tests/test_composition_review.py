"""Composition preserves source meaning in search, schema metadata and display."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from paraverse_graph.composition import compose_kbs
from paraverse_graph.connection import open_db
from paraverse_graph.kb import KbError
from paraverse_graph.loader import load_graph
from paraverse_graph.mapping import node_properties
from paraverse_graph.queries import fulltext_query
from tests.test_composition import write_kb


def test_scalar_conflict_variants_remain_searchable(tmp_path: Path):
    roots = {
        name: write_kb(
            tmp_path / name,
            [("organization", {"id": "org:shared", "name": "Shared", "description": text})],
        )
        for name, text in (("alpha", "Nebular research"), ("beta", "Quasar engineering"))
    }
    kb = compose_kbs(roots)
    db = open_db(tmp_path / "search.rdb")
    try:
        load_graph(db, kb, "search")
        graph = db.select_graph("search")
        for term in ("Nebular", "Quasar"):
            rows = graph.ro_query(
                "CALL db.idx.fulltext.queryNodes('Entity', $q) YIELD node "
                "RETURN node.id, node.description, node.doc",
                {"q": fulltext_query(term)},
            ).result_set
            assert len(rows) == 1, term
            assert rows[0][:2] == ["org:shared", "Nebular research"]
            assert json.loads(rows[0][2])["description"] == "Nebular research"
    finally:
        db.close()


def test_compatible_schema_alternatives_keep_reference_metadata(tmp_path: Path):
    roots = {}
    for name, suffix, prefixes in (
        ("alpha", "[a-z]+", "gh"),
        ("beta", "[a-z0-9-]+", "gh|acct"),
    ):
        root = write_kb(tmp_path / name, [("organization", {"id": f"org:{name}"})])
        (root / "_schemas/person.schema.yaml").write_text(
            yaml.safe_dump(
                {
                    "type": "object",
                    "properties": {
                        "event": {
                            "anyOf": [
                                {
                                    "type": "string",
                                    "pattern": f"^(event):{suffix}$",
                                    "title": "Conference",
                                    "description": f"From {name}",
                                },
                                {"type": "null"},
                            ]
                        },
                        "accounts": {
                            "type": "array",
                            "items": {"type": "string", "pattern": f"^({prefixes}):{suffix}$"},
                        },
                        "affiliations": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/Affiliation"},
                        },
                        "label": (
                            {"type": "string", "pattern": "^(event):[a-z]+$"}
                            if name == "alpha"
                            else {"type": "string"}
                        ),
                    },
                    "$defs": {
                        "Affiliation": {
                            "type": "object",
                            "properties": {
                                "organization": {
                                    "type": "string",
                                    "pattern": f"^(org):{suffix}$",
                                }
                            },
                        }
                    },
                }
            )
        )
        roots[name] = root
    schemas = compose_kbs(roots).kind_schemas
    assert schemas is not None
    person = schemas["person"]
    fields = {field["name"]: field for field in person.fields}
    assert fields["event"]["type"] == "string"
    assert fields["event"]["ref_kinds"] == ["event"]
    assert fields["event"]["title"] == "Conference"
    assert fields["event"]["description"] == "From alpha\n\nFrom beta"
    assert fields["accounts"]["list"] is True
    assert fields["accounts"]["ref_kinds"] == ["github_account", "social_account"]
    assert fields["affiliations"]["def"] == "Affiliation"
    assert "ref_kinds" not in fields["label"]
    affiliation = {field["name"]: field for field in person.defs["Affiliation"]}
    assert affiliation["organization"]["ref_kinds"] == ["organization"]
    # The display hints must not erase the original accepted validation alternatives.
    alternatives = person.schema["$defs"]["Affiliation"]["properties"]["organization"]["anyOf"]
    assert [item["pattern"] for item in alternatives] == ["^(org):[a-z]+$", "^(org):[a-z0-9-]+$"]


def test_lists_keep_source_order_and_single_source_duplicates(tmp_path: Path):
    first = write_kb(
        tmp_path / "alpha",
        [
            (
                "organization",
                {"id": "org:shared", "aliases": ["Zulu", "Alpha", "Zulu"], "ranks": [3, 1, 3]},
            ),
            ("organization", {"id": "org:only", "aliases": ["Zulu", "Alpha", "Zulu"]}),
        ],
    )
    one = compose_kbs({"alpha": first})
    single = one.payload_for(next(node for node in one.nodes if node.id == "org:shared"))
    assert single is not None
    assert single["aliases"] == ["Zulu", "Alpha", "Zulu"]
    assert single["ranks"] == [3, 1, 3]
    second = write_kb(
        tmp_path / "beta",
        [("organization", {"id": "org:shared", "aliases": ["Beta", "Alpha"], "ranks": [2, 1]})],
    )
    combined = compose_kbs({"beta": second, "alpha": first})
    shared = combined.payload_for(next(node for node in combined.nodes if node.id == "org:shared"))
    only = combined.payload_for(next(node for node in combined.nodes if node.id == "org:only"))
    assert shared is not None and only is not None
    assert shared["aliases"] == ["Zulu", "Alpha", "Beta"]
    assert shared["ranks"] == [3, 1, 2]
    assert only["aliases"] == ["Zulu", "Alpha", "Zulu"]


def test_internal_artifact_keys_do_not_replace_display_paths(tmp_path: Path):
    roots = {
        name: write_kb(
            tmp_path / name,
            [("organization", {"id": f"org:{name}", "name": name})],
        )
        for name in ("alpha", "beta")
    }
    kb = compose_kbs(roots)
    assert len(kb.artifacts) == 2
    for node in kb.nodes:
        payload = kb.payload_for(node)
        assert payload is not None and payload["id"] == node.id
        props = node_properties(node, payload)
        assert props["kb_path"] == "0.yaml"
        assert node.path in kb.artifacts


@pytest.mark.parametrize(
    ("target_kind", "target_id", "corroboration"),
    [
        ("organization", "org:shared", "verified"),
        ("organization", "gh:shared", "verified"),
        ("organization", "gh:shared", "github"),
        ("social_account", "acct:shared", "github"),
        ("github_account", "org:shared", "verified"),
        ("social_account", "gh:shared", "verified"),
        ("github_account", "acct:shared", "github"),
    ],
)
def test_person_merge_rejects_nonaccount_or_mistyped_corroboration(
    tmp_path: Path, target_kind: str, target_id: str, corroboration: str
):
    person = {"id": "person:shared", "name": "Shared Person"}
    if corroboration == "github":
        person.update(github=target_id, github_resolution="resolved")
    edge = {
        "source": "person:shared",
        "relation": "has_account",
        "target": target_id,
        "verified": corroboration == "verified",
    }
    roots = {
        name: write_kb(
            tmp_path / name,
            [("person", person), (target_kind, {"id": target_id})],
            [edge],
        )
        for name in ("alpha", "beta")
    }
    with pytest.raises(KbError, match="shared verified account is required"):
        compose_kbs(roots)


@pytest.mark.parametrize(
    ("target_kind", "target_id", "corroboration"),
    [
        ("github_account", "gh:shared", "github"),
        ("social_account", "acct:shared", "verified"),
    ],
)
def test_person_merge_accepts_actual_corroborating_account_nodes(
    tmp_path: Path, target_kind: str, target_id: str, corroboration: str
):
    person = {"id": "person:shared", "name": "Shared Person"}
    if corroboration == "github":
        person.update(github=target_id, github_resolution="resolved")
    roots = {
        name: write_kb(
            tmp_path / name,
            [("person", person), (target_kind, {"id": target_id})],
            [
                {
                    "source": "person:shared",
                    "relation": "has_account",
                    "target": target_id,
                    "verified": corroboration == "verified",
                }
            ],
        )
        for name in ("alpha", "beta")
    }
    assert len([node for node in compose_kbs(roots).nodes if node.kind == "person"]) == 1


@pytest.mark.parametrize("nullable_name", ["alpha", "beta"])
def test_one_sided_nullable_alternative_preserves_values_in_either_dataset_order(
    tmp_path: Path, nullable_name: str
):
    roots = {}
    event_ref = {"type": "string", "pattern": "^(event):[a-z]+$"}
    for name in ("alpha", "beta"):
        root = write_kb(tmp_path / name, [("organization", {"id": f"org:{name}"})])
        nullable = name == nullable_name
        (root / "_schemas/person.schema.yaml").write_text(
            yaml.safe_dump(
                {
                    "type": "object",
                    "properties": {
                        "role": (
                            {"anyOf": [{"enum": ["judge"]}, {"type": "null"}]}
                            if nullable
                            else {"enum": ["host"]}
                        ),
                        "event": (
                            {"anyOf": [event_ref, {"type": "null"}]} if nullable else event_ref
                        ),
                    },
                }
            )
        )
        roots[name] = root
    schemas = compose_kbs(roots).kind_schemas
    assert schemas is not None
    person = schemas["person"]
    role = Draft202012Validator(person.schema["properties"]["role"])
    assert all(role.is_valid(value) for value in ("host", "judge", None))
    assert not role.is_valid("unexpected")
    fields = {field["name"]: field for field in person.fields}
    assert fields["event"]["type"] == "string"
    assert fields["event"]["ref_kinds"] == ["event"]
    assert set(fields["role"]["enum"]) == {"host", "judge"}
