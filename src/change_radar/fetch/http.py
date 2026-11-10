"""Polite HTTP access: identifies itself, obeys robots.txt and limits request rate."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from collections.abc import Callable
from http.client import HTTPException
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from change_radar import __version__

USER_AGENT = f"change-radar/{__version__} (+https://github.com/KaparthyReddy/change-radar)"
DEFAULT_TIMEOUT = 20.0
DEFAULT_MAX_BYTES = 5_000_000
DEFAULT_MIN_INTERVAL = 2.0

Fetcher = Callable[[str], bytes]


class FetchError(Exception):
    """Raised when a document cannot be fetched, or may not be fetched."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def http_get(
    url: str,
    *,
    user_agent: str = USER_AGENT,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> bytes:
    """Fetch one URL over HTTPS and return the body. Refuses very large responses."""
    if not url.startswith("https://"):
        raise FetchError(f"only https URLs are allowed: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body: bytes = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} for {url}", status=exc.code) from exc
    except (OSError, HTTPException) as exc:
        raise FetchError(f"could not fetch {url}: {exc}") from exc
    if len(body) > max_bytes:
        raise FetchError(f"response from {url} is larger than {max_bytes} bytes")
    return body


class PoliteFetcher:
    """Fetches URLs while obeying robots.txt and a minimum delay per host."""

    def __init__(
        self,
        *,
        user_agent: str = USER_AGENT,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        respect_robots: bool = True,
        get: Fetcher | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._user_agent = user_agent
        self._min_interval = min_interval
        self._respect_robots = respect_robots
        self._get: Fetcher = get or (lambda url: http_get(url, user_agent=user_agent))
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}

    def __call__(self, url: str) -> bytes:
        parts = urlsplit(url)
        if self._respect_robots and not self._allowed(url, parts.scheme, parts.netloc):
            raise FetchError(f"robots.txt does not allow fetching {url}")
        return self._polite_get(url, parts.netloc)

    def _polite_get(self, url: str, host: str) -> bytes:
        last = self._last_request.get(host)
        if last is not None:
            remaining = self._min_interval - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        try:
            return self._get(url)
        finally:
            self._last_request[host] = self._clock()

    def _allowed(self, url: str, scheme: str, host: str) -> bool:
        parser = self._robots.get(host)
        if parser is None:
            parser = self._load_robots(scheme, host)
            self._robots[host] = parser
        return parser.can_fetch(self._user_agent, url)

    def _load_robots(self, scheme: str, host: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            body = self._polite_get(f"{scheme}://{host}/robots.txt", host)
        except FetchError as exc:
            if exc.status != 404:
                raise FetchError(f"could not read robots.txt for {host}: {exc}") from exc
            parser.parse(["User-agent: *", "Allow: /"])
        else:
            parser.parse(body.decode("utf-8", errors="replace").splitlines())
        parser.modified()
        return parser
