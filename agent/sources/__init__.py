"""Source scanners. Each scanner receives a ScanContext, records one SourceStatus row per scanned link
and appends RawJob objects (with the FULL description fetched from the job page) to ctx.raw_jobs."""
import threading

from ..models import SourceStatus
from ..textutil import canonical_url


class ScanContext:
    def __init__(self, http, now):
        self.http = http
        self.now = now
        self.statuses = []
        self.raw_jobs = []
        self.companies = {}          # company name -> site where seen (feeds ATS discovery)
        self.new_boards = []         # (kind, slug, company, via) discovered during this run
        self.comeet_done = set()     # Comeet company UIDs already scanned in this run
        self._seen = set()
        self._lock = threading.Lock()

    def status(self, url, site, method):
        st = SourceStatus(url=url, site=site, method=method)
        with self._lock:
            self.statuses.append(st)
        return st

    def first_time(self, url):
        """True the first time a job URL is seen in this run (avoids fetching the same job page twice)."""
        key = canonical_url(url)
        with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True

    def add(self, raw):
        with self._lock:
            self.raw_jobs.append(raw)

    def saw_company(self, name, site):
        name = (name or "").strip()
        if name and len(name) < 80:
            with self._lock:
                self.companies.setdefault(name, site)
