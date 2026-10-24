"""
Aggregate the loaded graph for the browser's welcome page. Counts describe stored
entities and direct source citations; they do not certify collection or data quality.
Only aggregate evidence leaves this module, apart from public event edition details.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from paraverse_graph.mapping import ENTITY_LABEL, LABELS

_PROVIDER = re.compile(r"[a-z][a-z0-9_.-]{0,79}")
Record = tuple[str, str, dict[str, Any] | None]


def build_overview(
    reader: Any,
    meta: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    kind_groups: tuple[tuple[str, tuple[str, ...]], ...],
) -> dict[str, Any]:
    """
    Read each payload once and combine it with the loader's checked statistics.
    The caller validates that the load did not change across these reads.
    """
    counts = meta["stats"].get("nodes", {})
    groups = {kind: title for title, kinds in kind_groups for kind in kinds}
    group_order = {title: index for index, (title, _) in enumerate(kind_groups)}
    entities = [
        {
            "kind": kind,
            "title": schemas.get(kind, {}).get("title") or kind.replace("_", " ").title(),
            "group": groups.get(kind, "Other"),
            "count": count,
        }
        for kind, count in counts.items()
        if count
    ]
    entities.sort(key=lambda row: (group_order.get(row["group"], len(groups)), row["kind"]))
    relationships: dict[str, dict[str, Any]] = {
        relation.upper(): {"type": relation.upper(), "count": count, "from": [], "to": []}
        for relation, count in meta["stats"].get("edges", {}).items()
        if count
    }
    for stat in meta["rel_stats"]:
        row = relationships.get(stat["type"])
        if row is not None:
            row["from"] = sorted({*row["from"], stat["from"]})
            row["to"] = sorted({*row["to"], stat["to"]})

    records: list[Record] = []
    by_kind: dict[str, list[Record]] = defaultdict(list)
    for id_, kind, name, doc in reader.ro_query(
        f"MATCH (n:{ENTITY_LABEL}) RETURN n.id, n.entity_kind, n.display_name, n.doc"
    ).result_set:
        try:
            payload = json.loads(doc) if isinstance(doc, str) else None
        except (ValueError, TypeError):
            payload = None
        record = (id_, name, payload if isinstance(payload, dict) else None)
        records.append(record)
        by_kind[kind].append(record)

    source_summary, source_coverage = _sources(records)
    coverage = [source_coverage]
    profiles = by_kind.get("profile", [])
    if profiles:
        bios = [payload.get("brief_bio") for _, _, payload in profiles if payload is not None]
        present = [bio for bio in bios if isinstance(bio, dict) and _text(bio.get("text"))]
        coverage.append(
            {
                "key": "profile_brief_bio",
                "title": "Profile brief bios",
                "kind": "profile",
                "total": len(profiles),
                "present": len(present),
                "missing": len(profiles) - len(present),
                "stale": sum(bio.get("stale") is True for bio in present),
                "unknown": sum(not isinstance(bio.get("stale"), bool) for bio in present),
                "note": "Present means nonempty bio text. Stale and unknown freshness are "
                "subsets of present; a missing stale flag does not establish freshness.",
            }
        )
        for field, title in (
            ("expertise", "Profile expertise"),
            ("interests", "Profile interests"),
        ):
            count = 0
            for _, _, payload in profiles:
                claims = payload.get(field) if payload else None
                count += isinstance(claims, list) and any(
                    isinstance(claim, dict) and bool(_text(claim.get("label"))) for claim in claims
                )
            coverage.append(
                {
                    "key": f"profile_{field}",
                    "title": title,
                    "kind": "profile",
                    "total": len(profiles),
                    "present": count,
                    "missing": len(profiles) - count,
                    "note": "At least one labeled claim is present; this does not verify its accuracy.",
                }
            )
    accounts = by_kind.get("social_account", [])
    if accounts:
        fetched = sum(
            payload is not None and payload.get("details_fetched") is True
            for _, _, payload in accounts
        )
        not_fetched = sum(
            payload is not None and payload.get("details_fetched") is False
            for _, _, payload in accounts
        )
        coverage.append(
            {
                "key": "social_details",
                "title": "Social account details fetched",
                "kind": "social_account",
                "total": len(accounts),
                "present": fetched,
                "missing": len(accounts) - fetched,
                "not_fetched": not_fetched,
                "unknown": len(accounts) - fetched - not_fetched,
                "note": "Present requires details_fetched=true. Missing is the sum of "
                "explicit false and unknown (absent or nonboolean flags).",
            }
        )
    sessions = by_kind.get("session", [])
    if sessions:
        scheduled = sum(_scheduled(payload) for _, _, payload in sessions)
        coverage.append(
            {
                "key": "session_schedule",
                "title": "Sessions with scheduled times",
                "kind": "session",
                "total": len(sessions),
                "present": scheduled,
                "missing": len(sessions) - scheduled,
                "note": "At least one slot has valid start and end timestamps, with end after "
                "start. This does not verify room assignments or every repeated slot.",
            }
        )
    edition_counts = dict(
        reader.ro_query(
            f"MATCH (s:{LABELS['session']})-[:PART_OF]->(e:{LABELS['event']}) "
            "RETURN e.id, count(DISTINCT s)"
        ).result_set
    )
    editions = [
        {
            "id": id_,
            "name": _text(payload.get("name")) or name,
            "edition": _text(payload.get("edition")),
            "start": _event_timestamp(payload.get("start")),
            "end": _event_timestamp(payload.get("end")),
            "sessions": edition_counts.get(id_, 0),
        }
        for id_, name, original in by_kind.get("event", [])
        for payload in [original or {}]
    ]
    editions.sort(key=lambda row: (row["start"] or row["edition"] or "", row["id"]), reverse=True)
    participation: Counter[str] = Counter()
    for _, _, payload in by_kind.get("person", []):
        basis = _text(payload.get("inclusion_basis")) if payload else None
        participation[basis if basis and _PROVIDER.fullmatch(basis) else "unknown"] += 1
    return {
        "load": {
            key: meta[key] for key in ("dataset", "graph", "kb_digest", "loaded_at", "load_id")
        },
        "totals": {
            "entities": sum(counts.values()),
            "relationships": sum(row["count"] for row in relationships.values()),
            "entity_kinds": len(entities),
            "relationship_types": len(relationships),
        },
        "entities": entities,
        "relationships": [relationships[key] for key in sorted(relationships)],
        "editions": editions,
        "sources": source_summary,
        "coverage": coverage,
        "participation": [
            {"basis": basis, "count": count} for basis, count in sorted(participation.items())
        ],
    }


def _sources(records: list[Record]) -> tuple[dict[str, Any], dict[str, Any]]:
    provider_entities: dict[str, set[str]] = defaultdict(set)
    references: Counter[str] = Counter()
    latest: dict[str, datetime] = {}
    urls: set[str] = set()
    with_sources = unknown = 0
    for id_, _, payload in records:
        sources = payload.get("sources") if payload is not None else None
        if sources is None:
            unknown += payload is None
            continue
        if not isinstance(sources, list):
            unknown += 1
            continue
        has_source = has_unknown = False
        for citation in sources:
            system = _text(citation.get("system")) if isinstance(citation, dict) else None
            if not system or not _PROVIDER.fullmatch(system):
                has_unknown = True
                continue
            has_source = True
            provider_entities[system].add(id_)
            references[system] += 1
            retrieved = _instant(citation.get("retrieved_at"))
            if retrieved is not None and (system not in latest or retrieved > latest[system]):
                latest[system] = retrieved
            url = _text(citation.get("url"))
            if url:
                try:
                    parsed = urlsplit(url)
                    if parsed.scheme in ("http", "https") and parsed.hostname:
                        urls.add(url)
                except ValueError:
                    pass
        with_sources += has_source
        unknown += has_unknown
    return (
        {
            "entities_with_sources": with_sources,
            "entities_without_sources": len(records) - with_sources,
            "source_references": sum(references.values()),
            "unique_urls": len(urls),
            "providers": [
                {
                    "source": system,
                    "entities": len(provider_entities[system]),
                    "references": count,
                    "latest_retrieved_at": _timestamp(latest.get(system)),
                }
                for system, count in sorted(references.items())
            ],
            "latest_retrieved_at": _timestamp(max(latest.values(), default=None)),
        },
        {
            "key": "source_citations",
            "title": "Entities with direct source citations",
            "kind": "all",
            "total": len(records),
            "present": with_sources,
            "missing": len(records) - with_sources,
            "unknown": unknown,
            "note": "Counts direct top-level sources with a usable system identifier, not "
            "collected records. Derived entities may inherit provenance through a parent. "
            "Unknown marks malformed metadata and can overlap present for partly usable lists.",
        },
    )


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(UTC) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def _event_timestamp(value: Any) -> str | None:
    # Edition dates belong to the event's calendar. UTC conversion can change the
    # date at midnight, unlike retrieval times where comparing instants is intended.
    timestamp = _text(value)
    return timestamp if _instant(timestamp) is not None else None


def _scheduled(payload: dict[str, Any] | None) -> bool:
    slots = payload.get("slots") if payload else None
    if not isinstance(slots, list):
        return False
    for slot in slots:
        if isinstance(slot, dict):
            start, end = _instant(slot.get("start")), _instant(slot.get("end"))
            if start is not None and end is not None and end > start:
                return True
    return False
