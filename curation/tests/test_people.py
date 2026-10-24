from __future__ import annotations

import csv
import io

from paraverse_curation.people import COLUMNS, check_list_text


def listed(*rows: dict[str, str]) -> str:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def person(**changes: str) -> dict[str, str]:
    return {
        **dict.fromkeys(COLUMNS, ""),
        "name": "Example Person",
        "reason": "Maintains the example project",
        "relation": "maintainer",
        "target": "software:example-project",
        "source_url": "https://example.org/team",
        "github": "example-person",
        "added_by": "example-editor",
        "added_on": "2026-10-24",
        **changes,
    }


def test_lists_check_accounts_provenance_and_duplicate_facts() -> None:
    for column, value in (
        ("github", "https://github.com/Example-Person"),
        ("linkedin", "https://www.linkedin.com/in/example-person"),
        ("x", "@example_person"),
        ("bluesky", "example.bsky.social"),
        ("mastodon", "@example@social.example.org"),
        ("website", "https://example.org"),
    ):
        assert not check_list_text(
            listed(
                person(github="", **{column: value}) if column != "github" else person(github=value)
            )
        ).problems
    duplicate = check_list_text(
        listed(person(), person(github="https://github.com/Example-Person/"))
    )
    assert any("same account, relation and target" in p.message for p in duplicate.problems)
    assert not check_list_text(listed(person(), person(relation="author"))).problems
    assert not check_list_text(listed()).problems


def test_lists_reject_contact_details_invalid_sources_and_malformed_csv() -> None:
    for column, value in (
        ("reason", "Contact example@example.org"),
        ("reason", "example [at] example dot org"),
        ("title", "Call +44 20 7946 0123"),
        ("source_url", "https://[broken"),
        ("source_url", "https://user:password@example.org/team"),
        ("attendance_source", "http://example.org/post"),
        ("target", "../private"),
        ("added_on", "2026-02-30"),
        ("relation", "friend"),
        ("github", ""),
    ):
        report = check_list_text(listed(person(**{column: value})))
        assert any(p.column == column or p.column is None for p in report.problems)
    for text in ("", "name,reason\n", listed() + '"unclosed', listed() + "one,two\n"):
        assert check_list_text(text).problems
