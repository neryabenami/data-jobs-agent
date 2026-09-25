"""HTTP helper: one shared session, polite per-host rate limiting, retries with backoff."""
import random
import threading
import time
from urllib.parse import urlparse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Minimum seconds between requests to the same host
HOST_DELAY = {
    "www.linkedin.com": 1.6,
    "www.alljobs.co.il": 1.2,
    "www.jobmaster.co.il": 1.0,
    "www.drushim.co.il": 0.8,
    "webapi.drushim.co.il": 0.8,
    "www.bing.com": 3.0,
}
DEFAULT_DELAY = 0.4


class FetchError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


class Http:
    def __init__(self, deadline=None):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9,he;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        })
        self._last = {}
        self._lock = threading.Lock()
        self.deadline = deadline  # epoch seconds; no new requests after it

    def out_of_time(self):
        return self.deadline is not None and time.time() >= self.deadline

    def _wait_turn(self, host):
        delay = HOST_DELAY.get(host, DEFAULT_DELAY)
        with self._lock:
            now = time.time()
            nxt = max(now, self._last.get(host, 0) + delay)
            self._last[host] = nxt
        if nxt > now:
            time.sleep(nxt - now + random.uniform(0, delay * 0.3))

    def request(self, method, url, retries=3, timeout=30, headers=None, **kw):
        host = urlparse(url).netloc
        last_err = None
        for attempt in range(retries + 1):
            if self.out_of_time():
                raise FetchError("הסריקה נעצרה - הגיע מועד סיום הסריקה")
            self._wait_turn(host)
            try:
                r = self.s.request(method, url, timeout=timeout, headers=headers, **kw)
            except requests.RequestException as e:
                last_err = FetchError(f"שגיאת רשת: {type(e).__name__}")
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                last_err = FetchError(f"HTTP {r.status_code}", r.status_code)
                if attempt == retries:
                    break
                wait = min(60, 5 * 2 ** attempt)
                ra = r.headers.get("Retry-After")
                if ra and ra.isdigit():
                    wait = min(90, int(ra))
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise FetchError(f"HTTP {r.status_code}", r.status_code)
            return r
        raise last_err or FetchError("נכשל")

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def get_json(self, url, **kw):
        r = self.get(url, **kw)
        try:
            return r.json()
        except ValueError:
            raise FetchError("תשובה שאינה JSON")

    def get_text(self, url, **kw):
        r = self.get(url, **kw)
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text
