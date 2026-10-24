"""
The knowledge base browser: a read-only JSON API and server-sent events over the
FalkorDB graph, plus the static front end in `paraverse_graph/web/`.

Everything is schema-driven. The loader stores each kind's field descriptions as a
`(:Schema)` node, so tables and record views are generic: any schema field can be a
column, references resolve to named entity chips, nested values become counted
summaries, and relationship columns come from the graph's own statistics.

Patterns (Host validation, compact JSON, bounded query parameters, the SSE fan-out
bus and heartbeat) follow metabrowser's server, reduced to what a read-only local
browser needs.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import math
import re
import threading
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Literal, override

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response, StreamingResponse
from starlette.responses import JSONResponse as _StarletteJSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from paraverse_graph.loader import events_channel
from paraverse_graph.mapping import ENTITY_LABEL, LABELS, META_LABEL, SCHEMA_LABEL, TYPED_REF
from paraverse_graph.queries import QueryError, fulltext_query, run_query
from paraverse_graph.review import CHECKS, SEVERITY_ORDER, run_check

log = logging.getLogger(__name__)

DEFAULT_LIMIT = 100
# Large enough that the browser shows every row of any current kind on one page (the
# largest, repositories, has about 1,300), small enough to stay fast to render.
MAX_LIMIT = 2000
RELATED_PER_TYPE = 50
CHIPS_PER_CELL = 3
HEARTBEAT_SECONDS = 15.0
CLIENT_QUEUE_SIZE = 64
# Below the embedded client's 5 s socket timeout, so FalkorDB stops a slow query and
# reports it before the connection gives up.
QUERY_TIMEOUT_MS = 4000
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})
# The only pub/sub event types forwarded to browsers, and the fields kept from them.
EVENT_TYPES = frozenset({"graph.loaded"})
_EVENT_FIELDS = ("kb_digest", "loaded_at")
SCALAR_TYPES = frozenset({"string", "integer", "number", "boolean"})
_MAX_INT = 2**63 - 1

# Sidebar grouping; kinds not listed here land in "Other".
KIND_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Program", ("event", "day", "session", "room", "venue", "experience")),
    ("People", ("person", "profile")),
    ("Organizations", ("organization",)),
    ("Accounts and web", ("github_account", "social_account", "website")),
    ("Code and software", ("repository", "package", "software")),
    ("Taxonomy", ("facet", "term")),
    ("Content", ("page",)),
)

# Default table columns. Plain names are payload fields or stored properties;
# `in:TYPE` and `out:TYPE` are relationship columns.
DEFAULT_COLUMNS: dict[str, tuple[str, ...]] = {
    "day": ("label", "date", "access"),
    "event": ("name", "edition", "start", "end", "venue"),
    "experience": ("name", "category", "schedule", "venue"),
    "facet": ("label", "multi_valued", "out:HAS_TERM"),
    "github_account": ("login", "name", "kind", "followers", "entity"),
    "organization": ("name", "roles", "sponsor_tier", "website", "in:AFFILIATED_WITH"),
    "package": ("name", "ecosystem", "latest_version", "software"),
    "page": ("title", "site", "url"),
    "person": ("name", "job_title", "affiliation_label", "inclusion_basis", "out:PRESENTS"),
    "profile": ("person", "headline", "location"),
    "repository": ("full_name", "stars", "primary_language", "owner", "archived"),
    "room": ("name", "venue", "capacity", "in:HELD_IN"),
    "session": ("code", "title", "start", "event", "in:PRESENTS"),
    "social_account": ("platform", "handle", "display_name", "followers", "owner"),
    "software": ("name", "kind", "vendor", "homepage"),
    "term": ("label", "session_count", "in:HAS_TERM"),
    "venue": ("name", "kind", "parent", "address"),
    "website": ("url", "kind", "title", "owner", "fetch_status"),
}


@dataclass(frozen=True)
class Computed:
    """The stored type of a property the loader derives beyond the payload."""

    type: Literal["string", "integer", "boolean"]
    is_list: bool = False


_STR, _INT, _BOOL = Computed("string"), Computed("integer"), Computed("boolean")
_STRS = Computed("string", is_list=True)

# Flattened properties the loader adds beyond the payload, offered as extra columns.
# Filters and sorts rely on these types; a test checks them against the stored values.
COMPUTED_COLUMNS: dict[str, dict[str, Computed]] = {
    "event": {"start_epoch": _INT, "end_epoch": _INT},
    "organization": {"sponsor_tier": _STR, "sponsor_booth": _STR, "sponsor_industries": _STRS},
    "person": {
        "participation_roles": _STRS,
        "participation_statuses": _STRS,
        "current_titles": _STRS,
    },
    "profile": {
        "expertise_labels": _STRS,
        "technology_labels": _STRS,
        "language_labels": _STRS,
        "interest_labels": _STRS,
    },
    "session": {
        "start": _STR,
        "end": _STR,
        "start_epoch": _INT,
        "slot_count": _INT,
        "capacity": _INT,
        "in_person": _BOOL,
        "virtual": _BOOL,
    },
}

IMAGE_FIELDS = ("photo_url", "logo_url", "image_url", "avatar_url")
CARD_FIELDS: dict[str, tuple[str, ...]] = {
    "organization": ("roles", "sponsor_tier", "industry", "website"),
    "person": ("job_title", "affiliation_label", "inclusion_basis", "participation_roles"),
    "repository": ("description", "stars", "primary_language"),
    "session": ("code", "start", "abstract"),
}
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REL_COLUMN = re.compile(r"^(in|out):([A-Z][A-Z0-9_]*)$")


class BadRequest(ValueError):
    """A request parameter is invalid; returned as 400 with the message."""


class Unavailable(RuntimeError):
    """The graph cannot serve requests (no `GraphMeta` node yet); returned as 503."""


class JSONResponse(_StarletteJSONResponse):
    """Compact UTF-8 JSON, as metabrowser renders it."""

    @override
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content, ensure_ascii=False, allow_nan=False, separators=(",", ":"), default=str
        ).encode("utf-8")


class NoCacheStaticFiles(StaticFiles):
    """
    Static files that browsers always revalidate. The front end is ES modules imported
    by unversioned URLs, so without this a browser keeps running stale modules.
    """

    @override
    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


class HostValidationMiddleware:
    """
    Reject requests whose Host is not a loopback name, so a DNS-rebinding page cannot
    read the API. Any port is allowed.
    """

    def __init__(self, app: ASGIApp, extra_hosts: frozenset[str] | None = None) -> None:
        self.app: ASGIApp = app
        self.allowed: frozenset[str] = ALLOWED_HOSTS | (extra_hosts or frozenset())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            host = dict(scope["headers"]).get(b"host", b"").decode("latin-1")
            hostname = host.rsplit(":", 1)[0] if not host.endswith("]") else host
            if hostname not in self.allowed:
                response = JSONResponse(
                    {"error": f"Host {host!r} is not permitted"}, status_code=421
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


@dataclass
class EventBus:
    """
    Fan-out of server events to SSE clients, one bounded queue per client. A client
    that falls behind is dropped; its browser reconnects and refetches.
    """

    clients: set[asyncio.Queue[dict[str, Any] | None]] = field(default_factory=set)
    loop: asyncio.AbstractEventLoop | None = None

    def attach(self) -> asyncio.Queue[dict[str, Any] | None]:
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=CLIENT_QUEUE_SIZE)
        self.clients.add(queue)
        return queue

    def detach(self, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        self.clients.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        for queue in list(self.clients):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop the backlog, so the resync is the next thing the client reads.
                self.clients.discard(queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(None)

    def publish_threadsafe(self, event: dict[str, Any]) -> None:
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.publish, event)


def encode_sse(event: dict[str, Any]) -> bytes:
    # JSON escapes newlines in `data`; a newline in the event name would start a new
    # SSE field, so it is removed.
    name = re.sub(r"[\r\n]", "", str(event.get("type") or "message"))
    payload = json.dumps(event, separators=(",", ":"), default=str)
    return f"event: {name}\ndata: {payload}\n\n".encode()


def parse_event(data: Any) -> dict[str, Any] | None:
    """
    The event in a pub/sub message, rebuilt from known fields, or `None` unless the
    message is a JSON object whose `type` is in `EVENT_TYPES`. Any client of the
    server can publish on the channel, so nothing else reaches browsers.
    """
    try:
        event = json.loads(data)
    except (TypeError, ValueError):
        return None
    if not isinstance(event, dict) or event.get("type") not in EVENT_TYPES:
        return None
    kept = {k: event[k] for k in _EVENT_FIELDS if isinstance(event.get(k), str)}
    return {"type": event["type"], **kept}


@dataclass(frozen=True)
class GraphReader:
    """
    Read-only queries for one request, each with a timeout. A reader wraps a fresh
    falkordb `Graph`: falkordb-py caches label, property-key and relationship-type
    names on the `Graph` object and does not notice a reload, so a long-lived one
    decodes nodes and edges with the previous build's names.
    """

    graph: Any
    timeout_ms: int

    def ro_query(
        self, q: str, params: dict[str, Any] | None = None, timeout: int | None = None
    ) -> Any:
        for value in (params or {}).values():
            # FalkorDB cannot parse a NUL in a parameter, and no ID or filter has one.
            if isinstance(value, str) and "\x00" in value:
                raise BadRequest("a request parameter contains a NUL character")
        return self.graph.ro_query(q, params, timeout=timeout or self.timeout_ms)


class GraphCatalog:
    """
    Cached schemas, metadata and review results for the current graph load.
    `invalidate()` runs when a `graph.loaded` event arrives, and `revalidate()` on
    requests that use the catalog catches a load whose event was missed.
    """

    def __init__(self, graph: Any, *, timeout_ms: int = QUERY_TIMEOUT_MS) -> None:
        self.graph: Any = graph
        self.timeout_ms: int = timeout_ms
        self._lock: threading.Lock = threading.Lock()
        self._review_lock: threading.Lock = threading.Lock()
        self._generation: int = 0
        self._stamp: list[Any] | None = None
        self._schemas: dict[str, dict[str, Any]] | None = None
        self._meta: dict[str, Any] | None = None
        self._review: dict[str, dict[str, Any]] | None = None

    def reader(self) -> GraphReader:
        fresh = type(self.graph)(self.graph.client, self.graph.name)
        return GraphReader(fresh, self.timeout_ms)

    def invalidate(self) -> None:
        with self._lock:
            self._generation += 1
            self._schemas = None
            self._meta = None
            self._review = None

    def revalidate(self) -> None:
        """
        Invalidate if `GraphMeta` shows a load this catalog has not seen. One small
        query; it covers a `graph.loaded` event that never arrived.
        """
        reader = self.reader()
        rows = reader.ro_query(f"MATCH (m:{META_LABEL}) RETURN m.kb_digest, m.loaded_at").result_set
        stamp = rows[0] if rows else None
        with self._lock:
            if stamp == self._stamp:
                return
            self._stamp = stamp
        self.invalidate()

    def schemas(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            if self._schemas is None:
                reader = self.reader()
                rows = reader.ro_query(
                    f"""
                    MATCH (s:{SCHEMA_LABEL})
                    RETURN s.kind, s.label, s.title, s.description, s.contract,
                           s.fields_json, s.defs_json
                    """
                ).result_set
                self._schemas = {
                    kind: {
                        "kind": kind,
                        "label": label,
                        "title": title,
                        "description": description,
                        "contract": contract,
                        "fields": json.loads(fields),
                        "defs": json.loads(defs),
                    }
                    for kind, label, title, description, contract, fields, defs in rows
                }
            return self._schemas

    def meta(self) -> dict[str, Any]:
        with self._lock:
            if self._meta is None:
                reader = self.reader()
                rows = reader.ro_query(
                    f"""
                    MATCH (m:{META_LABEL})
                    RETURN m.graph, m.dataset, m.kb_digest, m.loaded_at, m.stats_json,
                           m.rel_stats_json
                    """
                ).result_set
                if not rows:
                    raise Unavailable("the graph has no GraphMeta node; run `paraverse-graph load`")
                name, dataset, digest, loaded_at, stats, rel_stats = rows[0]
                self._meta = {
                    "graph": name,
                    "dataset": dataset,
                    "kb_digest": digest,
                    "loaded_at": loaded_at,
                    "stats": json.loads(stats),
                    "rel_stats": json.loads(rel_stats or "[]"),
                }
            return self._meta

    def schema(self, kind: str) -> dict[str, Any]:
        schema = self.schemas().get(kind)
        if schema is None:
            raise BadRequest(f"unknown kind `{kind}`")
        return schema

    def relationship_columns(self, kind: str) -> list[dict[str, Any]]:
        """
        One column per relationship type and direction, with the kinds at the other
        end. Types are read back from the graph and later interpolated into Cypher, so
        anything but a plain upper-case identifier is left out.
        """
        merged: dict[str, dict[str, Any]] = {}
        for stat in self.meta()["rel_stats"]:
            for direction, here, there in (("out", "from", "to"), ("in", "to", "from")):
                if stat[here] != kind:
                    continue
                name = f"{direction}:{stat['type']}"
                if not _REL_COLUMN.match(name):
                    log.warning("ignoring relationship type %r in GraphMeta", stat["type"])
                    continue
                column = merged.setdefault(
                    name,
                    {
                        "name": name,
                        "direction": direction,
                        "type": stat["type"],
                        "kinds": [],
                        "count": 0,
                    },
                )
                column["kinds"] = sorted({*column["kinds"], stat[there]})
                column["count"] += stat["count"]
        return sorted(merged.values(), key=lambda c: (c["direction"], c["type"]))

    def review(self) -> dict[str, dict[str, Any]]:
        """
        Every check's full result for the current load, keyed by name. The checks run
        once per load, not on every page view.
        """
        with self._review_lock:
            cached = self._review
            if cached is not None:
                return cached
            generation = self._generation
            reader = self.reader()
            results = {check.name: run_check(reader, check) for check in CHECKS}
            with self._lock:
                # Results computed across a reload belong to neither build.
                if generation == self._generation:
                    self._review = results
            return results


def create_app(
    graph: Any,
    *,
    extra_hosts: frozenset[str] | None = None,
    subscribe: Callable[[EventBus, GraphCatalog], Callable[[], None]] | None = None,
    query_timeout_ms: int = QUERY_TIMEOUT_MS,
) -> Starlette:
    """
    Build the browser app over one FalkorDB graph. `subscribe`, when given, starts a
    change listener on startup (see `redis_subscriber`) and returns a stop function.
    Every query runs through `GraphCatalog.reader()`, so it decodes with the current
    build's names and stops after `query_timeout_ms`.
    """
    catalog = GraphCatalog(graph, timeout_ms=query_timeout_ms)
    bus = EventBus()
    web = files("paraverse_graph") / "web"

    def meta(_: Request) -> Response:
        catalog.revalidate()
        info = catalog.meta()
        schemas = catalog.schemas()
        counts = info["stats"].get("nodes", {})
        kinds = {
            kind: {
                "kind": kind,
                "label": s["label"],
                "title": s["title"],
                "description": s["description"],
                "count": counts.get(kind, 0),
            }
            for kind, s in schemas.items()
            if counts.get(kind)
        }
        grouped = {k for _, ks in KIND_GROUPS for k in ks}
        groups = [
            {"title": title, "kinds": [kinds[k] for k in ks if k in kinds]}
            for title, ks in KIND_GROUPS
        ]
        other = [kinds[k] for k in sorted(kinds) if k not in grouped]
        if other:
            groups.append({"title": "Other", "kinds": other})
        return JSONResponse(
            {
                "graph": info["graph"],
                "dataset": info["dataset"],
                "kb_digest": info["kb_digest"],
                "loaded_at": info["loaded_at"],
                "node_total": sum(counts.values()),
                "edge_total": sum(info["stats"].get("edges", {}).values()),
                "groups": groups,
                "relationships": info["stats"].get("edges", {}),
            }
        )

    def schema(request: Request) -> Response:
        catalog.revalidate()
        kind = request.path_params["kind"]
        s = catalog.schema(kind)
        return JSONResponse(
            {
                **s,
                "computed": list(COMPUTED_COLUMNS.get(kind, {})),
                "default_columns": list(_default_columns(kind, s)),
                "relationships": catalog.relationship_columns(kind),
            }
        )

    def rows(request: Request) -> Response:
        catalog.revalidate()
        kind = request.path_params["kind"]
        params = request.query_params
        s = catalog.schema(kind)
        label = _label(kind)
        columns = _columns(params.get("cols"), kind, s, catalog)
        offset = _bounded_int(params.get("offset"), 0, 0, 10_000_000)
        limit = _bounded_int(params.get("limit"), DEFAULT_LIMIT, 1, MAX_LIMIT)
        where, args = _filters(params, kind, s, catalog)
        sort = params.get("sort") or "display_name"
        sort_prop, sort_key = _sort_key(sort, kind, s)
        order = "DESC" if params.get("order") == "desc" else "ASC"
        reader = catalog.reader()
        match = f"MATCH (n:{label}){where['rel']}"
        clause = f" WHERE {' AND '.join(where['conditions'])}" if where["conditions"] else ""
        total = reader.ro_query(f"{match}{clause} RETURN count(DISTINCT n)", args).result_set[0][0]
        fields = {f["name"]: f for f in s["fields"]}
        field_columns = [c for c in columns if c in fields]
        computed = [c for c in columns if c not in fields and c in COMPUTED_COLUMNS.get(kind, {})]
        # Only what the cells need: the payload (`doc`) only for schema-field columns,
        # and each computed column as its own value.
        returns = ["n.id", "n.display_name", "n.doc" if field_columns else "null"]
        returns += [f"n.{c}" for c in computed]
        page = reader.ro_query(
            f"""
            {match}{clause}
            WITH DISTINCT n
            ORDER BY {sort_prop} IS NULL, {sort_key} {order}, n.id
            SKIP $offset LIMIT $limit
            RETURN {", ".join(returns)}
            """,
            {**args, "offset": offset, "limit": limit},
        ).result_set
        ids = [row[0] for row in page]
        rel_cells = _relationship_cells(reader, ids, [c for c in columns if _REL_COLUMN.match(c)])
        docs = {row[0]: json.loads(row[2] or "{}") for row in page}
        values = {row[0]: dict(zip(computed, row[3:], strict=True)) for row in page}
        refs = _resolve_refs(
            reader,
            [docs[i].get(c) for i in ids for c in field_columns if fields[c].get("ref_kinds")],
        )
        out_rows = []
        for entity_id, name, *_ in page:
            cells: dict[str, Any] = {}
            for column in columns:
                if _REL_COLUMN.match(column):
                    cells[column] = rel_cells.get(column, {}).get(
                        entity_id, {"items": [], "count": 0}
                    )
                elif column in fields:
                    cells[column] = _cell(docs[entity_id].get(column), fields[column], refs)
                else:
                    cells[column] = _plain(values[entity_id][column])
            out_rows.append({"id": entity_id, "name": name, "cells": cells})
        return JSONResponse(
            {
                "kind": kind,
                "columns": columns,
                "total": total,
                "offset": offset,
                "limit": limit,
                "sort": sort,
                "order": order.lower(),
                "rows": out_rows,
            }
        )

    def entity(request: Request) -> Response:
        entity_id = request.path_params["id"]
        reader = catalog.reader()
        found = reader.ro_query(
            f"MATCH (n:{ENTITY_LABEL} {{id: $id}}) RETURN labels(n), properties(n)",
            {"id": entity_id},
        ).result_set
        if not found:
            return JSONResponse({"error": f"no entity `{entity_id}`"}, status_code=404)
        labels, props = found[0]
        doc = json.loads(props.get("doc") or "{}")
        relationships = {
            "out": _related(reader, entity_id, "out"),
            "in": _related(reader, entity_id, "in"),
        }
        return JSONResponse(
            {
                "id": entity_id,
                "kind": props.get("entity_kind"),
                "name": props.get("display_name"),
                "labels": labels,
                "kb_path": props.get("kb_path"),
                "doc": doc,
                "properties": {k: v for k, v in props.items() if k not in ("doc", "search_text")},
                "refs": _resolve_refs(reader, [doc]),
                "relationships": relationships,
            }
        )

    def card(request: Request) -> Response:
        catalog.revalidate()
        entity_id = request.path_params["id"]
        reader = catalog.reader()
        found = reader.ro_query(
            f"MATCH (n:{ENTITY_LABEL} {{id: $id}}) RETURN labels(n), properties(n)",
            {"id": entity_id},
        ).result_set
        if not found:
            return JSONResponse({"error": f"no entity `{entity_id}`"}, status_code=404)
        labels, props = found[0]
        kind = props.get("entity_kind", "")
        doc = json.loads(props.get("doc") or "{}")
        keys = CARD_FIELDS.get(kind) or tuple(DEFAULT_COLUMNS.get(kind, ()))[:4]
        details = []
        for key in keys:
            value = props.get(key, doc.get(key))
            if value in (None, "", []) or (isinstance(value, str) and TYPED_REF.match(value)):
                continue
            if isinstance(value, str) and len(value) > 220:
                value = value[:217].rstrip() + "…"
            details.append({"name": key, "value": _plain(value)})
        image = next((doc[f] for f in IMAGE_FIELDS if isinstance(doc.get(f), str)), None)
        return JSONResponse(
            {
                "id": entity_id,
                "kind": kind,
                "name": props.get("display_name"),
                "labels": labels,
                "image": image,
                "fields": details,
                "title": catalog.schemas().get(kind, {}).get("title", kind),
            }
        )

    def search(request: Request) -> Response:
        q = (request.query_params.get("q") or "").strip()
        if not q:
            raise BadRequest("missing `q`")
        limit = _bounded_int(request.query_params.get("limit"), 25, 1, 200)
        kinds = [k for k in (request.query_params.get("kinds") or "").split(",") if k]
        if kinds:
            catalog.revalidate()
        for kind in kinds:
            catalog.schema(kind)
        query = fulltext_query(q)
        # Text with no words (a lone quote while typing, say) matches nothing.
        if not query:
            return JSONResponse({"q": q, "hits": []})
        reader = catalog.reader()
        rows = reader.ro_query(
            f"""
            CALL db.idx.fulltext.queryNodes('{ENTITY_LABEL}', $q) YIELD node, score
            WHERE size($kinds) = 0 OR node.entity_kind IN $kinds
            RETURN node.id, node.entity_kind, node.display_name, node.search_text, score
            ORDER BY score DESC LIMIT $limit
            """,
            {"q": query, "kinds": kinds, "limit": limit},
        ).result_set
        return JSONResponse(
            {
                "q": q,
                "hits": [
                    {"id": i, "kind": k, "name": n, "snippet": _snippet(text, n), "score": score}
                    for i, k, n, text, score in rows
                ],
            }
        )

    def review_list(_: Request) -> Response:
        catalog.revalidate()
        results = catalog.review()
        ordered = sorted(CHECKS, key=lambda c: (SEVERITY_ORDER.index(c.severity), c.area, c.name))
        return JSONResponse(
            {"checks": [{k: v for k, v in results[c.name].items() if k != "rows"} for c in ordered]}
        )

    def review_check(request: Request) -> Response:
        catalog.revalidate()
        name = request.path_params["name"]
        if not any(c.name == name for c in CHECKS):
            raise BadRequest(f"unknown check `{name}`")
        return JSONResponse(catalog.review()[name])

    def named_query(request: Request) -> Response:
        try:
            body = run_query(
                catalog.reader(), request.path_params["name"], dict(request.query_params)
            )
        except QueryError as e:
            raise BadRequest(str(e)) from e
        return JSONResponse(body)

    async def hello() -> dict[str, Any]:
        try:
            info = await run_in_threadpool(catalog.meta)
        except Exception:
            # A stamp no client has makes the browser refetch `/api/meta`, which
            # reports the error; the stream itself stays up.
            log.exception("could not read the graph's load stamp for an SSE hello")
            info = {}
        return {
            "type": "hello",
            "kb_digest": info.get("kb_digest"),
            "loaded_at": info.get("loaded_at"),
        }

    async def events(request: Request) -> Response:
        # A graph that cannot be read is a JSON 503 before the stream starts, not a
        # stream that breaks after its headers. EventSource reconnects either way.
        await run_in_threadpool(catalog.meta)

        async def stream() -> AsyncIterator[bytes]:
            # Attach before reading the load stamp: a reload then either reaches the
            # queue or is already in the hello, so none slips between the two.
            queue = bus.attach()
            try:
                yield encode_sse(await hello())
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                    except TimeoutError:
                        yield b": heartbeat\n\n"
                        continue
                    if event is None:
                        yield encode_sse({"type": "resync"})
                        return
                    yield encode_sse(event)
            finally:
                bus.detach(queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    def index(_: Request) -> Response:
        html = (web / "index.html").read_text(encoding="utf-8")
        # Cache-bust assets by content, so a reload always picks up new files.
        for name in ("app.js", "style.css"):
            asset = web / name
            if asset.is_file():
                version = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
                html = html.replace(f'"/static/{name}"', f'"/static/{name}?v={version}"')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    # Every error is JSON `{"error": message}`; messages never carry FalkorDB internals.
    async def bad_request(_: Request, exc: Exception) -> Response:
        return JSONResponse({"error": str(exc)}, status_code=400)

    async def unavailable(_: Request, exc: Exception) -> Response:
        return JSONResponse({"error": str(exc)}, status_code=503)

    async def http_error(_: Request, exc: Exception) -> Response:
        if not isinstance(exc, HTTPException):
            raise exc
        if exc.status_code in (204, 304):
            return Response(status_code=exc.status_code, headers=exc.headers)
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    async def database_error(_: Request, exc: Exception) -> Response:
        status, message = _database_failure(exc, query_timeout_ms)
        return JSONResponse({"error": message}, status_code=status)

    async def server_error(_: Request, exc: Exception) -> Response:  # pyright: ignore[reportUnusedParameter]
        return JSONResponse({"error": "internal server error"}, status_code=500)

    class Lifespan:
        """Attach the event bus to the server's loop and run the change listener."""

        def __init__(self, _: Starlette) -> None:
            self.stop: Callable[[], None] | None = None

        async def __aenter__(self) -> None:
            bus.loop = asyncio.get_running_loop()
            self.stop = subscribe(bus, catalog) if subscribe else None

        async def __aexit__(self, *_: object) -> None:
            if self.stop:
                self.stop()

    app = Starlette(
        routes=[
            Route("/", index),
            Route("/api/meta", meta),
            Route("/api/schema/{kind}", schema),
            Route("/api/rows/{kind}", rows),
            Route("/api/entity/{id:path}", entity),
            Route("/api/card/{id:path}", card),
            Route("/api/search", search),
            Route("/api/review", review_list),
            Route("/api/review/{name}", review_check),
            Route("/api/query/{name}", named_query),
            Route("/api/events", events),
            Mount("/static", app=NoCacheStaticFiles(directory=str(web)), name="static"),
        ],
        middleware=[Middleware(HostValidationMiddleware, extra_hosts=extra_hosts)],
        exception_handlers={
            BadRequest: bad_request,
            Unavailable: unavailable,
            HTTPException: http_error,
            RedisError: database_error,
            # Starlette sends this one and then re-raises, so the server still logs it.
            Exception: server_error,
        },
        lifespan=Lifespan,
    )
    app.state.bus = bus
    app.state.catalog = catalog
    return app


def redis_subscriber(
    connection: Any, graph_name: str
) -> Callable[[EventBus, GraphCatalog], Callable[[], None]]:
    """
    Listen on the graph's pub/sub channel in a thread and forward each valid event to
    the bus, invalidating cached schemas first. The loader publishes after every swap.
    """

    def start(bus: EventBus, catalog: GraphCatalog) -> Callable[[], None]:
        stop = threading.Event()
        channel = events_channel(graph_name)
        pubsub = connection.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)

        def run() -> None:
            while not stop.is_set():
                try:
                    message = pubsub.get_message(timeout=1.0)
                except Exception:
                    log.exception("pub/sub listener failed")
                    stop.wait(2.0)
                    continue
                if message and message.get("type") == "message":
                    event = parse_event(message["data"])
                    if event is None:
                        log.warning("ignored a malformed message on %s", channel)
                        continue
                    catalog.invalidate()
                    bus.publish_threadsafe(event)

        thread = threading.Thread(target=run, name="paraverse-graph-events", daemon=True)
        thread.start()

        def close() -> None:
            stop.set()
            thread.join(timeout=3)
            with contextlib.suppress(Exception):
                pubsub.close()

        return close

    return start


def _default_columns(kind: str, s: dict[str, Any]) -> tuple[str, ...]:
    configured = DEFAULT_COLUMNS.get(kind)
    if configured:
        return configured
    names = [f["name"] for f in s["fields"] if f["name"] not in ("id", "sources")]
    return tuple(names[:5])


def _label(kind: str) -> str:
    """
    The Cypher label for a kind, from the code's own table rather than the label the
    graph's `Schema` node records, so no label read back from the graph is
    interpolated.
    """
    label = LABELS.get(kind)
    if label is None:
        raise BadRequest(f"unknown kind `{kind}`")
    return label


def _columns(raw: str | None, kind: str, s: dict[str, Any], catalog: GraphCatalog) -> list[str]:
    columns = [c for c in (raw or "").split(",") if c] or list(_default_columns(kind, s))
    allowed = {f["name"] for f in s["fields"]} | set(COMPUTED_COLUMNS.get(kind, {}))
    rel_allowed = {c["name"] for c in catalog.relationship_columns(kind)}
    for column in columns:
        if column not in allowed and column not in rel_allowed:
            raise BadRequest(f"unknown column `{column}` for `{kind}`")
    # A repeated column would repeat a RETURN item, which FalkorDB rejects.
    return list(dict.fromkeys(columns))


def _sort_key(sort: str, kind: str, s: dict[str, Any]) -> tuple[str, str]:
    """
    The property to sort by and the expression to order on. Strings sort without
    regard to case, so `apple` sorts beside `Apple` rather than after every capital.
    """
    types: dict[str, str] = {"display_name": "string", "id": "string"}
    types |= {
        f["name"]: f["type"]
        for f in s["fields"]
        if f["type"] in SCALAR_TYPES and not f.get("ref_kinds") and not f["list"]
    }
    # Computed columns last: the loader's derived value is the stored property.
    types |= {
        name: "list" if c.is_list else c.type for name, c in COMPUTED_COLUMNS.get(kind, {}).items()
    }
    if sort not in types or not _IDENTIFIER.match(sort):
        raise BadRequest(f"cannot sort `{kind}` by `{sort}`")
    if kind == "session" and sort in ("start", "end"):
        return f"n.{sort}_epoch", f"n.{sort}_epoch"
    prop = f"n.{sort}"
    return prop, f"toLower(toString({prop}))" if types[sort] == "string" else prop


def _filters(
    params: Any, kind: str, s: dict[str, Any], catalog: GraphCatalog
) -> tuple[dict[str, Any], dict[str, Any]]:
    conditions: list[str] = []
    args: dict[str, Any] = {}
    rel = ""
    q = (params.get("q") or "").strip()
    if q:
        conditions.append("toLower(n.search_text) CONTAINS $q")
        args["q"] = q.lower()
    fields = {f["name"]: f for f in s["fields"]}
    for index, (key, value) in enumerate(params.items()):
        if not key.startswith("f."):
            continue
        name = key[2:]
        if not _IDENTIFIER.match(name):
            raise BadRequest(f"cannot filter `{kind}` by `{name}`")
        value_type, is_list = _filter_type(name, kind, fields)
        parameter = f"f{index}"
        if is_list:
            conditions.append(f"${parameter} IN n.{name}")
        else:
            conditions.append(f"n.{name} = ${parameter}")
        args[parameter] = _typed(value, value_type)
    raw_rel = params.get("rel")
    if raw_rel:
        direction, _, rest = raw_rel.partition(":")
        rel_type, _, other = rest.partition(":")
        # Relationship columns hold only plain `in|out:TYPE` names, so a match here
        # makes `direction` and `rel_type` safe to interpolate.
        if (
            f"{direction}:{rel_type}" not in {c["name"] for c in catalog.relationship_columns(kind)}
            or not other
        ):
            raise BadRequest(f"invalid `rel` filter `{raw_rel}`; expected `in|out:TYPE:<id>`")
        arrow = f"-[:{rel_type}]->" if direction == "out" else f"<-[:{rel_type}]-"
        rel = f"{arrow}(:{ENTITY_LABEL} {{id: $rel_id}})"
        args["rel_id"] = other
    return {"conditions": conditions, "rel": rel}, args


def _filter_type(name: str, kind: str, fields: dict[str, dict[str, Any]]) -> tuple[str, bool]:
    """
    The stored type of a filterable property, and whether it holds a list. References
    and nested values are relationships and `doc`, not properties, so a filter on one
    is a 400 rather than an empty table.
    """
    computed = COMPUTED_COLUMNS.get(kind, {}).get(name)
    if computed is not None:
        return computed.type, computed.is_list
    info = fields.get(name)
    if info is None:
        raise BadRequest(f"cannot filter `{kind}` by `{name}`")
    if name == "id":
        return "string", False
    if info.get("ref_kinds") or info.get("def"):
        raise BadRequest(
            f"cannot filter `{kind}` by `{name}`: it is a reference or a nested value; "
            + "filter by a relationship with `rel=` instead"
        )
    if info["type"] not in SCALAR_TYPES:
        raise BadRequest(f"cannot filter `{kind}` by `{name}`")
    return info["type"], info["list"]


def _typed(value: str, value_type: str) -> Any:
    if value_type == "boolean":
        if value.lower() not in ("true", "false"):
            raise BadRequest(f"`{value}` is not a boolean; use `true` or `false`")
        return value.lower() == "true"
    if value_type == "integer":
        try:
            number = int(value)
        except ValueError as e:
            raise BadRequest(f"`{value}` is not an integer") from e
        if abs(number) > _MAX_INT:
            raise BadRequest(f"`{value}` is out of range")
        return number
    if value_type == "number":
        try:
            real = float(value)
        except ValueError as e:
            raise BadRequest(f"`{value}` is not a number") from e
        if not math.isfinite(real):
            raise BadRequest(f"`{value}` is not a finite number")
        return real
    return value


def _database_failure(exc: Exception, timeout_ms: int) -> tuple[int, str]:
    """
    The status and client message for a database error: 503 for conditions that
    pass (a timeout, no connection, no graph yet), 500 otherwise. Details stay in
    the server log.
    """
    text = str(exc)
    if text == "Query timed out":
        log.warning("query timed out after %d ms", timeout_ms)
        return 503, f"the query took longer than {timeout_ms} ms; try a narrower request"
    if isinstance(exc, RedisTimeoutError):
        log.warning("database did not answer: %s", text)
        return 503, "the graph database did not answer in time"
    if isinstance(exc, RedisConnectionError):
        log.warning("database unreachable: %s", text)
        return 503, "the graph database is not reachable"
    if "empty key" in text:
        return 503, "the graph is not loaded; run `paraverse-graph load`"
    if text.startswith("RediSearch: Syntax error"):
        return 400, "the search text could not be parsed"
    log.error("database error: %s", text, exc_info=exc)
    return 500, "database error"


def _bounded_int(raw: str | None, default: int, minimum: int, maximum: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as e:
        raise BadRequest(f"`{raw}` is not an integer") from e
    return max(minimum, min(value, maximum))


def _relationship_cells(
    reader: GraphReader, ids: list[str], columns: list[str]
) -> dict[str, dict[str, dict[str, Any]]]:
    cells: dict[str, dict[str, dict[str, Any]]] = {}
    for column in columns:
        match = _REL_COLUMN.match(column)
        if not match or not ids:
            continue
        direction, rel_type = match.groups()
        arrow = f"-[:{rel_type}]->" if direction == "out" else f"<-[:{rel_type}]-"
        rows = reader.ro_query(
            f"""
            MATCH (n:{ENTITY_LABEL}){arrow}(m:{ENTITY_LABEL})
            WHERE n.id IN $ids
            WITH n, m ORDER BY m.display_name
            RETURN n.id, count(m), collect([m.id, m.display_name, m.entity_kind])[0..{CHIPS_PER_CELL}]
            """,
            {"ids": ids},
        ).result_set
        cells[column] = {
            entity_id: {
                "count": count,
                "items": [{"id": i, "name": n, "kind": k} for i, n, k in items],
            }
            for entity_id, count, items in rows
        }
    return cells


def _related(reader: GraphReader, entity_id: str, direction: str) -> list[dict[str, Any]]:
    arrow = "-[r]->" if direction == "out" else "<-[r]-"
    rows = reader.ro_query(
        f"""
        MATCH (n:{ENTITY_LABEL} {{id: $id}}){arrow}(m:{ENTITY_LABEL})
        WITH type(r) AS t, r, m ORDER BY m.display_name
        RETURN t, count(m), count(DISTINCT m), collect([m.id, m.display_name, m.entity_kind, properties(r)])[0..{RELATED_PER_TYPE}]
        ORDER BY t
        """,
        {"id": entity_id},
    ).result_set
    # `count` is relationships; `distinct` is the entities they reach. They differ when
    # one entity is linked several times (an affiliation from several sources), and
    # `distinct` is what the related table's `rel=` filter returns.
    return [
        {
            "type": rel_type,
            "count": count,
            "distinct": distinct,
            "items": [{"id": i, "name": n, "kind": k, "edge": e} for i, n, k, e in items],
        }
        for rel_type, count, distinct, items in rows
    ]


def _collect_refs(value: Any, found: set[str]) -> None:
    if isinstance(value, str):
        if TYPED_REF.match(value):
            found.add(value)
    elif isinstance(value, list):
        for item in value:
            _collect_refs(item, found)
    elif isinstance(value, dict):
        for item in value.values():
            _collect_refs(item, found)


def _resolve_refs(reader: GraphReader, values: list[Any]) -> dict[str, dict[str, Any]]:
    """
    Names and kinds for every typed reference found anywhere in `values`. References
    to entities with no node (an organization with no artifact) map to `None` names.
    """
    found: set[str] = set()
    for value in values:
        _collect_refs(value, found)
    if not found:
        return {}
    rows = reader.ro_query(
        f"MATCH (m:{ENTITY_LABEL}) WHERE m.id IN $ids RETURN m.id, m.display_name, m.entity_kind",
        {"ids": sorted(found)},
    ).result_set
    resolved = {i: {"name": n, "kind": k} for i, n, k in rows}
    return {ref: resolved.get(ref, {"name": None, "kind": None}) for ref in sorted(found)}


def _cell(value: Any, info: dict[str, Any], refs: dict[str, dict[str, Any]]) -> Any:
    """
    A table cell for one schema field: plain values as is, references as entity chips,
    nested objects as a counted summary (the record view shows them in full).
    """
    if value is None:
        return None
    if info.get("ref_kinds"):
        values = value if isinstance(value, list) else [value]
        chips = [{"id": v, **refs.get(v, {"name": None, "kind": None})} for v in values]
        return {"refs": chips}
    if info.get("def"):
        items = value if isinstance(value, list) else [value]
        return {
            "nested": info["def"],
            "count": len(items),
            "preview": _preview(items[0]) if items else "",
        }
    return _plain(value)


def _preview(item: Any) -> str:
    if isinstance(item, dict):
        parts = [
            str(v)
            for v in item.values()
            if isinstance(v, str | int | float) and not isinstance(v, bool)
        ]
        return " · ".join(parts[:3])[:120]
    return str(item)[:120]


def _plain(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return str(value)


def _snippet(text: str | None, name: str | None) -> str:
    body = (text or "").replace(name or "", "", 1).strip()
    return re.sub(r"\s+", " ", body)[:160]


## Tests


def test_cells():
    refs = {"org:a": {"name": "A", "kind": "organization"}}
    assert _cell("org:a", {"ref_kinds": ["organization"]}, refs) == {
        "refs": [{"id": "org:a", "name": "A", "kind": "organization"}]
    }
    nested = _cell([{"start": "x", "room": "room:a"}], {"def": "TimeSlot"}, {})
    assert nested["count"] == 1 and nested["nested"] == "TimeSlot"


def test_typed_filter_values():
    assert _typed("TRUE", "boolean") is True and _typed("false", "boolean") is False
    assert _typed("-3", "integer") == -3 and _typed("2.5", "number") == 2.5
    for value, value_type in (
        ("banana", "boolean"),
        ("1", "boolean"),
        ("two", "integer"),
        (str(2**63), "integer"),
        ("nan", "number"),
        ("inf", "number"),
    ):
        try:
            _typed(value, value_type)
        except BadRequest:
            continue
        raise AssertionError(f"accepted {value!r} as {value_type}")


def test_pubsub_events_are_validated():
    loaded = json.dumps({"type": "graph.loaded", "kb_digest": "d", "loaded_at": "t", "x": 1})
    assert parse_event(loaded) == {"type": "graph.loaded", "kb_digest": "d", "loaded_at": "t"}
    for bad in ("[1, 2]", "nope", '"graph.loaded"', '{"type": "spoofed"}', None, "{}"):
        assert parse_event(bad) is None
    injected = encode_sse({"type": "graph.loaded\ndata: {}\n\nevent: x", "a": "b\nc"})
    assert injected.count(b"\n") == 3 and injected.endswith(b"\n\n")


def test_overflow_sends_resync_first():
    bus = EventBus()
    queue = bus.attach()
    for i in range(CLIENT_QUEUE_SIZE + 1):
        bus.publish({"type": "graph.loaded", "n": i})
    assert queue.get_nowait() is None and queue.empty() and queue not in bus.clients
