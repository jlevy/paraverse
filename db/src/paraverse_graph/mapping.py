"""
How softschema entities become FalkorDB nodes and relationships.

The mapping is generic so it keeps working as the KB contracts evolve:

- Every node gets its kind's label plus `Entity`, so one index serves lookups by
  typed ID across kinds. A few derived labels (`Account`, `Speaker`, `Sponsor`, ...)
  make common filters cheap and give a UI something to style by.
- Top-level scalars and lists of scalars become properties. Typed references are
  dropped from properties because the graph export already carries them as
  relationships, and two copies could disagree.
- Nested value objects (slots, affiliations, claims, sponsorship, sources) cannot
  be FalkorDB properties, so the full payload is kept as JSON in `doc` for display,
  and a few nested fields that queries filter on are promoted to flat properties.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from paraverse_graph.kb import KbEdge, KbNode

ENTITY_LABEL = "Entity"
META_LABEL = "GraphMeta"
SCHEMA_LABEL = "Schema"

LABELS: dict[str, str] = {
    "day": "Day",
    "event": "Event",
    "experience": "Experience",
    "facet": "Facet",
    "github_account": "GitHubAccount",
    "organization": "Organization",
    "package": "Package",
    "page": "Page",
    "person": "Person",
    "profile": "Profile",
    "repository": "Repository",
    "room": "Room",
    "session": "Session",
    "social_account": "SocialAccount",
    "software": "Software",
    "term": "Term",
    "venue": "Venue",
    "website": "Website",
}

# Derived labels, from fields that queries and UIs filter on most.
PARTICIPATION_LABELS = {
    "speaker": "Speaker",
    "attendee": "Attendee",
    "organizer": "Organizer",
    "sponsor_representative": "SponsorRep",
    "host": "Host",
    "judge": "Judge",
    "volunteer": "Volunteer",
}

TYPED_REF = re.compile(
    r"^(event|day|session|person|profile|org|room|venue|experience|facet|term|gh|acct|site|repo"
    r"|pkg|software):[a-z0-9][a-z0-9._/@+-]*$"
)
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

Scalar = str | int | float | bool
PropValue = Scalar | list[Scalar]


class MappingError(ValueError):
    """An entity or relation cannot be mapped safely."""


def labels_for(node: KbNode, payload: dict[str, Any] | None) -> tuple[str, ...]:
    """
    Labels for a node, primary label first. Labels are interpolated into Cypher (they
    cannot be query parameters), so every one comes from a fixed table or is checked.
    """
    primary = LABELS.get(node.kind)
    if primary is None:
        raise MappingError(f"no label for kind `{node.kind}` ({node.id})")
    labels = [primary]
    payload = payload or {}
    if node.kind in ("github_account", "social_account"):
        labels.append("Account")
    if node.kind == "person":
        roles = {p.get("role") for p in payload.get("participations", []) if isinstance(p, dict)}
        for role in sorted(r for r in roles if r):
            label = PARTICIPATION_LABELS.get(role)
            if label is None:
                raise MappingError(f"no label for participation role `{role}` ({node.id})")
            labels.append(label)
    if node.kind == "organization" and "sponsor" in payload.get("roles", []):
        labels.append("Sponsor")
    labels.append(ENTITY_LABEL)
    return tuple(_checked_identifier(label) for label in labels)


def relationship_type(relation: str) -> str:
    """`presents` becomes `PRESENTS`, following Cypher convention."""
    return _checked_identifier(relation.upper())


def node_properties(
    node: KbNode, payload: dict[str, Any] | None, *, display_name: str | None = None
) -> dict[str, PropValue]:
    """
    Flat properties for one node. `entity_kind`, `display_name` and `kb_path` come
    from the graph export, so they never collide with payload fields such as a
    venue's own `kind`. `display_name` overrides the export's name (see
    `readable_name`).
    """
    payload = payload or {}
    kb_path = node.path
    composition = payload.get("_composition")
    if isinstance(composition, dict):
        sources = composition.get("sources")
        if (
            isinstance(sources, list)
            and sources
            and isinstance(sources[0], dict)
            and isinstance(sources[0].get("path"), str)
        ):
            kb_path = sources[0]["path"]
    props: dict[str, PropValue] = {
        "id": node.id,
        "entity_kind": node.kind,
        "display_name": display_name or node.name,
        "kb_path": kb_path,
    }
    for key, value in payload.items():
        if key in ("id", "sources") or key in props:
            continue
        prop = _property_value(value)
        if prop is not None:
            props[key] = prop

    systems = sorted(
        {s["system"] for s in payload.get("sources", []) if isinstance(s, dict) and "system" in s}
    )
    if systems:
        props["source_systems"] = list(systems)

    promote = _PROMOTERS.get(node.kind)
    if promote:
        props.update({k: v for k, v in promote(payload).items() if v is not None})

    props["search_text"] = _search_text(str(props["display_name"]), payload)
    props["doc"] = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return props


def edge_properties(edge: KbEdge) -> dict[str, PropValue]:
    """
    Edge attributes from the export. Times also get an epoch copy so range filters
    do not depend on every timestamp sharing one UTC offset.
    """
    props: dict[str, PropValue] = {}
    for key, value in edge.attrs.items():
        prop = _property_value(value, keep_refs=True)
        if prop is not None:
            props[key] = prop
        elif value is not None:
            props[f"{key}_json"] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    start = edge.attrs.get("start")
    if isinstance(start, str):
        epoch = _epoch(start)
        if epoch is not None:
            props["start_epoch"] = epoch
    return props


def _property_value(value: Any, *, keep_refs: bool = False) -> PropValue | None:
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        if not keep_refs and TYPED_REF.match(value):
            return None
        return value
    if isinstance(value, list) and value:
        if not all(isinstance(item, str | int | float | bool) for item in value):
            return None
        if not keep_refs and any(isinstance(item, str) and TYPED_REF.match(item) for item in value):
            return None
        return list(value)
    return None


def _epoch(timestamp: str) -> int | None:
    """
    Seconds since the epoch. A value with no UTC offset, such as a bare date, is read
    as UTC, so the result does not depend on the loading machine's time zone.
    """
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp())


def _by_epoch(timestamp: str) -> tuple[bool, int, str]:
    """
    Sort key for times in instant order. Strings sort wrongly when slots have
    different UTC offsets; unparsable values sort last.
    """
    epoch = _epoch(timestamp)
    return (epoch is None, epoch or 0, timestamp)


def _session_fields(payload: dict[str, Any]) -> dict[str, PropValue | None]:
    slots = [s for s in payload.get("slots", []) if isinstance(s, dict)]
    starts = sorted((s["start"] for s in slots if s.get("start")), key=_by_epoch)
    ends = sorted((s["end"] for s in slots if s.get("end")), key=_by_epoch)
    capacities = [s["capacity"] for s in slots if isinstance(s.get("capacity"), int)]
    return {
        "start": starts[0] if starts else None,
        "end": ends[-1] if ends else None,
        "start_epoch": _epoch(starts[0]) if starts else None,
        "end_epoch": _epoch(ends[-1]) if ends else None,
        "slot_count": len(slots),
        "in_person": any(s.get("in_person") for s in slots),
        "virtual": any(s.get("virtual") for s in slots),
        "capacity": max(capacities) if capacities else None,
    }


def _event_fields(payload: dict[str, Any]) -> dict[str, PropValue | None]:
    start, end = payload.get("start"), payload.get("end")
    return {
        "start_epoch": _epoch(start) if isinstance(start, str) else None,
        "end_epoch": _epoch(end) if isinstance(end, str) else None,
    }


def _organization_fields(payload: dict[str, Any]) -> dict[str, PropValue | None]:
    sponsorship = payload.get("sponsorship") or {}
    return {
        "sponsor_tier": sponsorship.get("tier"),
        "sponsor_booth": sponsorship.get("booth"),
        "sponsor_summary": sponsorship.get("summary"),
        "sponsor_industries": sponsorship.get("industries") or None,
    }


def _person_fields(payload: dict[str, Any]) -> dict[str, PropValue | None]:
    participations = [p for p in payload.get("participations", []) if isinstance(p, dict)]
    current = [
        a for a in payload.get("affiliations", []) if isinstance(a, dict) and a.get("current")
    ]
    titles = sorted({a["title"] for a in current if a.get("title")})
    return {
        "participation_roles": sorted({p["role"] for p in participations if p.get("role")}) or None,
        "participation_statuses": sorted({p["status"] for p in participations if p.get("status")})
        or None,
        "current_titles": titles or None,
    }


def _profile_fields(payload: dict[str, Any]) -> dict[str, PropValue | None]:
    def labels(key: str) -> list[Scalar] | None:
        found = [c["label"] for c in payload.get(key, []) if isinstance(c, dict) and c.get("label")]
        return list(found) or None

    return {
        "expertise_labels": labels("expertise"),
        "technology_labels": labels("technologies"),
        "language_labels": labels("programming_languages"),
        "interest_labels": labels("interests"),
        "recognition_labels": labels("recognitions"),
    }


_PROMOTERS: dict[str, Callable[[dict[str, Any]], dict[str, PropValue | None]]] = {
    "event": _event_fields,
    "organization": _organization_fields,
    "person": _person_fields,
    "profile": _profile_fields,
    "session": _session_fields,
}

_SEARCH_FIELDS = (
    "title",
    "name",
    "full_name",
    "login",
    "handle",
    "label",
    "job_title",
    "affiliation_label",
    "headline",
    "description",
    "abstract",
    "bio",
)


def readable_name(node: KbNode, payload: dict[str, Any] | None, names: dict[str, str]) -> str:
    """
    The export names some records by their ID (a profile is `profile:april-leonard`).
    Name those after the first entity they reference that has a real name, such as
    the profile's person.
    """
    if node.name != node.id:
        return node.name
    for value in (payload or {}).values():
        if isinstance(value, str) and TYPED_REF.match(value):
            name = names.get(value)
            if name and name != value:
                return name
    return node.name


def _search_text(name: str, payload: dict[str, Any]) -> str:
    """
    One text field per node for a single full-text index across every kind, so
    global search is one call rather than one per label.
    """
    parts = [name]
    values = [payload.get(key) for key in (*_SEARCH_FIELDS, "aliases")]
    composition = payload.get("_composition")
    if isinstance(composition, dict):
        for conflict in composition.get("conflicts", []):
            if isinstance(conflict, dict) and conflict.get("field") in (*_SEARCH_FIELDS, "aliases"):
                values.extend(
                    variant.get("value")
                    for variant in conflict.get("values", [])
                    if isinstance(variant, dict)
                )
    for value in values:
        for text in value if isinstance(value, list) else [value]:
            if isinstance(text, str) and text not in parts:
                parts.append(text)
    # FalkorDB's tokenizer drops newlines between words instead of separating them.
    return " ".join(parts)


def _checked_identifier(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise MappingError(f"unsafe Cypher identifier: {name!r}")
    return name


## Tests


def test_readable_name_uses_the_referenced_entity():
    profile = KbNode(id="profile:a", kind="profile", name="profile:a", path="profiles/a.yaml")
    names = {"person:a": "Ann A", "profile:a": "profile:a"}
    assert readable_name(profile, {"person": "person:a"}, names) == "Ann A"
    named = KbNode(id="person:a", kind="person", name="Ann A", path="people/a.md")
    assert readable_name(named, {}, names) == "Ann A"


def test_refs_become_edges_not_properties():
    node = KbNode(id="session:a1", kind="session", name="A talk", path="sessions/a1.md")
    payload = {
        "id": "session:a1",
        "event": "event:x-2026",
        "title": "A talk",
        "related": ["session:b2"],
        "slots": [
            {
                "start": "2026-10-28T09:00:00-07:00",
                "end": "2026-10-28T09:30:00-07:00",
                "capacity": 40,
            }
        ],
        "sponsored": False,
        "sources": [{"system": "rainfocus"}],
    }
    props = node_properties(node, payload)
    assert "event" not in props and "related" not in props and "slots" not in props
    assert props["title"] == "A talk"
    assert props["start_epoch"] == 1793203200  # 2026-10-28T16:00:00Z
    assert props["capacity"] == 40
    assert props["source_systems"] == ["rainfocus"]
    assert json.loads(str(props["doc"]))["event"] == "event:x-2026"


def test_derived_labels():
    person = KbNode(id="person:a", kind="person", name="A", path="people/a.md")
    payload = {"participations": [{"role": "speaker"}, {"role": "attendee"}]}
    assert labels_for(person, payload) == ("Person", "Attendee", "Speaker", "Entity")
    org = KbNode(id="org:a", kind="organization", name="A", path="organizations/a.md")
    assert labels_for(org, {"roles": ["sponsor"]}) == ("Organization", "Sponsor", "Entity")
    try:
        labels_for(person, {"participations": [{"role": "juggler"}]})
    except MappingError as e:
        assert "juggler" in str(e)
    else:
        raise AssertionError("an unknown participation role should raise MappingError")


def test_epoch_ignores_the_machine_time_zone():
    import os
    import time

    saved = os.environ.get("TZ")
    try:
        for tz in ("America/Los_Angeles", "Asia/Tokyo"):
            os.environ["TZ"] = tz
            time.tzset()
            assert _epoch("2026-10-28") == 1793145600  # 2026-10-28T00:00:00Z
            assert _epoch("2026-10-28T09:00:00-07:00") == 1793203200
    finally:
        if saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = saved
        time.tzset()
    assert _epoch("not a date") is None


def test_session_slots_are_ordered_by_instant_not_string():
    # 09:00 at UTC-7 is 16:00Z, later than 10:00Z, though its string sorts first.
    later = {"start": "2026-10-28T09:00:00-07:00", "end": "2026-10-28T09:30:00-07:00"}
    earlier = {"start": "2026-10-28T10:00:00+00:00", "end": "2026-10-28T10:30:00+00:00"}
    fields = _session_fields({"slots": [later, earlier]})
    assert fields["start"] == earlier["start"]
    assert fields["end"] == later["end"]
    assert fields["start_epoch"] == _epoch(earlier["start"])
    assert fields["end_epoch"] == _epoch(later["end"])


def test_edge_attrs_keep_refs_and_encode_nested():
    edge = KbEdge(
        source="person:a",
        relation="affiliated_with",
        target="org:b",
        attrs={"basis": "event_listing", "current": True, "evidence": [{"url": "https://x"}]},
    )
    props = edge_properties(edge)
    assert props["basis"] == "event_listing" and props["current"] is True
    assert json.loads(str(props["evidence_json"])) == [{"url": "https://x"}]
