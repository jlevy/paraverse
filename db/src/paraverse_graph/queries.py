"""
The named query catalog: the only Cypher the HTTP API runs.

Clients (the web browser, the Swift client, the CLI) ask for a query by name with
typed parameters, never send Cypher. That keeps every query parameterized and
read-only, lets the catalog be reviewed and tested as a unit, and gives a stable
contract if the graph model changes underneath.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Any

from paraverse_graph.results import result_json

MAX_LIMIT = 500

# Nodes that connect almost everything, so paths through them say nothing about why
# two entities are related.
HUB_LABELS = ("Event", "Day", "Facet")

# Only people the event itself published are suggested. Self-reported and curated
# people appear in the graph but are never suggested.
PUBLISHED_BY_EVENT = "o.inclusion_basis = 'published_by_event'"


class QueryError(ValueError):
    """An unknown query name or an invalid parameter."""


def fulltext_query(text: str) -> str:
    """
    A full-text query for any user text: its words, each longer one prefix-matched so
    search-as-you-type works. Only word characters survive, so RediSearch syntax
    (quotes, parentheses, `-` negation, `|`, `@field:`, `%` fuzzy) can never make a
    query fail or change its meaning. Empty when `text` has no words.
    """
    words = re.findall(r"\w+", text)
    return " ".join(f"{w}*" if len(w) > 2 else w for w in words)


@dataclass(frozen=True)
class Param:
    name: str
    type: type[str] | type[int] = str
    default: str | int | None = None
    help: str = ""
    # Rewrites a string value before binding (search text, say); an empty result is rejected.
    clean: Callable[[str], str] | None = None

    @property
    def required(self) -> bool:
        return self.default is None


@dataclass(frozen=True)
class NamedQuery:
    name: str
    description: str
    cypher: str
    params: tuple[Param, ...] = field(default_factory=tuple)
    include_doc: bool = False

    def bind(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        unknown = set(raw) - {p.name for p in self.params}
        if unknown:
            raise QueryError(f"{self.name}: unknown parameters {sorted(unknown)}")
        bound: dict[str, Any] = {}
        for param in self.params:
            value = raw.get(param.name, param.default)
            if value is None:
                raise QueryError(f"{self.name}: missing parameter `{param.name}`")
            if param.type is int:
                try:
                    value = int(value)
                except (TypeError, ValueError) as e:
                    raise QueryError(f"{self.name}: `{param.name}` must be an integer") from e
                if param.name == "limit":
                    value = max(1, min(value, MAX_LIMIT))
            else:
                value = str(value)
                # FalkorDB cannot parse a NUL in a parameter.
                if "\x00" in value:
                    raise QueryError(f"{self.name}: `{param.name}` contains a NUL character")
                if param.clean:
                    value = param.clean(value)
                    if not value:
                        raise QueryError(f"{self.name}: `{param.name}` has nothing to search for")
            bound[param.name] = value
        return bound

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "params": [
                {"name": p.name, "type": p.type.__name__, "default": p.default, "help": p.help}
                for p in self.params
            ],
        }


def _q(text: str) -> str:
    return dedent(text).strip()


ID = Param("id", help="A typed entity ID, such as `person:april-leonard`.")


def _limit(default: int) -> Param:
    return Param("limit", int, default, f"Maximum rows, 1 to {MAX_LIMIT}.")


_HUB_FILTER = " OR ".join(f"x:{label}" for label in HUB_LABELS)

QUERIES: tuple[NamedQuery, ...] = (
    NamedQuery(
        "stats",
        "Entity counts by kind, and which KB build the graph was loaded from.",
        _q("""
            MATCH (n:Entity) WITH n.entity_kind AS kind, count(n) AS count
            OPTIONAL MATCH (m:GraphMeta)
            RETURN kind, count, m.kb_digest AS kb_digest, m.loaded_at AS loaded_at
            ORDER BY kind
            """),
    ),
    NamedQuery(
        "entity",
        "One entity with its full softschema payload (`doc`).",
        "MATCH (n:Entity {id: $id}) RETURN n",
        (ID,),
        include_doc=True,
    ),
    NamedQuery(
        "neighborhood",
        "An entity and everything one hop away, for a graph view.",
        _q("""
            MATCH (n:Entity {id: $id})
            OPTIONAL MATCH (n)-[r]-(m:Entity)
            RETURN n, r, m
            LIMIT $limit
            """),
        (ID, _limit(150)),
    ),
    NamedQuery(
        "search",
        "Full-text search across every entity's names, titles, bios and abstracts.",
        _q("""
            CALL db.idx.fulltext.queryNodes('Entity', $q) YIELD node, score
            RETURN node.id AS id, node.entity_kind AS kind, node.display_name AS name, score
            ORDER BY score DESC
            LIMIT $limit
            """),
        (
            Param(
                "q",
                help="Search text. Words are prefix-matched; search syntax is ignored.",
                clean=fulltext_query,
            ),
            _limit(25),
        ),
    ),
    NamedQuery(
        "days",
        "The event's days, for a schedule picker.",
        "MATCH (d:Day) RETURN d.id AS id, d.display_name AS name ORDER BY d.date",
    ),
    NamedQuery(
        "schedule",
        "Sessions on one day in start order, with speakers and the first room/type alphabetically when several are listed.",
        _q("""
            MATCH (s:Session)-[on:SCHEDULED_ON]->(:Day {id: $day})
            OPTIONAL MATCH (s)-[h:HELD_IN]->(room:Room) WHERE h.start = on.start
            OPTIONAL MATCH (p:Person)-[:PRESENTS]->(s)
            OPTIONAL MATCH (s)-[:HAS_TYPE]->(type:Term)
            RETURN on.start AS start, s.end AS end, s.id AS session, s.code AS code,
                   s.title AS title, min(type.label) AS type, min(room.name) AS room,
                   collect(DISTINCT p.display_name) AS speakers, on.start_epoch AS start_epoch
            ORDER BY start_epoch, code
            LIMIT $limit
            """),
        (Param("day", help="A day ID, such as `day:2026-10-28`."), _limit(MAX_LIMIT)),
    ),
    NamedQuery(
        "sessions_for_term",
        "Sessions tagged with a taxonomy term (topic, product, track, level, ...).",
        _q("""
            MATCH (s:Session)-[r]->(t:Term {id: $term})
            RETURN s.id AS session, s.code AS code, s.title AS title, s.start AS start,
                   type(r) AS facet
            ORDER BY s.start_epoch, code
            LIMIT $limit
            """),
        (Param("term", help="A term ID, such as `term:github-product/actions`."), _limit(100)),
    ),
    NamedQuery(
        "person_card",
        "A person with their sessions, affiliations, accounts and websites, for a graph view.",
        _q("""
            MATCH (p:Person {id: $id})
            OPTIONAL MATCH (p)-[r:PRESENTS|AFFILIATED_WITH|HAS_ACCOUNT|HAS_WEBSITE]->(x:Entity)
            RETURN p, r, x
            """),
        (ID,),
    ),
    NamedQuery(
        "person_repositories",
        "Repositories a person maintains or pins, by stars.",
        _q("""
            MATCH (p:Person {id: $id})-[m:MAINTAINS]->(r:Repository)
            RETURN r.id AS repository, r.full_name AS full_name, r.stars AS stars,
                   r.primary_language AS language, m.via AS via
            ORDER BY stars DESC, full_name
            LIMIT $limit
            """),
        (ID, _limit(25)),
    ),
    NamedQuery(
        "similar_people",
        "People the event published who share the most expertise and technologies with a person.",
        _q(f"""
            MATCH (p:Person {{id: $id}})-[:EXPERT_IN|WORKS_WITH]->(x)<-[:EXPERT_IN|WORKS_WITH]-(o:Person)
            WHERE o <> p AND {PUBLISHED_BY_EVENT}
            RETURN o.id AS person, o.display_name AS name, o.affiliation_label AS affiliation,
                   count(DISTINCT x) AS shared, collect(DISTINCT x.display_name) AS in_common
            ORDER BY shared DESC, name
            LIMIT $limit
            """),
        (ID, _limit(10)),
    ),
    NamedQuery(
        "connecting_paths",
        "Short paths that explain how two entities are connected, skipping hub nodes.",
        _q(f"""
            MATCH path = (a:Entity {{id: $a}})-[*1..3]-(b:Entity {{id: $b}})
            WHERE none(x IN nodes(path) WHERE {_HUB_FILTER})
            RETURN path, length(path) AS hops
            ORDER BY hops
            LIMIT $limit
            """),
        (
            Param("a", help="The first entity ID."),
            Param("b", help="The second entity ID."),
            _limit(10),
        ),
    ),
    NamedQuery(
        "organization_card",
        "An organization with its people, hosted sessions, software and accounts.",
        _q("""
            MATCH (o:Organization {id: $id})
            OPTIONAL MATCH (o)-[r:HOSTS|MAKES|HAS_ACCOUNT|SPONSORS]->(x:Entity)
            OPTIONAL MATCH (p:Person)-[a:AFFILIATED_WITH]->(o)
            RETURN o, r, x, a, p
            """),
        (ID,),
    ),
    NamedQuery(
        "sponsors",
        "Sponsors by their highest tier, with the distinct sessions each hosts.",
        _q("""
            MATCH (o:Sponsor)-[r:SPONSORS]->(:Event)
            WITH DISTINCT o, r.tier AS tier,
                 CASE r.tier WHEN 'platinum' THEN 0 WHEN 'gold' THEN 1 WHEN 'silver' THEN 2
                             WHEN 'bronze' THEN 3 ELSE 4 END AS rank
            ORDER BY rank, tier
            WITH o, collect(tier)[0] AS tier, min(rank) AS rank
            OPTIONAL MATCH (o)-[:HOSTS]->(s:Session)
            WITH o, tier, rank, count(DISTINCT s) AS hosted
            RETURN o.id AS organization, o.display_name AS name, tier, hosted
            ORDER BY rank, name
            """),
    ),
    NamedQuery(
        "top_software",
        "Software mentioned in sessions and bios or used by people, by distinct subjects.",
        _q("""
            MATCH (x)-[:MENTIONS|WORKS_WITH]->(s:Software)
            RETURN s.id AS software, s.display_name AS name, count(DISTINCT x) AS subjects
            ORDER BY subjects DESC, name
            LIMIT $limit
            """),
        (_limit(20),),
    ),
    NamedQuery(
        "taxonomy",
        "Every facet and term with its session count, for filter menus.",
        _q("""
            MATCH (f:Facet)-[:HAS_TERM]->(t:Term)
            OPTIONAL MATCH (s:Session)-[]->(t)
            RETURN f.id AS facet, f.display_name AS facet_name, t.id AS term,
                   t.display_name AS term_name, count(s) AS sessions
            ORDER BY facet, sessions DESC, term_name
            """),
    ),
)

CATALOG: dict[str, NamedQuery] = {q.name: q for q in QUERIES}


def run_query(graph: Any, name: str, raw_params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """
    Run a catalog query read-only and return its JSON form.

    falkordb-py decodes nodes and edges with label, property-key and relationship-type
    names it caches on the `Graph` object and never refreshes after a reload, so a
    long-lived process should pass a fresh `Graph` per call (the browser does).
    """
    query = CATALOG.get(name)
    if query is None:
        raise QueryError(f"unknown query `{name}`")
    result = graph.ro_query(query.cypher, query.bind(raw_params or {}))
    return {"query": name, **result_json(result, include_doc=query.include_doc)}


## Tests


def test_bind_clamps_and_validates():
    query = CATALOG["search"]
    assert query.bind({"q": "mcp", "limit": "9999"}) == {"q": "mcp*", "limit": MAX_LIMIT}
    for bad in (
        {},
        {"q": "x", "limit": "many"},
        {"q": "x", "nope": 1},
        {"q": '"(-'},
        {"q": "x\x00"},
    ):
        try:
            query.bind(bad)
        except QueryError:
            continue
        raise AssertionError(f"accepted {bad}")


def test_fulltext_query_strips_search_syntax():
    assert fulltext_query("supply chain!") == "supply* chain*"
    assert fulltext_query("copilot -") == "copilot*"
    assert fulltext_query("-copilot") == "copilot*"
    assert fulltext_query("co-pilot don't") == "co pilot* don* t"
    assert fulltext_query('@title:foo (a|b) "x" 50%') == "title* foo* a b x 50"
    assert fulltext_query('" ( | - % { } * ~ 😀') == ""
