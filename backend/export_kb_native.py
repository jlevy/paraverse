"""
Export the pinned conference KBs into the native client's offline JSON assets.

Run from db/: UV_CONFIG_FILE=uv.toml uv run python ../backend/export_kb_native.py
The graph selects records; softschema YAML supplies every consumed value. Native
assets supply only existing sprite IDs and local image names. Markdown bodies,
raw responses, source caches, and generated uncited biographies are never used.
Every output file is replaced atomically; the manifest is published last. This
is a reproducible build step, not an atomic transaction across the asset folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from paraverse_graph.kb import KnowledgeBase, load_kb
from paraverse_graph.validation import validate_artifacts

ROOT = Path(__file__).resolve().parents[1]
DATASETS = (
    ("universe2026-md", "event:github-universe-2026", "world-speakers.json"),
    ("ptc2026-md", "event:patch-the-conference-2026", "ptc-judges.json"),
)
JSON = dict[str, Any]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Expected a structured text value")
    return value


def _url(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    parsed = urlsplit(text)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Expected a public HTTP(S) source URL")
    return text


def _identity_url(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").removeprefix("www.").casefold()
    host = "x.com" if host == "twitter.com" else host
    return host + parsed.path.rstrip("/").casefold()


def match_legacy(person: JSON, links: JSON, legacy: list[JSON]) -> JSON | None:
    """Reuse a sprite identity only when name/account evidence names one record."""
    name = " ".join(_text(person.get("name")).split()).casefold()
    accounts = {_identity_url(v) for v in links.values() if v}
    candidates = {}
    for old in legacy:
        old_name = " ".join(_text(old.get("name")).split()).casefold()
        old_accounts = {
            _identity_url(old[k]) for k in ("githubURL", "linkedinURL", "xURL") if old.get(k)
        }
        if (name and name == old_name) or accounts & old_accounts:
            candidates[old["id"]] = old
    if len(candidates) > 1:
        raise ValueError(f"{person['id']}: ambiguous legacy sprite identity")
    return next(iter(candidates.values()), None)


def _links(person: JSON, records: dict[str, JSON]) -> JSON:
    result: JSON = {"githubURL": None, "linkedinURL": None, "xURL": None}
    for ref in sorted(
        set(person.get("accounts", []) + ([person["github"]] if person.get("github") else []))
    ):
        account = records.get(ref)
        if account is None:
            raise ValueError(f"{person['id']}: missing account {ref}")
        owner = account.get("owner", account.get("entity"))
        if owner and owner != person["id"]:
            raise ValueError(f"{person['id']}: account {ref} belongs to another person")
        platform = "github" if ref.startswith("gh:") else _text(account.get("platform"))
        key = {"github": "githubURL", "linkedin": "linkedinURL", "x": "xURL"}.get(platform)
        if key:
            url = _url(account.get("url"))
            # Native has one button per platform; keep every URL separately below.
            result[key] = result[key] or url or None
    return result


def _biography(person: JSON, records: dict[str, JSON]) -> tuple[str, JSON | None]:
    if person.get("bio"):
        return _text(person["bio"]), {
            "basis": "event_bio",
            "cites": sorted({_url(s["url"]) for s in person.get("sources", []) if s.get("url")}),
        }
    profile = records.get(_text(person.get("profile")), {})
    bio = profile.get("brief_bio", {})
    if not bio or bio.get("stale"):
        return "", None
    cites = bio.get("cites", [])
    # Generated text must carry actual public citations, its author and input hash.
    if not cites or not all(
        isinstance(c, str) and c.startswith(("https://", "http://")) for c in cites
    ):
        return "", None
    if not bio.get("written_by") or not re.fullmatch(
        r"[a-fA-F0-9]{64}", _text(bio.get("input_sha256"))
    ):
        return "", None
    return _text(bio.get("text")), {
        key: bio[key]
        for key in ("basis", "cites", "written_by", "written_at", "input_sha256")
        if key in bio
    }


def _attendance_proof(person: JSON, participation: list[JSON], records: dict[str, JSON], event: JSON) -> tuple[JSON | None, list[JSON]]:
    """Fail closed unless an owned public post explicitly says the person will attend."""
    accounts = [records[ref] for ref in person.get("accounts", []) if records[ref].get("owner", records[ref].get("entity")) == person["id"] and records[ref].get("url")]
    event_name = re.sub(r"[^a-z]", "", re.sub(r"\b\d{4}\b", "", _text(event.get("name"))).casefold())
    for account in accounts:
        profile = urlsplit(_url(account["url"]))
        prefix = profile.path.rstrip("/").casefold() + "/"
        evidence = []
        for item in participation:
            if item.get("role") != "attendee" or item.get("status") != "self_reported":
                continue
            for source in item.get("evidence", []):
                post = urlsplit(_url(source.get("url")))
                quote = _text(source.get("quote"))
                # A cited third-party post, event mention, negation or uncertain plan
                # cannot establish this person's stated attendance.
                own_post = profile.scheme == post.scheme == "https" and profile.netloc.casefold() == post.netloc.casefold() and post.path.casefold().startswith(prefix)
                explicit = re.search(r"\bi(?:['’](?:ll|m)|\s+(?:am|will))\b[^.!?\n]{0,60}\b(?:attend(?:ing)?|be\s+at|at|join(?:ing)?)\b", quote, re.I)
                uncertain = re.search(r"\b(?:not|never|might|maybe|hope|wish|won['’]t|can['’]t|cannot)\b", quote, re.I)
                names_event = bool(event_name) and event_name in re.sub(r"[^a-z]", "", quote.casefold())
                if own_post and explicit and not uncertain and names_event:
                    evidence.append(source)
        if evidence:
            return account, evidence
    return None, []


def build_dataset(kb: KnowledgeBase, event_id: str, legacy: list[JSON]) -> JSON:
    """Project one event into native people and timed session records, deterministically."""
    records = {node.id: kb.payload_for(node) for node in kb.nodes}
    event = records.get(event_id)
    if event is None:
        raise ValueError(f"Missing event {event_id}")
    by_person: dict[str, list[JSON]] = defaultdict(list)
    sessions, descriptions = [], {}
    gaps: JSON = {"missingBiographies": [], "unscheduledSessions": [], "missingLegacyIdentity": []}
    for node in sorted(kb.nodes, key=lambda n: n.id):
        session = records[node.id]
        if node.kind != "session" or session.get("event") != event_id:
            continue
        url = _url(session.get("url"))
        base_id = urlsplit(url).path.rstrip("/").split("/")[-1] if url else node.id
        slots = sorted(session.get("slots", []), key=lambda s: _text(s.get("start")))
        if not slots:
            gaps["unscheduledSessions"].append(node.id)
        for slot in slots:
            start, end = _text(slot.get("start")), _text(slot.get("end"))
            begin, finish = datetime.fromisoformat(start), datetime.fromisoformat(end)
            if begin.tzinfo is None or finish.tzinfo is None or finish <= begin:
                raise ValueError(f"{node.id}: session slot needs ordered timezone-aware timestamps")
            sid = base_id if len(slots) == 1 else f"{base_id}@{start}"
            room = records.get(slot.get("room"), {})
            names = [_text(records[s["person"]].get("name")) for s in session.get("speakers", [])]
            row = dict(
                id=sid,
                kbID=node.id,
                title=_text(session.get("title")),
                description=_text(session.get("abstract")),
                speakers=", ".join(names),
                start=start,
                end=end,
                location=_text(room.get("label") or room.get("name")),
                sourceURL=url,
                reason="Official conference session",
            )
            if sid in descriptions:
                raise ValueError(f"Duplicate native session ID {sid}")
            descriptions[sid] = row["description"]
            sessions.append(row)
            native = dict(
                id=sid,
                title=row["title"],
                date=begin.date().isoformat(),
                start=f"{begin.hour % 12 or 12}:{begin.minute:02d} {'AM' if begin.hour < 12 else 'PM'}",
                startISO=start,
                room=row["location"],
                url=url,
            )
            for speaker in session.get("speakers", []):
                by_person[speaker["person"]].append(native)
    people, attendees, used_ids = [], [], set()
    for node in sorted(kb.nodes, key=lambda n: n.id):
        if node.kind != "person":
            continue
        person = records[node.id]
        participation = [
            p
            for p in person.get("participations", [])
            if p.get("event") == event_id and p.get("status") in {"confirmed", "self_reported"}
        ]
        account, attendance_evidence = _attendance_proof(person, participation, records, event)
        if not attendance_evidence:
            participation = [p for p in participation if p.get("role") != "attendee"]
        if not participation:
            continue
        roles = sorted({_text(p.get("role")) for p in participation})
        links = _links(person, records)
        old = match_legacy(person, links, legacy)
        native_id = old["id"] if old else node.id
        if native_id in used_ids:
            raise ValueError(f"{node.id}: duplicate native person ID {native_id}")
        used_ids.add(native_id)
        biography, provenance = _biography(person, records)
        if not biography:
            gaps["missingBiographies"].append(node.id)
        if native_id == node.id:
            gaps["missingLegacyIdentity"].append(node.id)
        evidence = attendance_evidence + [e for p in participation if p.get("role") != "attendee" for e in p.get("evidence", []) if e.get("url")]
        source = (
            next((e["url"] for e in evidence), None)
            or next((s["url"] for s in person.get("sources", []) if s.get("url")), None)
            or event.get("url")
        )
        affiliations = [a for a in person.get("affiliations", []) if a.get("current")]
        company = _text(person.get("affiliation_label")) or ", ".join(
            dict.fromkeys(
                _text(a.get("label") or records.get(a.get("organization"), {}).get("name"))
                for a in affiliations
            )
        )
        row = dict(
            id=native_id,
            kbID=node.id,
            name=_text(person.get("name")),
            role=_text(person.get("job_title")) or " / ".join(r.capitalize() for r in roles),
            company=company,
            biography=biography,
            sourceURL=_url(source),
            photo=old.get("photo") if old else None,
            sessions=sorted(by_person[node.id], key=lambda s: (s["startISO"], s["id"])),
            attendee="attendee" in roles and "speaker" not in roles,
            participationRoles=roles,
            eventID=event_id,
            biographyProvenance=provenance,
            accountURLs=sorted(
                {
                    _url(records[ref].get("url"))
                    for ref in person.get("accounts", [])
                    if records[ref].get("url")
                }
            ),
            **links,
        )
        if old and old.get("avatarAsset"):
            row["avatarAsset"] = old["avatarAsset"]
        if old and old.get("avatarNote"):
            row["avatarNote"] = old["avatarNote"]
        people.append(row)
        if attendance_evidence:
            assert account is not None
            attendees.append(
                dict(
                    id=native_id,
                    kbID=node.id,
                    name=row["name"],
                    username=_text(account.get("handle") or account.get("login")),
                    platform=_text(account.get("platform") or "github"),
                    event=_text(event.get("name")),
                    attendance_mode="unspecified",
                    attendance_status="Public self-report",
                    matching_opt_in=False,
                    evidence="\n\n".join(_text(e["quote"]) for e in attendance_evidence),
                    source_url=_url(attendance_evidence[0]["url"]),
                    evidence_sources=attendance_evidence,
                    profile_url=_url(account["url"]),
                    post_date=_text(attendance_evidence[0].get("observed_at")),
                    role=row["role"],
                    avatar_asset=row.get("avatarAsset"),
                )
            )
    if not people:
        raise ValueError(f"{event_id}: no confirmed or self-reported participants")
    people.sort(key=lambda p: (p["name"].casefold(), p["kbID"]))
    sessions.sort(key=lambda s: (s["start"], s["id"]))
    kb.check_unchanged()
    return dict(
        people=people, attendees=attendees, sessions=sessions, descriptions=descriptions, gaps=gaps
    )


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _verified_pin(vendor: Path, dataset: str) -> str:
    repo = vendor / dataset
    commit = _git(repo, "rev-parse", "HEAD")
    path = f"{vendor.name}/{dataset}"
    entry = _git(vendor.parent, "ls-tree", "HEAD", "--", path).split()
    if len(entry) != 4 or entry[:2] != ["160000", "commit"] or entry[2] != commit:
        raise ValueError(f"{dataset}: checkout does not match the parent repository's pinned gitlink")
    if _git(repo, "status", "--porcelain", "--", "kb"):
        raise ValueError(f"{dataset}: KB has uncommitted changes; commit provenance would be misleading")
    return commit


def _legacy(assets: Path, filename: str) -> list[JSON]:
    path = assets / filename
    return json.loads(path.read_text()) if path.is_file() else []


def export_native(
    vendor: Path, assets: Path, *, validate: bool = True, reuse_validation: bool = False
) -> JSON:
    """Validate pinned builds before replacing assets; publish provenance last."""
    outputs: JSON = {}
    prior_path = assets / "kb-native-manifest.json"
    prior = json.loads(prior_path.read_text()) if reuse_validation and prior_path.is_file() else {}
    manifest: JSON = {
        "schemaVersion": 1,
        "generator": "backend/export_kb_native.py",
        "datasets": [],
        "limitations": [
            "Offline snapshot; regenerate after changing a dataset pin.",
            "Only confirmed or self-reported participation in the selected event is included.",
            "Missing structured biographies stay empty; Markdown bodies are never consumed.",
            "External side-event assets are maintained separately and are not refreshed here.",
            "Native social buttons use the first account ID in sorted order per platform; accountURLs retains all linked accounts.",
        ],
    }
    for dataset, event_id, filename in DATASETS:
        repo = vendor / dataset
        commit = _verified_pin(vendor, dataset)
        kb = load_kb(repo / "kb")
        validated_before = any(
            d.get("dataset") == dataset
            and d.get("commit") == commit
            and d.get("graphDigest") == kb.digest
            and d.get("softschemaValidated") is True
            for d in prior.get("datasets", [])
        )
        if validate and not validated_before:
            report = validate_artifacts(kb.root)
            if not report.ok:
                detail = "; ".join(p.line() for p in report.problems[:5])
                raise ValueError(
                    f"{dataset}: softschema validation failed ({report.checked} artifacts): {detail}"
                )
        legacy = _legacy(assets, filename)
        if dataset == "universe2026-md":
            legacy += [
                dict(
                    id="attendee:" + p["id"],
                    name=p["name"],
                    xURL=p.get("profile_url"),
                    linkedinURL=p.get("linkedin_url"),
                    githubURL=p.get("github_url"),
                    avatarAsset=p.get("avatar_asset"),
                )
                for p in _legacy(assets, "universe-attendees.json")
            ]
        result = build_dataset(kb, event_id, legacy)
        outputs[filename] = result["people"]
        if dataset == "universe2026-md":
            outputs["kb-sessions.json"] = result["sessions"]
            outputs["kb-attendees.json"] = result["attendees"]
            outputs["session-descriptions.json"] = result["descriptions"]
            browse_path = assets / "browse-events.json"
            browse = json.loads(browse_path.read_text()) if browse_path.is_file() else {}
            outputs["browse-events.json"] = {
                "sessions": result["sessions"],
                "external": browse.get("external", []),
            }
        manifest["datasets"].append(
            dict(
                dataset=dataset,
                repository=f"https://github.com/jlevy/{dataset}",
                commit=commit,
                graphDigest=kb.digest,
                eventID=event_id,
                people=len(result["people"]),
                sessionSlots=len(result["sessions"]),
                gaps=result["gaps"],
                contracts=sorted({a.contract for a in kb.artifacts.values()}),
                softschemaValidated=validate,
            )
        )
        kb.check_unchanged()
        if _verified_pin(vendor, dataset) != commit:
            raise ValueError(f"{dataset}: source changed during export")
    outputs["kb-native-manifest.json"] = manifest
    assets.mkdir(parents=True, exist_ok=True)
    # Render everything first so invalid values cannot leave a partially rendered set.
    rendered = {
        name: json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        for name, value in outputs.items()
    }
    for name, content in rendered.items():
        staged: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=assets, prefix=".kb-native-", delete=False
            ) as stream:
                staged = Path(stream.name)
                stream.write(content)
            staged.chmod(0o644)
            os.replace(staged, assets / name)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor", type=Path, default=ROOT / "vendor")
    parser.add_argument("--assets", type=Path, default=ROOT / "native/Assets")
    parser.add_argument(
        "--reuse-validation",
        action="store_true",
        help="Reuse successful validation recorded for the same clean dataset commit and graph digest; validate changed sources.",
    )
    args = parser.parse_args()
    manifest = export_native(args.vendor, args.assets, reuse_validation=args.reuse_validation)
    for dataset in manifest["datasets"]:
        print(
            f"{dataset['dataset']}@{dataset['commit']}: {dataset['people']} people, {dataset['sessionSlots']} session slots"
        )


if __name__ == "__main__":
    main()
