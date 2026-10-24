"""
Check lists of additional people, `<dataset>/additional-people.csv`, against the list
format and the data policy before a dataset's pipeline reads them.

The format is the one the dataset pipeline reads with `--additional-people`: one row
per person and relation, public and professional information only, and no contact
details in any cell. These checks are deliberately about form; whether a source really
supports a row is for the reviewer.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import override
from urllib.parse import unquote, urlsplit, urlunsplit

LIST_NAME = "additional-people.csv"

# The exact header, in order. The dataset pipeline reads the same file.
COLUMNS: tuple[str, ...] = (
    "name",
    "reason",
    "relation",
    "target",
    "source_url",
    "github",
    "linkedin",
    "x",
    "bluesky",
    "mastodon",
    "website",
    "organization",
    "title",
    "attendance_source",
    "added_by",
    "added_on",
)

REQUIRED: tuple[str, ...] = ("name", "reason", "relation", "source_url", "added_by", "added_on")

RELATIONS: tuple[str, ...] = (
    "maintainer",
    "author",
    "colleague",
    "organizer_staff",
    "sponsor_staff",
    "community",
)

ACCOUNT_COLUMNS: tuple[str, ...] = ("github", "linkedin", "x", "bluesky", "mastodon", "website")


@dataclass(frozen=True)
class Problem:
    path: str
    line: int
    column: str | None
    message: str

    @override
    def __str__(self) -> str:
        where = f"{self.path}:{self.line}"
        if self.column:
            return f"{where}: {self.column}: {self.message}"
        return f"{where}: {self.message}"


@dataclass
class ListReport:
    path: str
    rows: int = 0
    problems: list[Problem] = field(default_factory=list)


# ---- Value forms ----

_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
# A public host name: two or more labels, ending in a TLD that starts with a letter, so
# `localhost` and IP addresses don't pass.
_DOMAIN = r"(?:" + _LABEL + r"\.)+[A-Za-z](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_GITHUB_HANDLE = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
_X_HANDLE = r"[A-Za-z0-9_]{1,15}"
_MASTODON_USER = r"[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_])?"

_DOMAIN_RE = re.compile(_DOMAIN)
# These suffixes describe local or reserved namespaces, not public profile hosts.
_PRIVATE_HOST_SUFFIXES = (
    "local",
    "localhost",
    "localdomain",
    "internal",
    "home.arpa",
    "test",
    "invalid",
)
_GITHUB_HANDLE_RE = re.compile(r"@?(" + _GITHUB_HANDLE + r")")
_GITHUB_URL_RE = re.compile(r"https://(?:www\.)?github\.com/(" + _GITHUB_HANDLE + r")/?", re.I)
_LINKEDIN_URL_RE = re.compile(r"https://(?:www\.|[a-z]{2}\.)?linkedin\.com/in/([\w%-]+)/?", re.I)
_X_HANDLE_RE = re.compile(r"@?(" + _X_HANDLE + r")")
_X_URL_RE = re.compile(
    r"https://(?:www\.|mobile\.)?(?:x|twitter)\.com/(" + _X_HANDLE + r")/?", re.I
)
_BLUESKY_HANDLE_RE = re.compile(r"@?(" + _DOMAIN + r")")
_MASTODON_HANDLE_RE = re.compile(r"@(" + _MASTODON_USER + r")@(" + _DOMAIN + r")")
_MASTODON_URL_RE = re.compile(r"https://(" + _DOMAIN + r")/@(" + _MASTODON_USER + r")/?", re.I)
_TYPED_ID_RE = re.compile(r"[a-z][a-z_]*:[^\s:/]\S*")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _public_host(host: str) -> bool:
    host = host.lower()
    return bool(_DOMAIN_RE.fullmatch(host)) and not any(
        host == suffix or host.endswith(f".{suffix}") for suffix in _PRIVATE_HOST_SUFFIXES
    )


def https_url(value: str) -> str | None:
    """
    An HTTPS URL with normalized scheme/host and its other components preserved, or `None`.
    Rejects URLs with credentials (`https://user@host`), which can hide an email
    address, and local hosts.
    """
    if any(ch.isspace() for ch in value):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme != "https" or "@" in parts.netloc:
        return None
    try:
        parts.port  # noqa: B018 (raises ValueError on a malformed port)
    except ValueError:
        return None
    host = parts.hostname or ""
    if not _public_host(host):
        return None
    # Only the scheme and host are case-insensitive. Keep an explicit port, path,
    # query and fragment: each can distinguish professional profile pages.
    return urlunsplit(("https", parts.netloc.lower(), parts.path, parts.query, parts.fragment))


def github_account(value: str) -> str | None:
    match = _GITHUB_URL_RE.fullmatch(value) or _GITHUB_HANDLE_RE.fullmatch(value)
    return match.group(1).lower() if match else None


def linkedin_account(value: str) -> str | None:
    match = _LINKEDIN_URL_RE.fullmatch(value)
    return match.group(1).lower() if match else None


def x_account(value: str) -> str | None:
    match = _X_URL_RE.fullmatch(value) or _X_HANDLE_RE.fullmatch(value)
    return match.group(1).lower() if match else None


def bluesky_account(value: str) -> str | None:
    match = _BLUESKY_HANDLE_RE.fullmatch(value)
    return match.group(1).lower() if match and _public_host(match.group(1)) else None


def mastodon_account(value: str) -> str | None:
    match = _MASTODON_HANDLE_RE.fullmatch(value)
    if match and _public_host(match.group(2)):
        return f"{match.group(1)}@{match.group(2)}".lower()
    match = _MASTODON_URL_RE.fullmatch(value)
    if match and _public_host(match.group(1)):
        return f"{match.group(2)}@{match.group(1)}".lower()
    return None


# Each account column's parser, which returns a normalized account for matching
# duplicates, and the forms it accepts.
ACCOUNTS: dict[str, tuple[Callable[[str], str | None], str]] = {
    "github": (
        github_account,
        "a GitHub handle (janedoe or @janedoe) or profile URL (https://github.com/janedoe)",
    ),
    "linkedin": (linkedin_account, "a LinkedIn profile URL (https://www.linkedin.com/in/janedoe)"),
    "x": (x_account, "an X handle (@janedoe) or profile URL (https://x.com/janedoe)"),
    "bluesky": (bluesky_account, "a Bluesky handle (janedoe.bsky.social or a custom domain)"),
    "mastodon": (
        mastodon_account,
        "a Mastodon handle (@user@host) or profile URL (https://host/@user)",
    ),
    "website": (https_url, "an https URL on a public host name"),
}


def is_target(value: str) -> bool:
    """
    A KB ID such as `software:example-tool`, or an https URL.
    """
    if value.lower().startswith(("http:", "https:")):
        return https_url(value) is not None
    return bool(_TYPED_ID_RE.fullmatch(value))


def is_iso_date(value: str) -> bool:
    if not _ISO_DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


# ---- Contact details ----

# An `@` before the local part marks a fediverse handle (`@user@host`), not an email.
_EMAIL_RE = re.compile(r"(?<![\w.%+@-])[\w.%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
# An explicit email label also identifies spaced or dotless addresses without
# treating professional affiliations such as "Engineer @ Example.com" as contact.
_CONTEXTUAL_EMAIL_RE = re.compile(
    r"\be-?mail(?:\s+address)?\s*:\s*[\w.+-]+\s*@\s*[\w-]+(?:\.[\w-]+)*", re.I
)
_AT_BRACKETED = r"\s*[\[({<]\s*at\s*[\])}>]\s*"
_DOT_SPELLED = r"(?:\s*[\[({<]\s*dot\s*[\])}>]\s*|\s+dot\s+)"
_ANY_DOT = r"(?:" + _DOT_SPELLED + r"|\.)"
# Spelled-out addresses ("x at y dot z", "x [at] y.z"). A plain " at " needs a spelled
# "dot", so a title such as "Engineer at Example.com" is not an address.
_SPELLED_EMAIL_RES = (
    re.compile(r"[\w.+-]+" + _AT_BRACKETED + r"[\w-]+(?:" + _ANY_DOT + r"[\w-]+)+", re.I),
    re.compile(
        r"[\w.+-]+(?:\s+at\s+|\s*@\s*)(?:[\w-]+"
        + _ANY_DOT
        + r")*?[\w-]+"
        + _DOT_SPELLED
        + r"[\w-]+",
        re.I,
    ),
)

# URL components are checked for formatted contacts, while bare numeric profile
# and post IDs remain valid.
_URL_IN_TEXT_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.I)
_FORMATTED_PHONE_RES = (
    # International: a + and 7 to 15 digits, with any separators.
    re.compile(r"(?<![\w+])\+\d(?:[\s./()-]*\d){6,14}(?!\d)"),
    # Grouped: (202) 555-0100, 202-555-0100, 020 7946 0000. ISO dates don't match.
    re.compile(r"(?<![\w.-])\(?\d{2,4}\)?[\s./-]?\d{3,4}[\s./-]\d{4}(?![\w.-])"),
)
_BARE_PHONE_RE = re.compile(r"(?<![\w.+/-])\d{10,15}(?![\w.-])")


def has_email(text: str) -> bool:
    text = _URL_IN_TEXT_RE.sub(lambda match: unquote(match.group()), text)
    return (
        bool(_EMAIL_RE.search(text))
        or bool(_CONTEXTUAL_EMAIL_RE.search(text))
        or any(r.search(text) for r in _SPELLED_EMAIL_RES)
    )


def has_phone(text: str, *, numeric_account: bool = False) -> bool:
    for match in _URL_IN_TEXT_RE.finditer(text):
        if any(pattern.search(unquote(match.group())) for pattern in _FORMATTED_PHONE_RES):
            return True
    text = _URL_IN_TEXT_RE.sub(" ", text)
    return any(pattern.search(text) for pattern in _FORMATTED_PHONE_RES) or (
        not numeric_account and bool(_BARE_PHONE_RE.search(text))
    )


# ---- Rows and lists ----


def check_row(row: dict[str, str]) -> list[tuple[str | None, str]]:
    """
    The problems in one row, keyed by `COLUMNS`, as `(column, message)` pairs; the
    column is `None` for a problem with the row as a whole.
    """
    found: list[tuple[str | None, str]] = []
    for column, value in row.items():
        if value != value.strip():
            found.append((column, "has leading or trailing spaces"))
        if "\n" in value or "\r" in value:
            found.append((column, "has a line break; keep each cell on one line"))
        if has_email(value):
            found.append((column, "contains an email address; no contact details allowed"))
        # A valid platform handle can consist entirely of digits. This exemption
        # affects only bare numbers; formatted contacts still fail in account cells.
        numeric_account = (
            column in ACCOUNTS and column != "website" and ACCOUNTS[column][0](value) is not None
        ) or (column == "added_by" and _GITHUB_HANDLE_RE.fullmatch(value) is not None)
        if has_phone(value, numeric_account=numeric_account):
            found.append((column, "contains a phone number; no contact details allowed"))

    cell = {column: value.strip() for column, value in row.items()}
    for column in REQUIRED:
        if not cell[column]:
            found.append((column, "is required"))
    if cell["relation"] and cell["relation"] not in RELATIONS:
        found.append(("relation", f"must be one of {', '.join(RELATIONS)}"))
    if cell["target"] and not is_target(cell["target"]):
        found.append(("target", "must be a KB ID (such as software:example-tool) or an https URL"))
    for column in ("source_url", "attendance_source"):
        if cell[column] and https_url(cell[column]) is None:
            found.append((column, "must be an https URL on a public host name"))

    if not any(cell[column] for column in ACCOUNT_COLUMNS):
        found.append((None, f"needs at least one account: {', '.join(ACCOUNT_COLUMNS)}"))
    for column, (parse, form) in ACCOUNTS.items():
        if cell[column] and parse(cell[column]) is None:
            found.append((column, f"must be {form}"))

    if cell["added_by"] and not _GITHUB_HANDLE_RE.fullmatch(cell["added_by"]):
        found.append(("added_by", "must be the GitHub handle of whoever added the row"))
    if cell["added_on"] and not is_iso_date(cell["added_on"]):
        found.append(("added_on", "must be a date as YYYY-MM-DD"))
    return found


def _accounts(cell: dict[str, str]) -> list[str]:
    """
    The row's valid accounts, normalized so that a handle and its profile URL match.
    """
    accounts: list[str] = []
    for column, (parse, _form) in ACCOUNTS.items():
        account = parse(cell[column].strip()) if cell[column].strip() else None
        if account:
            accounts.append(f"{column}:{account}")
    return accounts


def _header_message(header: list[str]) -> str:
    missing = [c for c in COLUMNS if c not in header]
    unexpected = [str(index) for index, c in enumerate(header, start=1) if c not in COLUMNS]
    details: list[str] = []
    if missing:
        details.append(f"missing {', '.join(missing)}")
    if unexpected:
        details.append(f"unexpected columns at positions {', '.join(unexpected)}")
    if not details:
        details.append("columns repeated or out of order")
    return f"header must be exactly {','.join(COLUMNS)} ({'; '.join(details)})"


def check_list_text(text: str, path: str = LIST_NAME) -> ListReport:
    """
    Check the text of one list. A wrong header stops the check, since the cells can't
    be matched to columns.
    """
    report = ListReport(path)

    def add(line: int, column: str | None, message: str) -> None:
        report.problems.append(Problem(path, line, column, message))

    if text.startswith("\ufeff"):
        add(1, None, "starts with a byte-order mark; save it as UTF-8 without one")
        text = text[1:]

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
    except csv.Error:
        add(1, None, "has malformed CSV quoting")
        return report
    if header is None:
        add(1, None, f"is empty; it needs at least the header row, {','.join(COLUMNS)}")
        return report
    if tuple(header) != COLUMNS:
        add(1, None, _header_message(header))
        return report

    first_line: dict[tuple[str, ...], int] = {}
    person_line: dict[tuple[str, str, str], int] = {}
    while True:
        line = reader.line_num + 1
        try:
            cells = next(reader, None)
        except csv.Error:
            add(line, None, "has malformed CSV quoting")
            break
        if cells is None:
            break
        if not cells:
            continue
        report.rows += 1
        if len(cells) != len(COLUMNS):
            add(line, None, f"has {len(cells)} cells; the header has {len(COLUMNS)}")
            continue
        if not any(c.strip() for c in cells):
            add(line, None, "is an empty row; delete it")
            continue

        cell = dict(zip(COLUMNS, cells, strict=True))
        for column, message in check_row(cell):
            add(line, column, message)

        row_key = tuple(c.strip() for c in cells)
        if row_key in first_line:
            add(line, None, f"repeats line {first_line[row_key]}")
            continue
        first_line[row_key] = line
        # One row per person and relation: the same account with the same relation
        # and target is the same fact twice.
        relation = cell["relation"].strip()
        raw_target = cell["target"].strip()
        target = https_url(raw_target) or raw_target.rstrip("/").casefold()
        keys = [(relation, target, account) for account in _accounts(cell)]
        earlier = next((person_line[k] for k in keys if k in person_line), None)
        if earlier is not None:
            add(line, None, f"has the same account, relation and target as line {earlier}")
        for key in keys:
            person_line.setdefault(key, line)
    return report


def check_list(path: Path, label: str | None = None) -> ListReport:
    label = label or str(path)
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        report = ListReport(label)
        report.problems.append(Problem(label, 1, None, "is not valid UTF-8"))
        return report
    return check_list_text(text, label)


def find_lists(root: Path) -> list[Path]:
    """
    Every `<dataset>/additional-people.csv` directly under `root`.
    """
    return sorted(root.glob(f"*/{LIST_NAME}"))
