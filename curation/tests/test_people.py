from __future__ import annotations

import csv
import io

import pytest

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


@pytest.mark.parametrize(
    "value",
    [
        "Email: example @ example.org",
        "Email: example @ example",
        "E-mail address: example @example.org",
        "EMAIL: example@ example.org",
    ],
)
def test_contextual_spaced_email_is_rejected(value: str) -> None:
    report = check_list_text(listed(person(reason=value)))
    assert any(p.column == "reason" and "email address" in p.message for p in report.problems)


@pytest.mark.parametrize("title", ["Engineer at Example.com", "Engineer @ Example.com"])
def test_professional_affiliations_are_not_email_addresses(title: str) -> None:
    assert not check_list_text(listed(person(title=title))).problems


@pytest.mark.parametrize(
    "host",
    [
        "server.local",
        "app.localhost",
        "localhost.localdomain",
        "service.internal",
        "router.home.arpa",
        "host.test",
        "host.invalid",
    ],
)
def test_private_hosts_are_rejected_across_url_and_account_columns(host: str) -> None:
    for column, value in (
        ("source_url", f"https://{host}/team"),
        ("attendance_source", f"https://{host}/post"),
        ("target", f"https://{host}/project"),
        ("website", f"https://{host}/profile"),
        ("bluesky", host),
        ("mastodon", f"@example@{host}"),
        ("mastodon", f"https://{host}/@example"),
    ):
        report = check_list_text(listed(person(**{column: value})))
        assert any(p.column == column for p in report.problems), (column, host)


@pytest.mark.parametrize(
    "first,second",
    [
        ("https://example.org/Alice", "https://example.org/alice"),
        ("https://example.org/profile?id=1", "https://example.org/profile?id=2"),
        ("https://example.org:8443/profile", "https://example.org:9443/profile"),
        ("https://example.org/profile#Alice", "https://example.org/profile#Bob"),
        ("https://example.org/profile", "https://example.org/profile/"),
    ],
)
def test_distinct_website_profiles_are_not_duplicate_facts(first: str, second: str) -> None:
    assert not check_list_text(
        listed(
            person(github="", website=first),
            person(github="", website=second),
        )
    ).problems


def test_website_host_case_is_normalized_but_target_url_paths_remain_distinct() -> None:
    duplicate = check_list_text(
        listed(
            person(github="", website="HTTPS://EXAMPLE.ORG/Alice?id=1"),
            person(github="", website="https://example.org/Alice?id=1"),
        )
    )
    assert any("same account, relation and target" in p.message for p in duplicate.problems)
    assert not check_list_text(
        listed(
            person(target="https://example.org/Project"),
            person(target="https://example.org/project"),
        )
    ).problems


@pytest.mark.parametrize("column", ["source_url", "attendance_source", "website"])
@pytest.mark.parametrize("tail", ["/example%40example.org", "/team?contact=example%40example.org"])
def test_encoded_email_in_url_is_rejected_without_echoing_it(column: str, tail: str) -> None:
    value = f"https://example.org{tail}"
    report = check_list_text(listed(person(**{column: value})))
    assert any(p.column == column and "email address" in p.message for p in report.problems)
    assert all(value not in str(p) and "example@example.org" not in str(p) for p in report.problems)


@pytest.mark.parametrize("column", ["source_url", "attendance_source", "website"])
@pytest.mark.parametrize("tail", ["/202-555-0100", "/team?phone=202-555-0100"])
def test_formatted_phone_in_url_is_rejected(column: str, tail: str) -> None:
    report = check_list_text(listed(person(**{column: f"https://example.org{tail}"})))
    assert any(p.column == column and "phone number" in p.message for p in report.problems)


def test_numeric_accounts_and_profile_ids_are_not_free_text_phone_numbers() -> None:
    for column, value in (
        ("github", "1234567890"),
        ("x", "1234567890"),
        ("x", "@1234567890"),
        ("source_url", "https://example.org/profiles/1234567890"),
        ("website", "https://example.org/profile?id=1234567890"),
        ("added_by", "1234567890"),
    ):
        assert not check_list_text(listed(person(**{column: value}))).problems, column
    for value in ("Call 1234567890", "Call 020/7946/0000", "Call 202/555/0100"):
        report = check_list_text(listed(person(reason=value)))
        assert any(p.column == "reason" and "phone number" in p.message for p in report.problems)


@pytest.mark.parametrize("value", ["020/7946/0000", "202/555/0100"])
def test_slash_separated_phone_numbers_are_rejected(value: str) -> None:
    report = check_list_text(listed(person(reason=f"Call {value}")))
    assert any(p.column == "reason" and "phone number" in p.message for p in report.problems)
