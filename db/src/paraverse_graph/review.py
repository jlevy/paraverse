"""
Data-quality checks over the knowledge base graph, shown in the browser's Review
view. Each check is read-only Cypher returning `id`, `name` and `detail` columns, so
every finding links to the entity it is about. Each ends in `LIMIT $limit`, which
`run_check` binds to one more than `ROW_LIMIT` to tell a full page from a truncated one.
"""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Literal

ROW_LIMIT = 200

Severity = Literal["blocker", "high", "medium", "low", "info"]
SEVERITY_ORDER: tuple[Severity, ...] = ("blocker", "high", "medium", "low", "info")


@dataclass(frozen=True)
class Check:
    name: str
    title: str
    severity: Severity
    description: str
    cypher: str
    area: str = "graph"


def _q(text: str) -> str:
    return dedent(text).strip()


CHECKS: tuple[Check, ...] = (
    Check(
        "isolated_entities",
        "Entities with no relationships",
        "medium",
        "Nodes nothing points to and that point to nothing; usually an unlinked record.",
        _q("""
            MATCH (n:Entity) WHERE NOT (n)--()
            RETURN n.id AS id, n.display_name AS name, n.entity_kind AS detail
            ORDER BY detail, name LIMIT $limit
            """),
    ),
    Check(
        "accounts_without_owner",
        "Accounts not linked to a person or organization",
        "low",
        "GitHub or social accounts that no person or organization has.",
        _q("""
            MATCH (a:Account) WHERE NOT ()-[:HAS_ACCOUNT]->(a)
            RETURN a.id AS id, a.display_name AS name, a.entity_kind AS detail
            ORDER BY name LIMIT $limit
            """),
    ),
    Check(
        "people_same_name",
        "People who share a name",
        "high",
        "Two person records with the same name: either a split identity or two people.",
        _q("""
            MATCH (a:Person), (b:Person)
            WHERE a.id < b.id AND toLower(a.display_name) = toLower(b.display_name)
            RETURN a.id AS id, a.display_name AS name, 'also ' + b.id AS detail
            ORDER BY name LIMIT $limit
            """),
    ),
    Check(
        "slot_day_mismatch",
        "Slot day does not match its local start date or its event",
        "blocker",
        "A session slot whose day is not the local calendar date of the slot start, or whose day is not one of the session's event days. Either one puts the session under the wrong day of a published schedule.",
        _q(
            "MATCH (s:Session)-[r:SCHEDULED_ON]->(d:Day) MATCH (s)-[:PART_OF]->(e:Event) OPTIONAL MATCH (e)-[h:HAS_DAY]->(d) WITH s, r, d, e, h WHERE d.date <> substring(r.start, 0, 10) OR h IS NULL RETURN s.id AS id, s.title AS name, 'slot ' + r.start + ' on ' + d.id + ' of ' + e.id AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "session_edition_mismatch",
        "Session start year or ID namespace disagrees with its event",
        "blocker",
        "A session whose first slot is not in its event's edition year, or whose year-namespaced ID (session:<year>/...) names a different edition than its event.",
        _q(
            "MATCH (s:Session)-[:PART_OF]->(e:Event) WITH s, e, 'session:' + e.edition + '/' AS ns WHERE substring(s.start, 0, 4) <> e.edition OR (s.id CONTAINS '/' AND NOT (s.id STARTS WITH ns)) RETURN s.id AS id, s.title AS name, 'event ' + e.id + ' (edition ' + e.edition + '), starts ' + s.start AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "room_double_booked",
        "Two sessions in one room at overlapping times",
        "blocker",
        "Pairs of single-slot sessions in the same room whose times overlap, plus any two slots in one room with the same start. Watch parties have their own rooms, so any row is a real conflict or a duplicate.",
        _q(
            "MATCH (a:Session)-[ra:HELD_IN]->(rm:Room)<-[rb:HELD_IN]-(b:Session) WHERE a.id < b.id AND ((a.slot_count = 1 AND b.slot_count = 1 AND a.start_epoch < b.end_epoch AND b.start_epoch < a.end_epoch) OR ra.start_epoch = rb.start_epoch) RETURN a.id AS id, a.title AS name, 'overlaps ' + b.id + ' in ' + rm.id + ' at ' + ra.start AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "day_one_is_pre_event",
        "Day labelled 'Day 1' is a light pre-event day",
        "high",
        "An edition whose 'Day 1' has under a fifth of the sessions of its busiest day. The label was probably assigned by date order, so a pre-event social or workshop day is shown as the first conference day.",
        _q(
            "MATCH (e:Event)-[:HAS_DAY]->(d:Day) OPTIONAL MATCH (s:Session)-[:SCHEDULED_ON]->(d) WITH e, d, count(s) AS n WITH e, collect({id: d.id, label: d.label, n: n}) AS days, max(n) AS busiest UNWIND days AS day WITH e, day, busiest WHERE day.label = 'Day 1' AND day.n * 5 < busiest RETURN day.id AS id, e.name + ' ' + day.label AS name, toString(day.n) + ' slots vs ' + toString(busiest) + ' on the busiest day' AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "term_session_count_drift",
        "Term.session_count differs from its session edges",
        "medium",
        "A facet term whose stored session_count is not the number of sessions linked to it, so a filter's badge count disagrees with the list it opens.",
        _q(
            "MATCH (t:Term) OPTIONAL MATCH (s:Session)-[]->(t) WITH t, count(DISTINCT s) AS actual WHERE actual <> t.session_count RETURN t.id AS id, t.label AS name, 'session_count ' + toString(t.session_count) + ', linked sessions ' + toString(actual) AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "campus_room_at_external_venue",
        "Campus room placed at an external venue",
        "high",
        "A room whose catalog label names a Fort Mason building or area but which is linked to an 'external' venue, so it is shown off campus with the building name as its street address.",
        _q(
            "MATCH (r:Room)-[:LOCATED_IN]->(v:Venue) WHERE v.kind = 'external' AND (r.label CONTAINS 'Fort Mason' OR r.label CONTAINS 'Pavilion' OR r.label CONTAINS 'Firehouse' OR r.label CONTAINS 'General' OR r.label CONTAINS 'Building' OR r.label CONTAINS 'Plaza' OR r.label CONTAINS 'Greens') RETURN r.id AS id, r.label AS name, 'external venue ' + v.id + ', address ' + coalesce(v.address, '(none)') AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "external_venue_without_street_address",
        "External venue without a street address",
        "medium",
        "An outside venue with no address, or one whose address does not start with a street number (a building name, neighbourhood or room text instead).",
        _q(
            "MATCH (v:Venue) WHERE v.kind = 'external' AND (v.address IS NULL OR NOT left(v.address, 1) IN ['0','1','2','3','4','5','6','7','8','9']) OPTIONAL MATCH (r:Room)-[:LOCATED_IN]->(v) WITH v, count(r) AS rooms RETURN v.id AS id, v.name AS name, 'address ' + coalesce(v.address, '(none)') + '; rooms ' + toString(rooms) AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "possible_duplicate_places",
        "Venues or rooms that may be one place under two IDs",
        "medium",
        "Venue pairs whose names are equal ignoring case or one is a prefix of the other, or that share a street-address prefix and the first word of their names; and room pairs with the same name at the same venue (catalog label variants such as a changed floor note or address spelling). Review each pair: a merged room can also hide a changed address.",
        _q(
            "CALL { MATCH (a:Venue), (b:Venue) WHERE a.id < b.id AND (toLower(a.name) STARTS WITH toLower(b.name) OR toLower(b.name) STARTS WITH toLower(a.name) OR (a.address IS NOT NULL AND b.address IS NOT NULL AND split(toLower(a.name), ' ')[0] = split(toLower(b.name), ' ')[0] AND (a.address STARTS WITH b.address OR b.address STARTS WITH a.address))) RETURN a.id AS id, a.name AS name, 'venue ' + b.id + ' (' + b.name + '); addresses ' + coalesce(a.address, '-') + ' / ' + coalesce(b.address, '-') AS detail UNION ALL MATCH (a:Room)-[:LOCATED_IN]->(v:Venue)<-[:LOCATED_IN]-(b:Room) WHERE a.id < b.id AND toLower(a.name) = toLower(b.name) RETURN a.id AS id, a.label AS name, 'room ' + b.id + ' (' + b.label + ') at ' + v.id AS detail } RETURN id, name, detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "placeholder_capacity",
        "Room capacity is a catalog placeholder",
        "high",
        "A room whose capacity is 9,999 or more. The catalog uses 9999 and 1000000 for unlimited or unknown seating; publishing them as capacities is wrong.",
        _q(
            "MATCH (r:Room) WHERE r.capacity >= 5000 OPTIONAL MATCH (s:Session)-[:HELD_IN]->(r) WITH r, count(DISTINCT s) AS n RETURN r.id AS id, r.label AS name, 'capacity ' + toString(r.capacity) + '; sessions ' + toString(n) AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "program_session_without_speakers",
        "Program session with no speakers",
        "high",
        "A session with no PRESENTS edge whose type is not Social or Special Event and which is not a keynote viewing area or watch party.",
        _q(
            "MATCH (s:Session)-[:HAS_TYPE]->(t:Term) WHERE NOT t.label IN ['Social', 'Special Event'] AND NOT s.title STARTS WITH 'Viewing Area' AND NOT s.title STARTS WITH 'Watch the Keynote' AND NOT ()-[:PRESENTS]->(s) RETURN s.id AS id, s.title AS name, 'type ' + t.label AS detail ORDER BY id LIMIT $limit"
        ),
        area="program",
    ),
    Check(
        "org_multiple_linkedin_pages",
        "Organization merged from more than one LinkedIn company page",
        "blocker",
        "The build copies industry, size, headquarters, founded, tagline and logo from every LinkedIn page an organization owns, last page wins. Two pages means one of them may be another company's (IBM picked up the 2-10 employee Knowledge Stream page).",
        _q(
            "MATCH (o:Organization)-[:HAS_ACCOUNT]->(a:SocialAccount) WHERE a.id STARTS WITH 'acct:linkedin/company/' WITH o, collect(a.id) AS pages WHERE size(pages) > 1 RETURN o.id AS id, o.name AS name, 'LinkedIn pages: ' + reduce(s = '', p IN pages | s + p + ' ') + '| size=' + coalesce(o.size, '-') + ' industry=' + coalesce(o.industry, '-') AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "org_name_prefix_duplicates",
        "Organization whose name extends another organization's name",
        "high",
        "Likely duplicates from legal suffixes or longer spellings (Cathay Pacific / Cathay Pacific Airways, Otto / Otto GmbH & Co KG, Pendo / Pendo.io). Pairs already joined by RELATED_TO are left out; true subsidiaries should get a RELATED_TO link instead of a merge.",
        _q(
            # A name that extends another at a separator shares its first word (up to a
            # space, '.', ',' or '|'), so pairs are compared within first-word groups,
            # not across all organizations, which was quadratic.
            "MATCH (o:Organization) WITH split(split(split(split(toLower(o.name), ' ')[0], '.')[0], ',')[0], '|')[0] AS first_word, collect(o) AS orgs WHERE size(orgs) > 1 UNWIND orgs AS a UNWIND orgs AS b WITH a, b WHERE a.id <> b.id AND size(b.name) > size(a.name) AND toLower(b.name) STARTS WITH toLower(a.name) AND substring(b.name, size(a.name), 1) IN [' ', '.', ',', '|'] AND NOT (a)-[:RELATED_TO]-(b) OPTIONAL MATCH (p:Person)-[:AFFILIATED_WITH]->(a) WHERE (p)-[:AFFILIATED_WITH]->(b) WITH a, b, count(DISTINCT p) AS shared RETURN b.id AS id, b.name AS name, 'possible duplicate of ' + a.id + ' (' + a.name + '); people affiliated with both: ' + toString(shared) AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "org_mention_is_job_title_word",
        "Organization mention that is really a word in a job title",
        "high",
        "The gazetteer matches organization names case-sensitively, so a company named like a title word ('Principal') is 'mentioned' by every 'Principal Engineer'. Flags mentions where the name is followed by a role word in the mentioning text.",
        _q(
            "MATCH (s:Entity)-[m:MENTIONS]->(o:Organization) WITH s, m, o, CASE m.field WHEN 'bio' THEN s.bio WHEN 'abstract' THEN s.abstract ELSE s.title END AS text WHERE text IS NOT NULL AND any(w IN ['Engineer', 'Software', 'Security Researcher', 'Security Engineer', 'Product', 'Researcher', 'Research Software', 'Architect', 'Solution', 'Field', 'Lead', 'Trainer', 'Developer', 'User', 'Application', 'Investigator', 'Program', 'Consultant', 'Manager', 'R&D'] WHERE text CONTAINS (o.name + ' ' + w)) RETURN o.id AS id, o.name AS name, s.id + ' (' + m.field + ')' AS detail ORDER BY id, detail LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "org_size_implausible",
        "LinkedIn size range contradicts the organization's footprint",
        "medium",
        "A sponsor whose LinkedIn size is 1 or 2-10 employees, or any organization with more currently affiliated people in the KB than the top of its LinkedIn size range. The usual cause is a second, unrelated LinkedIn page merged into the record.",
        _q(
            "MATCH (o:Organization) WHERE o.size IS NOT NULL OPTIONAL MATCH (p:Person)-[r:AFFILIATED_WITH]->(o) WHERE r.current = true WITH o, count(DISTINCT p) AS current_people WHERE (o:Sponsor AND o.size IN ['1 employee', '2-10 employees']) OR (o.size = '1 employee' AND current_people > 1) OR (o.size = '2-10 employees' AND current_people > 10) OR (o.size = '11-50 employees' AND current_people > 50) RETURN o.id AS id, o.name AS name, 'size ' + o.size + ', current people in KB ' + toString(current_people) + ', sponsor ' + toString(o:Sponsor) AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "org_website_not_homepage",
        "Organization website is a careers page, shortener or tracking link",
        "medium",
        "LinkedIn's website field is often a campaign or careers link; a site would show it as the company's homepage.",
        _q(
            "MATCH (o:Organization) WHERE o.website IS NOT NULL AND (toLower(o.website) CONTAINS 'career' OR toLower(o.website) CONTAINS '/jobs' OR toLower(o.website) CONTAINS 'lifeat' OR toLower(o.website) CONTAINS 'travailler' OR toLower(o.website) CONTAINS '/publisher' OR o.website CONTAINS '?' OR any(h IN ['bit.ly/', '5tran.co/', 'goo.gle/', 'hubs.ly/', 'lnkd.in/', 'rbrk.co/', 'figma.bot/'] WHERE o.website CONTAINS h)) RETURN o.id AS id, o.name AS name, o.website AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "sponsor_missing_core_data",
        "Sponsor without website, GitHub account, logo or company facts",
        "medium",
        "Sponsors are the organizations a site shows most prominently; list each one missing a website, GitHub organization, logo, or the LinkedIn industry, size and headquarters.",
        _q(
            "MATCH (o:Sponsor) OPTIONAL MATCH (o)-[:HAS_ACCOUNT]->(g:GitHubAccount) WITH o, count(g) AS gh WITH o, [x IN [CASE WHEN o.website IS NULL THEN 'website' END, CASE WHEN gh = 0 THEN 'github' END, CASE WHEN o.logo_url IS NULL THEN 'logo' END, CASE WHEN o.industry IS NULL THEN 'industry' END, CASE WHEN o.size IS NULL THEN 'size' END, CASE WHEN o.headquarters IS NULL THEN 'headquarters' END] WHERE x IS NOT NULL] AS missing WHERE size(missing) > 0 RETURN o.id AS id, o.name AS name, o.sponsor_tier + ' sponsor; missing ' + reduce(s = '', x IN missing | s + x + ' ') AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "person_maintains_fork_or_archived",
        "Person 'maintains' a fork or an archived repository",
        "medium",
        "MAINTAINS comes from repositories the person's account owns, including pinned forks and archived projects; a profile would present a fork of someone else's project as the person's own work.",
        _q(
            "MATCH (p:Person)-[:MAINTAINS]->(r:Repository) WHERE r.fork = true OR r.archived = true RETURN r.id AS id, r.full_name AS name, p.id + (CASE WHEN r.fork = true THEN ' maintains a fork' ELSE '' END) + (CASE WHEN r.archived = true THEN ' maintains an archived repo, last push ' + substring(r.pushed_at, 0, 10) ELSE '' END) AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "package_unlinked",
        "Package with no repository or publisher link",
        "medium",
        "Gazetteer packages are kept without PUBLISHED_FROM and PUBLISHES edges even when the repository they name is in the KB.",
        _q(
            "MATCH (k:Package) WHERE NOT (k)-[:PUBLISHED_FROM]->(:Repository) OR NOT (:Entity)-[:PUBLISHES]->(k) OPTIONAL MATCH (r:Repository) WHERE toLower(k.repository_url) CONTAINS ('github.com/' + toLower(r.full_name) + '.git') OR toLower(k.repository_url) ENDS WITH ('github.com/' + toLower(r.full_name)) WITH k, collect(r.id) AS candidates RETURN k.id AS id, k.name AS name, 'repository_url ' + k.repository_url + (CASE WHEN size(candidates) > 0 THEN '; KB already has ' + reduce(s = '', c IN candidates | s + c + ' ') ELSE '; repository not in KB' END) AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "package_unlikely_release",
        "Package that is probably not a released library of its credited publisher",
        "medium",
        "The package rule accepts any registry entry that points back to the repository, so sample and workshop repositories, copies other people published (npm plugin-samples is credited to Figma), and Go modules with only a pseudo-version count as published packages. Review each before showing 'publishes'.",
        _q(
            "MATCH (pub:Entity)-[:PUBLISHES]->(k:Package)-[:PUBLISHED_FROM]->(r:Repository) WHERE any(w IN ['sample', 'example', 'template', 'workshop', 'demo', 'tutorial', 'starter', 'boilerplate'] WHERE toLower(r.full_name) CONTAINS w OR toLower(k.name) CONTAINS w) OR (k.ecosystem = 'go' AND k.latest_version STARTS WITH 'v0.0.0-') OR r.archived = true RETURN k.id AS id, k.name AS name, 'credited to ' + pub.id + '; ' + k.ecosystem + ' ' + k.latest_version + (CASE WHEN r.archived = true THEN '; repository archived' ELSE '' END) + '; registry description: ' + substring(coalesce(k.description, '-'), 0, 60) AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "org_without_profile_data",
        "Organization with no description, website, logo or accounts",
        "low",
        "Organizations a page can only show by name; most come from past-edition listings and are merge candidates for a better-populated record.",
        _q(
            "MATCH (o:Organization) WHERE o.description IS NULL AND o.website IS NULL AND o.logo_url IS NULL AND NOT (o)-[:HAS_ACCOUNT]->() OPTIONAL MATCH (p:Person)-[:AFFILIATED_WITH]->(o) OPTIONAL MATCH (s:Entity)-[:MENTIONS]->(o) WITH o, count(DISTINCT p) AS people, count(DISTINCT s) AS mentions RETURN o.id AS id, o.name AS name, 'people ' + toString(people) + ', mentioned by ' + toString(mentions) + ', roles ' + reduce(r = '', x IN o.roles | r + x + ' ') AS detail ORDER BY id LIMIT $limit"
        ),
        area="organizations",
    ),
    Check(
        "brief_bio_past_title_at_new_employer",
        "Brief bio gives a past listing's title at a newer employer",
        "blocker",
        "The person's job_title comes from a past edition's listing at one organization, LinkedIn or GitHub now places them at a different organization, and the brief bio says '<job_title> at/of <new organization>'. No source gives that title at the new employer, so the published bio states an unsupported fact. Organization-name variants (KPMG / KPMG US) are skipped; review each row against the account bios before rewriting.",
        _q(
            "MATCH (p:Person)-[old:AFFILIATED_WITH]->(o1:Organization) WHERE old.basis = 'event_listing' AND old.current = false AND old.title = p.job_title AND NOT (p)-[:AFFILIATED_WITH {current: true}]->(o1) MATCH (p)-[cur:AFFILIATED_WITH]->(o2:Organization) WHERE cur.current = true AND o2 <> o1 AND NOT toLower(o2.display_name) CONTAINS split(toLower(o1.display_name), ' ')[0] AND NOT toLower(o1.display_name) CONTAINS split(toLower(o2.display_name), ' ')[0] MATCH (pr:Profile)-[:DESCRIBES]->(p) WITH p, o1, o2, toLower(pr.doc) AS d, toLower(p.job_title) AS t, toLower(o2.display_name) AS n WHERE d CONTAINS (t + ' at ' + n) OR d CONTAINS (t + ' at the ' + n) OR d CONTAINS (t + ' of ' + n) RETURN DISTINCT p.id AS id, p.name AS name, p.job_title + ' was listed at ' + o1.display_name + '; brief bio puts it at ' + o2.display_name AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "past_title_paired_with_new_employer",
        "Title from a past listing, current employer is different",
        "medium",
        "job_title belongs to a past listing's organization while the current affiliation is elsewhere. Any page that prints job_title next to the current employer (or a bio built from both) states a wrong fact. Use listed_for, or a current_titles-style field, not job_title.",
        _q(
            "MATCH (p:Person)-[old:AFFILIATED_WITH]->(o1:Organization) WHERE old.basis = 'event_listing' AND old.current = false AND old.title = p.job_title AND NOT (p)-[:AFFILIATED_WITH {current: true}]->(o1) MATCH (p)-[cur:AFFILIATED_WITH]->(o2:Organization) WHERE cur.current = true AND o2 <> o1 WITH p, o1, collect(DISTINCT o2.display_name) AS now RETURN p.id AS id, p.name AS name, p.job_title + ' @ ' + o1.display_name + ' (past listing); current: ' + reduce(s = '', n IN now | s + n + ' ') AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "possible_split_person",
        "Two people who may be one (same family name, one given name extends the other)",
        "high",
        "Pairs of Person nodes with the same family name where one given name is a prefix of the other (Alex / Alexander). Confirm against the RainFocus userRef in each person's sources, then merge with curation names.",
        _q(
            "MATCH (a:Person), (b:Person) WHERE a.id < b.id AND a.family_name IS NOT NULL AND toLower(a.family_name) = toLower(b.family_name) AND a.given_name <> b.given_name AND (toLower(b.given_name) STARTS WITH toLower(a.given_name) OR toLower(a.given_name) STARTS WITH toLower(b.given_name)) RETURN a.id AS id, a.name AS name, 'may be the same person as ' + b.id + ' (' + b.name + ')' AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "listed_account_created_after_listing",
        "Event-listed account created after the edition that listed it",
        "high",
        "A social account tied to a person only by a past catalog whose creation date is later than that catalog's year: the handle was re-registered by someone else (for example a broken-link hijack), so the person links to a stranger's account.",
        _q(
            "MATCH (p:Person)-[:HAS_ACCOUNT]->(a:SocialAccount) WHERE a.link_basis = ['event_listing'] AND a.created_at IS NOT NULL WITH p, a, CASE WHEN a.doc CONTAINS 'raw/rainfocus/sessions.json' THEN 2026 WHEN a.doc CONTAINS 'editions/universe25' THEN 2025 WHEN a.doc CONTAINS 'editions/universe24' THEN 2024 WHEN a.doc CONTAINS 'editions/universe23' THEN 2023 ELSE NULL END AS listed WHERE listed IS NOT NULL AND toInteger(left(a.created_at, 4)) > listed RETURN a.id AS id, p.name AS name, 'listed in ' + toString(listed) + ' catalog; account created ' + a.created_at + '; followers ' + toString(coalesce(a.followers, 0)) AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "malformed_or_email_link",
        "Account or website built from a malformed value",
        "high",
        "Website URLs that contain '@' (an email address read as a URL) and accounts whose handle is one or two characters (catalog placeholders such as 'M/A' or a bare 'in/'), which link to someone else's page.",
        _q(
            "MATCH (p:Person)-[:HAS_WEBSITE|HAS_ACCOUNT]->(x) WHERE (x:Website AND x.url CONTAINS '@' AND NOT x.url CONTAINS '/@') OR (x:SocialAccount AND x.platform <> 'mastodon' AND size(last(split(x.handle, '/'))) <= 2) RETURN x.id AS id, p.name AS name, 'url ' + x.url AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "personal_email_in_text",
        "Personal email address in stored profile text",
        "medium",
        "Person-owned accounts, websites, people or profiles whose stored payload contains a webmail or mailto address (usually copied from a GitHub profile README). Decide whether to redact before publishing kb/ or _search/.",
        _q(
            "MATCH (x) WHERE (x:GitHubAccount OR x:SocialAccount OR x:Website OR x:Person OR x:Profile) AND (x.doc CONTAINS '@gmail.com' OR x.doc CONTAINS '@rocketmail.com' OR x.doc CONTAINS '@proton.me' OR x.doc CONTAINS '@yahoo.' OR x.doc CONTAINS '@hotmail.' OR x.doc CONTAINS '@outlook.' OR x.doc CONTAINS '@icloud.com' OR x.doc CONTAINS '@tec.mx' OR x.doc CONTAINS 'mailto:') OPTIONAL MATCH (owner:Person)-[:HAS_ACCOUNT|HAS_WEBSITE]->(x) WITH x, owner WHERE x:Person OR x:Profile OR owner IS NOT NULL RETURN x.id AS id, coalesce(owner.name, x.display_name) AS name, x.entity_kind + ' payload contains an email address' AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "rel_me_only_account_on_person",
        "Account tied to a person only by a homepage rel=me link",
        "medium",
        "Accounts that reach a person only through rel=me or plain links on a homepage. When that homepage is really a project, employer or podcast-network site (home-assistant.io, relay.fm, fly.io), its organization's accounts become the person's. Review each and add rejected_links or type the site as company.",
        _q(
            "MATCH (p:Person)-[:HAS_ACCOUNT]->(a:SocialAccount) WHERE 'website_rel_me' IN a.link_basis AND all(b IN a.link_basis WHERE b IN ['website_rel_me', 'website_link']) RETURN a.id AS id, p.name AS name, 'only via homepage links: ' + a.url AS detail ORDER BY name, id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "employer_site_typed_personal",
        "Employer website typed as the person's personal site",
        "medium",
        "A Website of kind personal whose host equals the website host of an organization the person is affiliated with. It should be kind company, so its rel=me links only corroborate and bio bundles leave it out.",
        _q(
            "MATCH (p:Person)-[:HAS_WEBSITE]->(w:Website), (p)-[:AFFILIATED_WITH]->(o:Organization) WHERE w.kind = 'personal' AND o.website IS NOT NULL WITH p, w, o, split(replace(replace(replace(toLower(w.url), 'https://', ''), 'http://', ''), 'www.', ''), '/')[0] AS wh, split(replace(replace(replace(toLower(o.website), 'https://', ''), 'http://', ''), 'www.', ''), '/')[0] AS oh WHERE wh = oh RETURN DISTINCT w.id AS id, p.name AS name, 'site host ' + wh + ' is the website of ' + o.display_name AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "several_current_employers",
        "Person with more than one current employer",
        "medium",
        "Current affiliations to two or more organizations. Often a duplicate organization (Pendo / Pendo.io, KPMG / KPMG US) or a LinkedIn side role that disagrees with the 2026 listing; a site should prefer event_listing, then curated, then the rest.",
        _q(
            "MATCH (p:Person)-[r:AFFILIATED_WITH]->(o:Organization) WHERE r.current = true WITH p, collect(DISTINCT o.display_name + ' (' + r.basis + ')') AS orgs, count(DISTINCT o) AS n WHERE n > 1 RETURN p.id AS id, p.name AS name, reduce(s = '', x IN orgs | s + x + '; ') AS detail ORDER BY id LIMIT $limit"
        ),
        area="people",
    ),
    Check(
        "overbroad_session_expertise",
        "Expertise inflated by over-tagged sessions or repeated topic labels",
        "medium",
        "People with more than 20 EXPERT_IN topic claims, or the same topic label claimed from several editions' term IDs. Catalog topics describe a session (some carry 24-31 topics), not the speaker; cap per-session topics and merge labels across editions before showing expertise.",
        _q(
            "MATCH (p:Person)-[:EXPERT_IN]->(t:Term) WITH p, count(t) AS n, count(DISTINCT toLower(t.display_name)) AS labels WHERE n > 20 OR labels < n RETURN p.id AS id, p.name AS name, toString(n) + ' expertise claims, ' + toString(labels) + ' distinct labels' AS detail ORDER BY n DESC, id LIMIT $limit"
        ),
        area="people",
    ),
)


def run_check(graph: Any, check: Check, *, count_only: bool = False) -> dict[str, Any]:
    """
    Run one check. `count` is the number of rows returned, at most `ROW_LIMIT`;
    `truncated` says there were more.
    """
    found = graph.ro_query(check.cypher, {"limit": ROW_LIMIT + 1}).result_set
    rows = found[:ROW_LIMIT]
    result: dict[str, Any] = {
        "name": check.name,
        "title": check.title,
        "severity": check.severity,
        "area": check.area,
        "description": check.description,
        "count": len(rows),
        "truncated": len(found) > ROW_LIMIT,
    }
    if not count_only:
        result["rows"] = [{"id": r[0], "name": r[1], "detail": r[2]} for r in rows]
    return result


## Tests


def test_truncated_only_when_rows_exceed_the_limit():
    from types import SimpleNamespace

    class Graph:
        def __init__(self, available: int):
            self.available: int = available

        def ro_query(self, cypher: str, params: dict[str, Any]) -> SimpleNamespace:
            assert cypher.endswith("LIMIT $limit")
            n = min(self.available, params["limit"])
            return SimpleNamespace(result_set=[[f"x:{i}", "n", "d"] for i in range(n)])

    check = CHECKS[0]
    exact = run_check(Graph(ROW_LIMIT), check)
    assert exact["count"] == ROW_LIMIT and not exact["truncated"]
    more = run_check(Graph(ROW_LIMIT + 5), check)
    assert more["count"] == len(more["rows"]) == ROW_LIMIT and more["truncated"]
