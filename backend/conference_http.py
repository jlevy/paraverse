"""Public HTTPS page transport, adapted from Universe fetch_safety at a823679."""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import partial
from typing import Any


MAX_REDIRECTS = 5
REDIRECT_STATUS = {301, 302, 303, 307, 308}
PUBLIC_REDIRECT_HEADERS = {"user-agent", "accept", "accept-language"}


class UnsafeDestination(ValueError):
    """A URL, DNS answer, or redirect would leave the public HTTP boundary."""


def _public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        # Translation/tunnel addresses must not hide an internal IPv4 destination.
        if ip.ipv4_mapped:
            return _public_address(str(ip.ipv4_mapped))
        if ip.sixtofour and not _public_address(str(ip.sixtofour)):
            return False
        if ip.teredo:
            return all(_public_address(str(part)) for part in ip.teredo)
        if ip in ipaddress.ip_network("64:ff9b::/96"):
            return _public_address(str(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)))
    return True


def _parse_url(url: str) -> urllib.parse.SplitResult:
    if "\\" in url or any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise UnsafeDestination("URL contains whitespace or control characters")
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
        port = parts.port
        if (parts.scheme != "https" or not host
                or parts.username is not None or parts.password is not None
                or (port is not None and port != 443)):
            raise ValueError("expected public HTTPS on port 443 without credentials")
        if "%" in host:
            raise ValueError("encoded hosts and scoped addresses are not allowed")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            host = host.encode("idna").decode("ascii").lower().rstrip(".")
            if (not host or host == "localhost" or host.endswith((".localhost", ".local"))
                    or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                           for label in host.split("."))):
                raise ValueError("invalid or local hostname") from None
        else:
            if not _public_address(host):
                raise ValueError("non-public IP address")
    except (ValueError, UnicodeError) as error:
        raise UnsafeDestination(f"unsafe HTTP destination: {error}") from error
    return parts


def validate_public_url(url: str) -> str:
    """Validate public HTTPS, including all current DNS answers."""
    _resolve(url)
    return url


@dataclass(frozen=True)
class _Destination:
    addresses: tuple[tuple[Any, ...], ...]


def _resolve(url: str) -> _Destination:
    parts = _parse_url(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except OSError as error:
        # Keep Fetcher.request's existing transient-network retry behavior.
        raise urllib.error.URLError(error) from error
    if not addresses or any(not _public_address(str(info[4][0])) for info in addresses):
        raise UnsafeDestination("hostname resolves to a non-public address")
    return _Destination(tuple(addresses))


def _connect(destination: _Destination, _address: Any, timeout: float,
             source_address: Any = None) -> socket.socket:
    last_error: OSError | None = None
    for family, socktype, proto, _canonname, sockaddr in destination.addresses:
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(timeout)
            if source_address is not None:
                sock.bind(source_address)
            # Use the checked sockaddr directly: a second DNS lookup could rebind it.
            sock.connect(sockaddr)
            return sock
        except OSError as error:
            sock.close()
            last_error = error
    if last_error is not None:
        raise last_error
    raise UnsafeDestination("hostname has no public addresses")


def _connection(destination: _Destination, connection_type: type[http.client.HTTPConnection],
                host: str, **kwargs: Any) -> http.client.HTTPConnection:
    connection = connection_type(host, **kwargs)
    # Keep the hostname on HTTPConnection for Host, TLS SNI and certificate checking;
    # replace only its socket factory, which otherwise performs another DNS lookup.
    connection._create_connection = partial(  # pyright: ignore[reportAttributeAccessIssue]
        _connect, destination)
    return connection


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, destination: _Destination) -> None:
        self.context = ssl.create_default_context()
        self.context.set_alpn_protocols(["http/1.1"])
        super().__init__(context=self.context)
        self.destination = destination

    def https_open(self, req: Any) -> Any:
        factory = partial(_connection, self.destination, http.client.HTTPSConnection)
        return self.do_open(factory, req, context=self.context)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


def _open_once(request: urllib.request.Request, destination: _Destination, timeout: float) -> Any:
    # A proxy would resolve/connect elsewhere, outside the checked socket boundary.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(),
                                        _PublicHTTPSHandler(destination))
    return opener.open(request, timeout=timeout)


def open_public_url(request: urllib.request.Request, *, timeout: float) -> Any:
    """Fetch public HTTPS pages with checked, pinned hops and no credential forwarding."""
    if request.data is not None or request.get_method() not in {"GET", "HEAD"}:
        raise UnsafeDestination("conference page retrieval requires GET or HEAD without a body")
    # These page fetches never need authentication, cookies, or caller-supplied Host.
    headers = {name: value for name, value in request.header_items()
               if name.lower() in PUBLIC_REDIRECT_HEADERS}
    request = urllib.request.Request(request.full_url, headers=headers,
                                     method=request.get_method())
    for redirects in range(MAX_REDIRECTS + 1):
        destination = _resolve(request.full_url)
        try:
            return _open_once(request, destination, timeout)
        except urllib.error.HTTPError as error:
            location = error.headers.get("Location") if error.headers else None
            if error.code not in REDIRECT_STATUS or not location:
                raise
            try:
                if redirects == MAX_REDIRECTS:
                    raise UnsafeDestination("too many redirects") from error
                target = urllib.parse.urljoin(request.full_url, location)
                # Every target is parsed, resolved and pinned on the next loop;
                # neither urllib redirects nor ambient proxies can bypass it.
                request = urllib.request.Request(target, headers=headers,
                                                 method=request.get_method())
            finally:
                error.close()
    raise AssertionError("unreachable")
