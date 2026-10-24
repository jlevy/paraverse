from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from export_kb_native import build_dataset, export_native, match_legacy
from paraverse_graph.kb import load_kb


class NativeExportTests(unittest.TestCase):
    def make_kb(self, root: Path):
        records = {
            "events/example.md": (
                "event",
                {
                    "id": "event:example",
                    "name": "Example Conference",
                    "url": "https://example.org/event",
                },
            ),
            "people/example.md": (
                "person",
                {
                    "id": "person:example",
                    "name": "Example Speaker",
                    "job_title": "Engineer",
                    "bio": "Public conference biography.",
                    "accounts": ["gh:example"],
                    "participations": [
                        {"event": "event:example", "role": "speaker", "status": "confirmed"}
                    ],
                },
            ),
            "accounts/example.yaml": (
                "github_account",
                {
                    "id": "gh:example",
                    "login": "example",
                    "url": "https://github.com/example",
                    "entity": "person:example",
                },
            ),
            "rooms/example.yaml": ("room", {"id": "room:example", "label": "Main Stage"}),
            "sessions/example.md": (
                "session",
                {
                    "id": "session:example",
                    "event": "event:example",
                    "title": "A public talk",
                    "abstract": "Structured abstract.",
                    "url": "https://example.org/session/legacy-session",
                    "speakers": [{"person": "person:example"}],
                    "slots": [
                        {
                            "start": "2026-10-28T16:00:00-07:00",
                            "end": "2026-10-28T16:30:00-07:00",
                            "room": "room:example",
                        }
                    ],
                },
            ),
            "people/historical.md": (
                "person",
                {
                    "id": "person:historical",
                    "name": "Past Speaker",
                    "participations": [
                        {"event": "event:old", "role": "speaker", "status": "confirmed"}
                    ],
                },
            ),
        }
        nodes = []
        for rel, (kind, payload) in records.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            document = {
                "softschema": {"contract": f"example:{kind}/v1", "envelope": kind},
                kind: payload,
            }
            text = json.dumps(document)
            if path.suffix == ".md":
                text = f"---\n{text}\n---\n# Reader context\n\nBiography: do not consume this body."
            path.write_text(text)
            nodes.append({"id": payload["id"], "kind": kind, "path": rel})
        graph = root / "_graph"
        graph.mkdir()
        (graph / "nodes.jsonl").write_text("\n".join(json.dumps(n) for n in nodes))
        (graph / "edges.jsonl").write_text("")
        (graph / "stats.json").write_text("{}")
        return load_kb(root)

    def test_structured_export_preserves_sprite_identity_and_filters_event(self):
        with tempfile.TemporaryDirectory() as folder:
            kb = self.make_kb(Path(folder))
            legacy = [
                {
                    "id": "sprite-id",
                    "name": "Example Speaker",
                    "photo": "example.jpg",
                    "biography": "Stale text",
                }
            ]
            result = build_dataset(kb, "event:example", legacy)
            (person,) = result["people"]
            self.assertEqual(person["id"], "sprite-id")
            self.assertEqual(person["kbID"], "person:example")
            self.assertEqual(person["biography"], "Public conference biography.")
            self.assertEqual(person["githubURL"], "https://github.com/example")
            self.assertEqual(person["sessions"][0]["id"], "legacy-session")
            self.assertEqual(result["sessions"][0]["description"], "Structured abstract.")
            self.assertEqual(result, build_dataset(kb, "event:example", legacy))

    def test_body_and_legacy_biographies_never_fill_missing_yaml(self):
        with tempfile.TemporaryDirectory() as folder:
            kb = self.make_kb(Path(folder))
            kb.artifacts["people/example.md"].payload.pop("bio")
            result = build_dataset(
                kb,
                "event:example",
                [{"id": "old", "name": "Example Speaker", "biography": "Stale text"}],
            )
            self.assertEqual(result["people"][0]["biography"], "")
            self.assertEqual(result["gaps"]["missingBiographies"], ["person:example"])

    def test_ambiguous_legacy_identity_fails(self):
        legacy = [
            {"id": "one", "name": "Example Speaker"},
            {"id": "two", "name": "Example Speaker"},
        ]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            match_legacy({"id": "person:example", "name": "Example Speaker"}, {}, legacy)

    def test_account_identity_can_resolve_changed_name(self):
        person = {"id": "person:example", "name": "Updated Name"}
        legacy = [
            {"id": "sprite", "name": "Earlier Name", "githubURL": "https://github.com/Example/"}
        ]
        self.assertEqual(
            match_legacy(person, {"githubURL": "https://github.com/example"}, legacy), legacy[0]
        )

    def test_missing_graph_fails_instead_of_falling_back(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            self.assertRaisesRegex(ValueError, "incomplete"),
        ):
            load_kb(Path(folder))

    def test_repeated_session_slots_have_distinct_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            kb = self.make_kb(Path(folder))
            session = kb.artifacts["sessions/example.md"].payload
            session["slots"].append(
                {
                    "start": "2026-10-29T16:00:00-07:00",
                    "end": "2026-10-29T16:30:00-07:00",
                    "room": "room:example",
                }
            )
            result = build_dataset(kb, "event:example", [])
            self.assertEqual(len({s["id"] for s in result["sessions"]}), 2)
            self.assertEqual(len(result["people"][0]["sessions"]), 2)

    def test_attendee_projection_uses_self_report_and_actual_account_platform(self):
        with tempfile.TemporaryDirectory() as folder:
            kb = self.make_kb(Path(folder))
            participation = kb.artifacts["people/example.md"].payload["participations"][0]
            participation.update(
                role="attendee",
                status="self_reported",
                evidence=[
                    {
                        "url": "https://github.com/example/posts/1",
                        "quote": "I am attending Example Conference.",
                        "observed_at": "2026-10-24T10:00:00Z",
                    }
                ],
            )
            (attendee,) = build_dataset(kb, "event:example", [])["attendees"]
            self.assertEqual(attendee["platform"], "github")
            self.assertEqual(attendee["username"], "example")
            self.assertEqual(attendee["evidence"], "I am attending Example Conference.")
            self.assertEqual(attendee["post_date"], "2026-10-24T10:00:00Z")
            self.assertFalse(attendee["matching_opt_in"])
            participation["status"] = "unconfirmed"
            with self.assertRaisesRegex(ValueError, "no confirmed"):
                build_dataset(kb, "event:example", [])

    def test_unsubstantiated_attendance_is_never_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            kb = self.make_kb(Path(folder))
            person = kb.artifacts["people/example.md"].payload
            person["accounts"] = []
            person["participations"].append(dict(event="event:example",role="attendee",status="confirmed"))
            row, = build_dataset(kb,"event:example",[])["people"]
            self.assertFalse(row["attendee"])
            self.assertEqual(row["participationRoles"],["speaker"])
            person["participations"] = [person["participations"][-1]]
            with self.assertRaisesRegex(ValueError,"no confirmed"):
                build_dataset(kb,"event:example",[])

    def test_attendance_requires_owned_post_and_explicit_event_self_report(self):
        with tempfile.TemporaryDirectory() as folder:
            kb = self.make_kb(Path(folder))
            person = kb.artifacts["people/example.md"].payload
            person["participations"] = [dict(event="event:example",role="attendee",status="self_reported",evidence=[dict(url="https://github.com/example/posts/1",quote="I am attending Example Conference.")])]
            self.assertTrue(build_dataset(kb,"event:example",[])["people"][0]["attendee"])
            evidence = person["participations"][0]["evidence"][0]
            for url, quote in [("https://github.com/someone-else/posts/1","I am attending Example Conference."),("https://github.com/example/posts/1","Example Conference has a great agenda."),("https://github.com/example/posts/1","I am following news from colleagues at Example Conference."),("https://github.com/example/posts/1","I am not attending Example Conference.")]:
                evidence.update(url=url,quote=quote)
                with self.assertRaisesRegex(ValueError,"no confirmed"):
                    build_dataset(kb,"event:example",[])

    def test_validation_reuse_requires_same_clean_source_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_kb(root / "vendor/one/kb")
            datasets = (("one", "event:example", "world-speakers.json"),)
            with (
                patch("export_kb_native.DATASETS", datasets),
                patch(
                    "export_kb_native._git",
                    side_effect=lambda _repo, *args: "a" * 40 if args[0] == "rev-parse" else ("160000 commit " + "a" * 40 + "\t" + args[-1] if args[0] == "ls-tree" else ""),
                ),
                patch(
                    "export_kb_native.validate_artifacts", return_value=SimpleNamespace(ok=True)
                ) as validate,
            ):
                export_native(root / "vendor", root / "assets")
                self.assertEqual(validate.call_count, 1)

                export_native(root / "vendor", root / "assets", reuse_validation=True)
                self.assertEqual(validate.call_count, 1)
            with (
                patch("export_kb_native.DATASETS", datasets),
                patch(
                    "export_kb_native._git",
                    side_effect=lambda _repo, *args: "b" * 40 if args[0] == "rev-parse" else ("160000 commit " + "b" * 40 + "\t" + args[-1] if args[0] == "ls-tree" else ""),
                ),
                patch(
                    "export_kb_native.validate_artifacts", return_value=SimpleNamespace(ok=True)
                ) as validate,
            ):
                export_native(root / "vendor", root / "assets", reuse_validation=True)
                self.assertEqual(validate.call_count, 1)

    def test_native_browse_replaces_sessions_and_preserves_external_events(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_kb(root / "vendor/universe2026-md/kb")
            assets = root / "assets"
            assets.mkdir()
            external = [{"id": "external", "title": "Public meetup"}]
            (assets / "browse-events.json").write_text(
                json.dumps({"sessions": [{"id": "stale"}], "external": external})
            )
            with (
                patch(
                    "export_kb_native.DATASETS",
                    (("universe2026-md", "event:example", "world-speakers.json"),),
                ),
                patch(
                    "export_kb_native._git",
                    side_effect=lambda _repo, *args: "a" * 40 if args[0] == "rev-parse" else ("160000 commit " + "a" * 40 + "\t" + args[-1] if args[0] == "ls-tree" else ""),
                ),
            ):
                export_native(root / "vendor", assets, validate=False)
            browse = json.loads((assets / "browse-events.json").read_text())
            self.assertEqual(browse["external"], external)
            self.assertEqual([s["id"] for s in browse["sessions"]], ["legacy-session"])
            self.assertEqual(browse["sessions"][0]["reason"], "Official conference session")

    def test_later_missing_dataset_leaves_existing_assets_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_kb(root / "vendor/one/kb")
            assets = root / "assets"
            assets.mkdir()
            destination = assets / "world-speakers.json"
            destination.write_text("[]")
            datasets = (
                ("one", "event:example", "world-speakers.json"),
                ("missing", "event:example", "ptc-judges.json"),
            )
            with (
                patch("export_kb_native.DATASETS", datasets),
                patch(
                    "export_kb_native._git",
                    side_effect=lambda _repo, *args: "a" * 40 if args[0] == "rev-parse" else ("160000 commit " + "a" * 40 + "\t" + args[-1] if args[0] == "ls-tree" else ""),
                ),
                self.assertRaisesRegex(ValueError, "incomplete"),
            ):
                export_native(root / "vendor", assets, validate=False)
            self.assertEqual(destination.read_text(), "[]")
            self.assertEqual(list(assets.iterdir()), [destination])

    def test_unpinned_or_dirty_dataset_is_rejected_before_loading_or_publication(self):
        for dirty, checked_out in ((False, "b" * 40), (True, "a" * 40)):
            with self.subTest(dirty=dirty), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.make_kb(root / "vendor/one/kb")
                assets = root / "assets"
                assets.mkdir()
                destination = assets / "world-speakers.json"
                destination.write_text("[]")
                def git_state(_repo, *args):
                    if args[0] == "rev-parse": return checked_out
                    if args[0] == "ls-tree": return "160000 commit " + "a" * 40 + "\tvendor/one"
                    return " M kb/people/example.md" if dirty else ""
                with (
                    patch("export_kb_native.DATASETS", (("one", "event:example", "world-speakers.json"),)),
                    patch("export_kb_native._git", side_effect=git_state),
                    patch("export_kb_native.load_kb", wraps=load_kb) as load,
                    self.assertRaisesRegex(ValueError, "pinned|uncommitted"),
                ):
                    export_native(root / "vendor", assets, validate=False)
                load.assert_not_called()
                self.assertEqual(destination.read_text(), "[]")

    def test_publication_failure_preserves_original_and_cleans_staging_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_kb(root / "vendor/one/kb")
            assets = root / "assets"
            assets.mkdir()
            destination = assets / "world-speakers.json"
            destination.write_text("[]")
            with (
                patch(
                    "export_kb_native.DATASETS", (("one", "event:example", "world-speakers.json"),)
                ),
                patch(
                    "export_kb_native._git",
                    side_effect=lambda _repo, *args: "a" * 40 if args[0] == "rev-parse" else ("160000 commit " + "a" * 40 + "\t" + args[-1] if args[0] == "ls-tree" else ""),
                ),
                patch("export_kb_native.os.replace", side_effect=OSError("publish failed")),
                self.assertRaisesRegex(OSError, "publish failed"),
            ):
                export_native(root / "vendor", assets, validate=False)
            self.assertEqual(destination.read_text(), "[]")
            self.assertEqual(list(assets.iterdir()), [destination])


if __name__ == "__main__":
    unittest.main()
