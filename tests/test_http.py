import pytest

from change_radar.fetch.http import FetchError, PoliteFetcher, http_get

ROBOTS = b"User-agent: *\nDisallow: /private/\n"


class FakeWeb:
    def __init__(self, pages: dict[str, bytes | FetchError]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        result = self.pages[url]
        if isinstance(result, FetchError):
            raise result
        return result


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_http_get_refuses_non_https() -> None:
    with pytest.raises(FetchError, match="https"):
        http_get("http://example.com/feed.xml")


def test_waits_between_requests_to_the_same_host() -> None:
    web = FakeWeb({"https://example.com/a": b"a", "https://example.com/b": b"b"})
    clock = FakeClock()
    fetcher = PoliteFetcher(
        min_interval=2.0, respect_robots=False, get=web, sleep=clock.sleep, clock=clock
    )
    fetcher("https://example.com/a")
    fetcher("https://example.com/b")
    assert clock.slept == [2.0]


def test_does_not_wait_between_different_hosts() -> None:
    web = FakeWeb({"https://one.example/a": b"a", "https://two.example/b": b"b"})
    clock = FakeClock()
    fetcher = PoliteFetcher(
        min_interval=2.0, respect_robots=False, get=web, sleep=clock.sleep, clock=clock
    )
    fetcher("https://one.example/a")
    fetcher("https://two.example/b")
    assert clock.slept == []


def test_does_not_wait_when_enough_time_has_passed() -> None:
    web = FakeWeb({"https://example.com/a": b"a", "https://example.com/b": b"b"})
    clock = FakeClock()
    fetcher = PoliteFetcher(
        min_interval=2.0, respect_robots=False, get=web, sleep=clock.sleep, clock=clock
    )
    fetcher("https://example.com/a")
    clock.now = 10.0
    fetcher("https://example.com/b")
    assert clock.slept == []


def test_robots_disallow_blocks_the_fetch() -> None:
    web = FakeWeb(
        {
            "https://example.com/robots.txt": ROBOTS,
            "https://example.com/public/a": b"ok",
            "https://example.com/private/a": b"secret",
        }
    )
    clock = FakeClock()
    fetcher = PoliteFetcher(min_interval=0, get=web, sleep=clock.sleep, clock=clock)
    assert fetcher("https://example.com/public/a") == b"ok"
    with pytest.raises(FetchError, match="robots.txt"):
        fetcher("https://example.com/private/a")
    assert "https://example.com/private/a" not in web.calls


def test_robots_is_read_once_per_host() -> None:
    web = FakeWeb(
        {
            "https://example.com/robots.txt": ROBOTS,
            "https://example.com/a": b"a",
            "https://example.com/b": b"b",
        }
    )
    clock = FakeClock()
    fetcher = PoliteFetcher(min_interval=0, get=web, sleep=clock.sleep, clock=clock)
    fetcher("https://example.com/a")
    fetcher("https://example.com/b")
    assert web.calls.count("https://example.com/robots.txt") == 1


def test_missing_robots_means_allowed() -> None:
    web = FakeWeb(
        {
            "https://example.com/robots.txt": FetchError("not found", status=404),
            "https://example.com/a": b"a",
        }
    )
    clock = FakeClock()
    fetcher = PoliteFetcher(min_interval=0, get=web, sleep=clock.sleep, clock=clock)
    assert fetcher("https://example.com/a") == b"a"


def test_unreadable_robots_fails_closed() -> None:
    web = FakeWeb(
        {
            "https://example.com/robots.txt": FetchError("server error", status=500),
            "https://example.com/a": b"a",
        }
    )
    clock = FakeClock()
    fetcher = PoliteFetcher(min_interval=0, get=web, sleep=clock.sleep, clock=clock)
    with pytest.raises(FetchError, match="robots.txt"):
        fetcher("https://example.com/a")
    assert "https://example.com/a" not in web.calls
