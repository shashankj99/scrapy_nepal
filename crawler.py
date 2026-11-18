"""Bounded HTTP fetching for configured public HTTPS sources."""

from contextlib import closing
import http.client
import ipaddress
import re
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

AGENT = "NepalDatasetImporter"
MAX_BYTES = 2 * 1024 * 1024
REDIRECTS = {301, 302, 303, 307, 308}


class ImportFailure(Exception):
    """A fixed error code that is safe to print and persist."""

    def __init__(self, code, rejected=None):
        super().__init__(code)
        self.code = code
        self.rejected = rejected


def public_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        raise ImportFailure("invalid_url")
    if any(ord(char) <= 32 or ord(char) >= 127 or char == "\\" for char in url):
        raise ImportFailure("invalid_url")
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or not re.fullmatch(r"[a-z0-9.-]+", parts.hostname)
            or parts.port not in (None, 443)
            or parts.username is not None
            or parts.fragment
        ):
            raise ImportFailure("invalid_url")
    except ValueError:
        raise ImportFailure("invalid_url") from None
    return parts


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=8, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def resolve(host):
    addresses = [
        ipaddress.ip_address(item[4][0])
        for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    ]
    if not addresses or any(
        not addr.is_global or addr.is_multicast or getattr(addr, "ipv4_mapped", None)
        for addr in addresses
    ):
        raise ImportFailure("nonpublic_destination")
    return str(addresses[0])


class Fetcher:
    def __init__(self, hosts):
        self.hosts = frozenset(hosts)
        self.robots = {}
        self.last_request = {}

    def fetch(self, url, *, robots=False):
        for _ in range(4):
            parts = public_url(url)
            host = parts.hostname
            if host not in self.hosts:
                raise ImportFailure("unapproved_host")
            if not robots:
                self.check_robots(parts, url)
            status, location, body = self.request(parts)
            if status in REDIRECTS and location:
                url = urljoin(url, location)
                continue
            if status == 200 or (robots and status in (404, 410)):
                return body, url
            raise ImportFailure("source_http_error")
        raise ImportFailure("too_many_redirects")

    def check_robots(self, parts, url):
        host = parts.hostname
        if host not in self.robots:
            robots_url = f"https://{host}/robots.txt"
            rules = RobotFileParser(robots_url)
            body, _ = self.fetch(robots_url, robots=True)
            rules.parse(body.decode("utf-8", "replace").splitlines())
            self.robots[host] = rules
        if not self.robots[host].can_fetch(AGENT, url):
            raise ImportFailure("robots_disallowed")

    def request(self, parts):
        host = parts.hostname
        rules = self.robots.get(host)
        delay = max(1, rules.crawl_delay(AGENT) or 0) if rules else 1
        if delay > 30:
            raise ImportFailure("crawl_delay_exceeds_limit")
        time.sleep(max(0, self.last_request.get(host, 0) + delay - time.monotonic()))
        self.last_request[host] = time.monotonic()
        target = parts.path or "/"
        if parts.query:
            target += "?" + parts.query
        try:
            connection = PinnedHTTPS(host, resolve(host))
            with closing(connection):
                connection.request("GET", target, headers={"User-Agent": AGENT})
                response = connection.getresponse()
                if response.status != 200:
                    return response.status, response.getheader("Location"), b""
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise ImportFailure("unsupported_content_encoding")
                expected = response.length
                if expected is not None and expected > MAX_BYTES:
                    raise ImportFailure("source_too_large")
                body = bytearray()
                deadline = time.monotonic() + 20
                while len(body) <= MAX_BYTES:
                    if time.monotonic() >= deadline:
                        raise ImportFailure("source_timeout")
                    chunk = response.read1(min(65536, MAX_BYTES + 1 - len(body)))
                    if not chunk:
                        if expected is not None and len(body) != expected:
                            raise ImportFailure("incomplete_response")
                        return response.status, None, bytes(body)
                    body.extend(chunk)
                raise ImportFailure("source_too_large")
        except (OSError, http.client.HTTPException):
            raise ImportFailure("source_connection_error") from None
